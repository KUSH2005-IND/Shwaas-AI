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

app = FastAPI(title="ShwaasAI Triage API")

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
    print(f"️ Could not download from Hugging Face: {e}")
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


# --- NEW: AUDIO QUALITY GATE ---
def audio_quality_gate(y: np.ndarray, max_amplitude: float = 0.99, min_rms: float = 0.005):
    """
    Rejects audio that is clipping (distorted) or too quiet (silence).
    Returns: (is_valid: bool, message: str)
    """
    # 1. Check for clipping (digital distortion)
    if np.max(np.abs(y)) >= max_amplitude:
        return False, "Audio is clipping (distorted). Please move the microphone further away."

    # 2. Check for silence / low signal level
    rms = np.sqrt(np.mean(y ** 2))
    if rms < min_rms:
        return False, "Audio is too quiet. Please ensure the microphone is close to the patient."

    return True, "Audio quality passed."


# --- UNCERTAINTY-AWARE CLINICAL SCORER ---
def calculate_clinical_score(q1, q2, q3, q4):
    """
    WHO-aligned TB Symptom Scorer with Uncertainty Handling.
    Inputs: 0 (No), 1 (Yes), 2 (Unsure/Unknown)
    """
    score = 0
    unknown_flags = []

    def evaluate(q_val, points, name):
        if q_val == 1:
            return points
        elif q_val == 2:
            unknown_flags.append(name)
            return 0
        else:
            return 0

    score += evaluate(q1, 2, "cough_duration")
    score += evaluate(q2, 1, "unintended_weight_loss")
    score += evaluate(q3, 1, "night_sweats_fever")
    score += evaluate(q4, 2, "tb_contact")

    if score <= 1:
        clinical_tier = "LOW"
    elif score <= 3:
        clinical_tier = "MODERATE"
    else:
        clinical_tier = "HIGH"

    return score, clinical_tier, unknown_flags


# --- API ENDPOINT ---
@app.post("/predict")
async def predict(
        file: UploadFile = File(...),
        q1: int = Form(0),
        q2: int = Form(0),
        q3: int = Form(0),
        q4: int = Form(0),
        include_gradcam: bool = Query(False,
                                      description="Set to true to include the heavy base64 heatmap in the response.")
):
    try:
        # 1. Audio Processing
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
            # ---------------------

            y_clean = preprocess_audio(y, sr)
            audio_tensor = audio_to_tensor(y_clean).to(device)
        finally:
            os.unlink(tmp_path)

        # 2. AI Audio Inference
        with torch.no_grad():
            tabular_zeros = torch.zeros((1, 4), dtype=torch.float32).to(device)
            audio_prob = model(audio_tensor, tabular_zeros).item()

            # 3. Clinical Scoring
        clinical_score, clinical_tier, unknown_flags = calculate_clinical_score(q1, q2, q3, q4)

        # 4. HYBRID FUSION & VERIFICATION LOGIC
        final_tier = clinical_tier
        fusion_status = "finalized"
        verification_status = "verified"
        next_action = "proceed_to_triage"

        if unknown_flags:
            fusion_status = "provisional"
            verification_status = "clarification_required"
            next_action = "ask_clarifying_question"
        else:
            if audio_prob > 0.65:
                if clinical_tier == "LOW":
                    final_tier = "MODERATE"
                elif clinical_tier == "MODERATE":
                    final_tier = "HIGH"

        # 5. Determine Safe Recommended Action
        if verification_status == "clarification_required":
            action = f"Resolve uncertain responses ({', '.join(unknown_flags)}). Do not rule out TB based on audio score alone."
        elif final_tier == "HIGH":
            action = "Urgent referral for CBNAAT testing recommended."
        elif final_tier == "MODERATE":
            action = "Clinical evaluation recommended. Persistent cough warrants PHC visit regardless of acoustic score."
        else:
            action = "Low immediate risk. Maintain standard respiratory hygiene."

        # 6. Build the Traceable Response Schema
        response_payload = {
            "status": "success",
            "clinical_score": clinical_score,
            "clinical_tier": clinical_tier,
            "uncertain_symptoms": unknown_flags,
            "verification": {
                "status": verification_status,
                "question_id": unknown_flags[0] if unknown_flags else None,
                "next_action": next_action
            },
            "audio_model": {
                "target": "audio_abnormality_proxy",
                "score": round(audio_prob, 4),
                "tb_probability_validated": False
            },
            "fusion": {
                "status": fusion_status,
                "tier": final_tier
            },
            "recommended_action": action
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