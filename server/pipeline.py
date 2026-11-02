"""
Inference pipeline wrapper for ShwaasAI:
- Fast cached model loading
- Concurrency protection for Grad-CAM hooks
- WHO-aligned clinical scorer with uncertainty tracking
- Context-aware dynamic escalation logic
- Starlette threadpool offloading
"""

import os
import sys
import base64
import tempfile
import asyncio
from pathlib import Path
from typing import Tuple, Dict, Any, List

import cv2
import librosa
import numpy as np
import torch
from starlette.concurrency import run_in_threadpool

PROJECT_ROOT = Path(__file__).parent.parent
SHWAAS_AI_ROOT = PROJECT_ROOT if (PROJECT_ROOT / "src").exists() else (PROJECT_ROOT / "Shwaas-AI")
sys.path.insert(0, str(SHWAAS_AI_ROOT))

from src.model import LateFusionTBModel
from src.gradcam import GradCAM
from src.api import preprocess_audio, audio_to_tensor, audio_quality_gate, apply_temperature_scaling
from server.schemas import TierEnum, PathwayCodeEnum

CACHE_DIR = SHWAAS_AI_ROOT / "cache"
device = torch.device("cpu")

# --- INITIALIZE MODEL WITH LOCAL CACHE FIRST ---
model = LateFusionTBModel().to(device)
weights_path = None

# Search for cached weights locally
candidate_paths = [
    CACHE_DIR / "late_fusion_model.pth",
    CACHE_DIR / "models--Kushagra-01--shwaasai-model" / "snapshots"
]

if candidate_paths[0].exists():
    weights_path = candidate_paths[0]
elif candidate_paths[1].exists():
    # Find any .pth file inside snapshots
    for root, dirs, files in os.walk(candidate_paths[1]):
        for f in files:
            if f.endswith(".pth"):
                weights_path = Path(root) / f
                break

if not weights_path or not weights_path.exists():
    from huggingface_hub import hf_hub_download
    print("📥 Model weights not found in local cache. Fetching from Hugging Face...")
    weights_path = Path(hf_hub_download(repo_id="Kushagra-01/shwaasai-model", filename="late_fusion_model.pth", cache_dir=str(CACHE_DIR)))

print(f"🧠 Loading model weights from: {weights_path}")
model.load_state_dict(torch.load(weights_path, map_location=device, weights_only=True))
model.eval()

target_layer = model.audio_encoder.backbone.features[-1][0]
gradcam_engine = GradCAM(model, target_layer)
gradcam_lock = asyncio.Lock()


# --- WHO-ALIGNED CLINICAL SCORER (Strict Max 18) ---
QUESTION_METADATA = {
    "cough_duration": {"weight": 2, "is_red_flag": False, "is_high_risk": False},
    "fever": {"weight": 2, "is_red_flag": False, "is_high_risk": False},
    "night_sweats": {"weight": 2, "is_red_flag": False, "is_high_risk": False},
    "weight_loss": {"weight": 2, "is_red_flag": False, "is_high_risk": False},
    "hemoptysis": {"weight": 2, "is_red_flag": True, "is_high_risk": False},
    "tb_contact": {"weight": 2, "is_red_flag": False, "is_high_risk": True},
    "diabetes": {"weight": 2, "is_red_flag": False, "is_high_risk": False},
    "hiv": {"weight": 2, "is_red_flag": False, "is_high_risk": True},
    "immunosuppression": {"weight": 1, "is_red_flag": False, "is_high_risk": True},
    "silica_exposure": {"weight": 1, "is_red_flag": False, "is_high_risk": False},
}

def evaluate_clinical_symptoms(answers: Dict[str, int]) -> Tuple[int, bool, bool, List[str]]:
    """
    Evaluates clinical score with exact WHO weighting:
    0 = No (0 pts)
    1 = Unsure (0 pts, uncertainty recorded)
    2 = Yes (full clinical weight added)
    Max score strictly equals 18.
    """
    total_score = 0
    red_flag = False
    high_risk = False
    uncertain_symptoms = []

    for key, meta in QUESTION_METADATA.items():
        val = answers.get(key, 0)
        if val == 2:  # Confirmed Yes
            total_score += meta["weight"]
            if meta["is_red_flag"]:
                red_flag = True
            if meta["is_high_risk"]:
                high_risk = True
        elif val == 1:  # Unsure
            uncertain_symptoms.append(key)

    return total_score, red_flag, high_risk, uncertain_symptoms


def _sync_audio_inference(audio_bytes: bytes) -> Tuple[bool, str, float, float, torch.Tensor]:
    """Runs audio decoding, quality gate, and PyTorch model in worker thread."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_path = tmp_file.name

    try:
        y, sr = librosa.load(tmp_path, sr=16000, mono=True)
        is_valid, msg = audio_quality_gate(y)
        if not is_valid:
            return False, msg, 0.0, 0.0, None

        y_clean = preprocess_audio(y, sr)
        audio_tensor = audio_to_tensor(y_clean).to(device)
        
        with torch.no_grad():
            tabular_zeros = torch.zeros((1, 4), dtype=torch.float32).to(device)
            raw_prob = float(model(audio_tensor, tabular_zeros).item())
            
        calibrated_prob = float(apply_temperature_scaling(raw_prob, temperature=1.5))
        return True, "Quality passed", raw_prob, calibrated_prob, audio_tensor
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


async def run_screening_pipeline(
    audio_bytes: bytes,
    age: int,
    sex: str,
    village: str,
    answers: Dict[str, int],
    include_gradcam: bool = False
) -> Dict[str, Any]:
    """
    Full async-safe triage pipeline:
    1. Pediatric check
    2. Threadpool audio processing & model inference
    3. Clinical rule evaluation & dynamic escalation
    4. Async-locked Grad-CAM generation
    """
    # 1. Pediatric check (<18)
    if age < 18:
        return {
            "error": True,
            "status_code": 400,
            "error_code": "PEDIATRIC_PATIENT",
            "message": "Patient is under 18. Pediatric TB screening requires a different clinical pathway.",
            "action": "route_to_pediatric_protocol",
            "pathway_code": PathwayCodeEnum.PEDIATRIC_PATHWAY
        }

    # 2. Audio processing in threadpool
    is_valid, msg, raw_prob, cal_prob, audio_tensor = await run_in_threadpool(
        _sync_audio_inference, audio_bytes
    )
    if not is_valid:
        return {
            "error": True,
            "status_code": 400,
            "error_code": "AUDIO_QUALITY_REJECTED",
            "message": msg,
            "action": "request_new_recording",
            "pathway_code": None
        }

    # 3. Clinical scoring
    clinical_score, red_flag, high_risk, uncertain_symptoms = evaluate_clinical_symptoms(answers)

    # 4. Context-Aware Escalation Logic
    if red_flag:
        tier = TierEnum.URGENT
        pathway_code = PathwayCodeEnum.IMMEDIATE_TRIAGE
        action = "Immediate medical assessment required (hemoptysis detected)."
        fusion_status = "safety_override"
    elif high_risk and clinical_score <= 3:
        tier = TierEnum.HIGH_RISK_SCREENING
        pathway_code = PathwayCodeEnum.HIGH_RISK_PATHWAY
        action = "High-risk profile detected (HIV/contact). Prioritized screening pathway recommended."
        fusion_status = "risk_based_referral"
    else:
        # Clinical baseline tier
        if clinical_score <= 3:
            clinical_tier = TierEnum.LOW
            audio_threshold = 0.45
        elif clinical_score <= 8:
            clinical_tier = TierEnum.MODERATE
            audio_threshold = 0.65
        else:
            clinical_tier = TierEnum.HIGH
            audio_threshold = 0.85

        final_tier = clinical_tier
        # Dynamic Audio Escalation
        if cal_prob > audio_threshold and clinical_tier != TierEnum.HIGH:
            if clinical_tier == TierEnum.LOW:
                final_tier = TierEnum.MODERATE
            elif clinical_tier == TierEnum.MODERATE:
                final_tier = TierEnum.HIGH

        tier = final_tier
        fusion_status = "finalized"

        if tier == TierEnum.HIGH:
            pathway_code = PathwayCodeEnum.CBNAAT_REFERRAL
            action = "Urgent referral for CBNAAT testing recommended."
        elif tier == TierEnum.MODERATE:
            pathway_code = PathwayCodeEnum.PHC_EVALUATION
            action = "Clinical evaluation recommended. Persistent cough warrants PHC visit."
        else:
            pathway_code = PathwayCodeEnum.STANDARD_HYGIENE
            action = "Low immediate risk. Maintain standard respiratory hygiene."

    # 5. Optional Grad-CAM with Concurrency Lock
    gradcam_b64 = None
    if include_gradcam and audio_tensor is not None:
        async with gradcam_lock:
            def _generate_cam_sync():
                tabular_zeros = torch.zeros((1, 4), dtype=torch.float32).to(device)
                heatmap = gradcam_engine.generate_cam(audio_tensor, tabular_zeros)
                _, buffer = cv2.imencode('.jpg', heatmap, [cv2.IMWRITE_JPEG_QUALITY, 60])
                return base64.b64encode(buffer).decode('utf-8')

            cam_b64_str = await run_in_threadpool(_generate_cam_sync)
            gradcam_b64 = f"data:image/jpeg;base64,{cam_b64_str}"

    return {
        "error": False,
        "clinical_score": clinical_score,
        "questionnaire_max": 18,
        "red_flag": red_flag,
        "high_risk": high_risk,
        "uncertain_symptoms": uncertain_symptoms,
        "raw_prob": round(raw_prob, 4),
        "calibrated_prob": round(cal_prob, 4),
        "tier": tier,
        "pathway_code": pathway_code,
        "recommended_pathway": action,
        "fusion_status": fusion_status,
        "gradcam_image": gradcam_b64
    }
