# src/api.py
import os
import base64
import tempfile
from pathlib import Path

import cv2
import librosa
import numpy as np
import scipy.signal as signal
import torch
from fastapi import FastAPI, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from huggingface_hub import hf_hub_download

from src.model import LateFusionTBModel
from src.gradcam import GradCAM

app = FastAPI(title="ShwaasAI Two-Channel Triage API")

# --- SETUP ---
PROJECT_ROOT = Path(__file__).parent.parent
CACHE_DIR = PROJECT_ROOT / "cache"
CACHE_DIR.mkdir(exist_ok=True)

device = torch.device("cpu")
model = LateFusionTBModel().to(device)

# --- AUTO-DOWNLOAD LOGIC ---
REPO_ID = "Kushagra-01/shwaasai-model"
FILENAME = "late_fusion_model.pth"

print(f"📥 Checking for model weights in cache or downloading from {REPO_ID}...")
try:
    model_path = hf_hub_download(repo_id=REPO_ID, filename=FILENAME, cache_dir=str(CACHE_DIR))
    print("✅ Model weights loaded successfully from Hugging Face!")
except Exception as e:
    print(f"⚠️ Could not download from Hugging Face: {e}")
    print("Falling back to local cache...")
    model_path = CACHE_DIR / FILENAME

model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
model.eval()

target_layer = model.audio_encoder.backbone.features[-1][0]
gradcam = GradCAM(model, target_layer)


# --- AUDIO PROCESSING HELPERS ---
def preprocess_audio(y, sr=16000):
    if sr != 16000:
        y = librosa.resample(y, orig_sr=sr, target_sr=16000)
    # Bandpass filter (300Hz - 6000Hz) to isolate cough frequencies
    nyq = 0.5 * 16000
    b, a = signal.butter(4, [300.0 / nyq, 6000.0 / nyq], btype='band')
    y = signal.filtfilt(b, a, y)
    y, _ = librosa.effects.trim(y, top_db=30)
    rms = np.sqrt(np.mean(y ** 2))
    if rms > 1e-5:
        y = y / (rms * 5.0)  # Loudness normalization
    target_len = int(16000 * 3.0)  # 3 seconds
    if len(y) < target_len:
        y = np.pad(y, (0, target_len - len(y)))
    else:
        y = y[:target_len]
    return y


def audio_to_tensor(y):
    mel_spec = librosa.feature.melspectrogram(y=y, sr=16000, n_mels=128, n_fft=1024, hop_length=512)
    log_mel = librosa.power_to_db(mel_spec, ref=np.max)
    log_mel = (log_mel - log_mel.min()) / (log_mel.max() - log_mel.min() + 1e-8)
    img = cv2.resize(log_mel, (224, 224))
    img_rgb = np.stack((img,) * 3, axis=-1)
    return torch.tensor(img_rgb, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0)


# --- AUDIO QUALITY GATE ---
def audio_quality_gate(y: np.ndarray, max_amplitude: float = 0.99, min_rms: float = 0.005):
    """Rejects audio that is clipping (distorted) or too quiet (silence)."""
    if np.max(np.abs(y)) >= max_amplitude:
        return False, "Audio is clipping (distorted). Please move the microphone further away."

    rms = np.sqrt(np.mean(y ** 2))
    if rms < min_rms:
        return False, "Audio is too quiet. Please ensure the microphone is close to the patient."

    return True, "Audio quality passed."


# --- TWO-CHANNEL WEIGHTED CLINICAL SCORER ---
def calculate_clinical_score(
        cough_duration: int,  # 0=None, 1=<2wks, 2=≥2wks
        fever: int,  # 0=No, 1=Yes
        night_sweats: int,  # 0=No, 1=Yes
        weight_loss: int,  # 0=No, 2=Yes (unexplained)
        hemoptysis: int,  # 0=No, 2=Yes
        tb_contact: int,  # 0=No, 3=Yes
        diabetes: int,  # 0=No, 1=Yes
        hiv: int,  # 0=No, 2=Yes
        immunosuppression: int,  # 0=No, 2=Yes
        silica_exposure: int  # 0=No, 2=Yes
):
    """
    WHO-aligned Weighted Clinical Scoring (Provisional Prototype).
    Maximum Score: 18 points.
    Returns: (score, red_flag_status, high_risk_status)
    """
    score = 0
    score += cough_duration
    score += fever
    score += night_sweats
    score += weight_loss
    score += hemoptysis
    score += tb_contact
    score += diabetes
    score += hiv
    score += immunosuppression
    score += silica_exposure

    # Safety Overrides
    red_flag = (hemoptysis == 2)  # Blood = Urgent
    high_risk = (hiv == 2 or immunosuppression == 2 or tb_contact == 3)

    return score, red_flag, high_risk


# --- API ENDPOINT ---
@app.post("/predict")
async def predict(
        file: UploadFile = File(...),
        # --- NEW: Bias-Aware Demographic Routing ---
        age: int = Form(18, description="Patient age in years. Used for routing only, not scoring."),
        sex: str = Form("prefer_not_to_say", description="Patient sex/gender. Used for records only, not scoring."),

        # --- 10-Question Clinical Parameters ---
        cough_duration: int = Form(0, description="0=None, 1=<2wks, 2=≥2wks"),
        fever: int = Form(0, description="0=No, 1=Yes"),
        night_sweats: int = Form(0, description="0=No, 1=Yes"),
        weight_loss: int = Form(0, description="0=No, 2=Yes"),
        hemoptysis: int = Form(0, description="0=No, 2=Yes (Red Flag)"),
        tb_contact: int = Form(0, description="0=No, 3=Yes"),
        diabetes: int = Form(0, description="0=No, 1=Yes"),
        hiv: int = Form(0, description="0=No, 2=Yes"),
        immunosuppression: int = Form(0, description="0=No, 2=Yes"),
        silica_exposure: int = Form(0, description="0=No, 2=Yes"),

        include_gradcam: bool = Query(False, description="Set to true to include the heavy base64 heatmap.")
):
    try:
        # 1. AGE ROUTING (Pediatric Safety Check)
        if age < 18:
            return JSONResponse(status_code=400, content={
                "status": "error",
                "message": "Patient is under 18. Pediatric TB screening requires a different clinical pathway.",
                "action": "route_to_pediatric_protocol"
            })

        # 2. Audio Processing
        contents = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(contents)
            tmp_path = tmp_file.name

        try:
            y, sr = librosa.load(tmp_path, sr=16000, mono=True)

            # --- QUALITY GATE ---
            is_valid, message = audio_quality_gate(y)
            if not is_valid:
                return JSONResponse(status_code=400, content={
                    "status": "error",
                    "message": message,
                    "action": "request_new_recording"
                })

            y_clean = preprocess_audio(y, sr)
            audio_tensor = audio_to_tensor(y_clean).to(device)
        finally:
            os.unlink(tmp_path)

        # 3. AI Audio Inference (Isolate audio score by passing zeros to tabular branch)
        with torch.no_grad():
            tabular_zeros = torch.zeros((1, 4), dtype=torch.float32).to(device)
            audio_prob = model(audio_tensor, tabular_zeros).item()

            # 4. Two-Channel Clinical Scoring
        clinical_score, red_flag, high_risk = calculate_clinical_score(
            cough_duration, fever, night_sweats, weight_loss,
            hemoptysis, tb_contact, diabetes, hiv,
            immunosuppression, silica_exposure
        )

        # 5. Transparent Routing Logic (No blind addition of scores)
        if red_flag:
            final_tier = "URGENT"
            action = "Immediate medical assessment required (hemoptysis detected)."
            fusion_status = "safety_override"
        elif high_risk and clinical_score <= 3:
            # Asymptomatic or low-symptom but high-risk (e.g., TB contact, HIV)
            final_tier = "HIGH_RISK_SCREENING"
            action = "Contact screening or high-risk pathway referral recommended."
            fusion_status = "risk_based_referral"
        else:
            # Standard tiering based on weighted score
            if clinical_score <= 3:
                clinical_tier = "LOW"
            elif clinical_score <= 8:
                clinical_tier = "MODERATE"
            else:
                clinical_tier = "HIGH"

            # Audio can escalate but NEVER downgrade
            final_tier = clinical_tier
            if audio_prob > 0.65 and clinical_tier != "HIGH":
                if clinical_tier == "LOW":
                    final_tier = "MODERATE"
                elif clinical_tier == "MODERATE":
                    final_tier = "HIGH"

            fusion_status = "finalized"

            if final_tier == "HIGH":
                action = "Urgent referral for CBNAAT testing recommended."
            elif final_tier == "MODERATE":
                action = "Clinical evaluation recommended. Persistent cough warrants PHC visit."
            else:
                action = "Low immediate risk. Maintain standard respiratory hygiene."

        # 6. Build the Traceable, Two-Channel Response Schema
        response_payload = {
            "status": "success",
            "patient_demographics": {
                "age": age,
                "sex": sex,
                "bias_note": "Demographics collected for record-keeping only. Excluded from scoring to prevent algorithmic bias."
            },
            "questionnaire_score": clinical_score,
            "questionnaire_max": 18,
            "red_flag_detected": red_flag,
            "high_risk_factors_present": high_risk,
            "audio_model": {
                "target": "respiratory_abnormality_proxy",
                "score": round(audio_prob, 4),
                "tb_probability_validated": False  # CRITICAL DISCLAIMER
            },
            "fusion": {
                "status": fusion_status,
                "tier": final_tier
            },
            "recommended_pathway": action,
            "clinical_note": "This is a screening support tool, not a diagnostic. Final decision requires clinician review."
        }

        # 7. Optional Heavy Payload (Grad-CAM)
        if include_gradcam:
            heatmap = gradcam.generate_cam(audio_tensor, tabular_zeros)
            _, buffer = cv2.imencode('.jpg', heatmap, [cv2.IMWRITE_JPEG_QUALITY, 60])
            heatmap_b64 = base64.b64encode(buffer).decode('utf-8')
            response_payload["gradcam_image"] = f"data:image/jpeg;base64,{heatmap_b64}"

        return JSONResponse(content=response_payload)

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})