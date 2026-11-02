"""
ShwaasAI Production Backend Server
Phase 1 Extended API wrapping core ML with:
- SQLite persistence
- JWT authentication
- Concurrency-safe inference & Grad-CAM locking
- Clean WHO-aligned referral tracking
"""

import uuid
import json
import os
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, Query, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from server.db import init_db, get_db, User, Screening, Referral
from server.auth import hash_password, verify_password, create_access_token, get_current_user, get_current_user_optional
from server.schemas import (
    LoginRequest, TokenResponse, ScreeningResponse, Demographics, AudioModelOutput, FusionOutput,
    ScreeningListItem, ReferralUpdateRequest, ReferralResponse, StatsResponse,
    TierEnum, PathwayCodeEnum, ReferralStatusEnum
)
from server.clinical_access import visible_screenings, require_screening, screening_scope
from server.clinical import install_clinical

# Initialize database schema on startup
init_db()

app = FastAPI(
    title="ShwaasAI Two-Channel Triage & Referral Tracking API",
    version="1.1.0",
    description="Multimodal TB screening API for frontline ASHA health workers."
)

# Explicit CORS Origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in os.getenv("SHWAAS_CORS_ORIGINS", "").split(",") if x.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB file size limit


# --- 1. SYSTEM ENDPOINTS ---
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ShwaasAI Production Server",
        "version": "1.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/version")
def version_info():
    return {
        "version": "1.1.0",
        "contract": "1.0.0",
        "engine": "MobileNetV2-CNN + WHO-Clinical-Rules",
        "proxy_task": "respiratory_abnormality_proxy"
    }


# --- 2. AUTHENTICATION ---
@app.post("/auth/login", response_model=TokenResponse)
def login(creds: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == creds.username).first()
    if not user or not verify_password(creds.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "phc_center": user.phc_center
    }


# --- 3. SCREENINGS (PREDICT & PERSIST) ---
@app.post("/screenings")
@app.post("/predict")
async def create_screening(
    file: UploadFile = File(...),
    age: int = Form(18),
    sex: str = Form("prefer_not_to_say"),
    village: str = Form("Unknown"),
    cough_duration: int = Form(0),
    fever: int = Form(0),
    night_sweats: int = Form(0),
    weight_loss: int = Form(0),
    hemoptysis: int = Form(0),
    tb_contact: int = Form(0),
    diabetes: int = Form(0),
    hiv: int = Form(0),
    immunosuppression: int = Form(0),
    silica_exposure: int = Form(0),
    consent_given: bool = Form(False),
    include_gradcam: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not consent_given:
        raise HTTPException(422, "Consent is required before saving a screening.")
    # 1. Content-type and file size check
    if file.content_type and "wav" not in file.content_type.lower() and "octet-stream" not in file.content_type.lower():
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error_code": "INVALID_AUDIO_FORMAT",
                "message": "Audio file must be WAV format (16kHz mono).",
                "action": "upload_wav_file"
            }
        )

    audio_bytes = await file.read(MAX_AUDIO_BYTES + 1)
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error_code": "FILE_TOO_LARGE",
                "message": f"Audio file exceeds maximum limit of {MAX_AUDIO_BYTES // (1024*1024)}MB.",
                "action": "record_shorter_audio"
            }
        )

    answers = {
        "cough_duration": cough_duration,
        "fever": fever,
        "night_sweats": night_sweats,
        "weight_loss": weight_loss,
        "hemoptysis": hemoptysis,
        "tb_contact": tb_contact,
        "diabetes": diabetes,
        "hiv": hiv,
        "immunosuppression": immunosuppression,
        "silica_exposure": silica_exposure,
    }

    try:
        # 2. Run Pipeline
        from server.pipeline import run_screening_pipeline
        result = await run_screening_pipeline(
            audio_bytes=audio_bytes,
            age=age,
            sex=sex,
            village=village,
            answers=answers,
            include_gradcam=include_gradcam
        )

        if result.get("error"):
            return JSONResponse(
                status_code=result.get("status_code", 400),
                content={
                    "status": "error",
                    "error_code": result.get("error_code"),
                    "message": result.get("message"),
                    "action": result.get("action"),
                    "pathway_code": result.get("pathway_code")
                }
            )

        # 3. Privacy Compliance: Generate Anonymous Patient Code
        session_id = str(uuid.uuid4())
        village_clean = "".join(c for c in village if c.isalnum())[:3].upper() or "GEN"
        time_part = datetime.now(timezone.utc).strftime("%H%M%S")
        patient_code = f"PAT-{village_clean}-{time_part}"

        # 4. Save to Database
        screening_record = Screening(
            id=session_id,
            user_id=current_user.id if current_user else None,
            patient_code=patient_code,
            age=age,
            sex=sex,
            village=village,
            answers_json=json.dumps(answers),
            clinical_score=result["clinical_score"],
            questionnaire_max=result["questionnaire_max"],
            audio_raw_score=result["raw_prob"],
            audio_calibrated_score=result["calibrated_prob"],
            tier=result["tier"].value,
            pathway_code=result["pathway_code"].value,
            recommended_pathway=result["recommended_pathway"],
            red_flag_detected=result["red_flag"],
            high_risk_present=result["high_risk"],
            uncertain_symptoms_json=json.dumps(result["uncertain_symptoms"]),
            gradcam_image=result["gradcam_image"],
            consent_given=consent_given
        )
        db.add(screening_record)

        # Create initial referral tracking entry
        referral_record = Referral(
            screening_id=session_id,
            status="pending",
            notes=f"Initial screening conducted. Recommended: {result['recommended_pathway']}"
        )
        db.add(referral_record)
        db.commit()

        # 5. Build Transparent Contract Response
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "session_id": session_id,
                "patient_code": patient_code,
                "patient_demographics": {
                    "age": age,
                    "sex": sex,
                    "village": village,
                    "bias_note": "Excluded from scoring to prevent algorithmic bias."
                },
                "questionnaire_score": result["clinical_score"],
                "questionnaire_max": result["questionnaire_max"],
                "red_flag_detected": result["red_flag"],
                "high_risk_factors_present": result["high_risk"],
                "uncertain_symptoms": result["uncertain_symptoms"],
                "audio_model": {
                    "target": "respiratory_abnormality_proxy",
                    "raw_score": result["raw_prob"],
                    "calibrated_score": result["calibrated_prob"],
                    "tb_probability_validated": False
                },
                "fusion": {
                    "status": result["fusion_status"],
                    "tier": result["tier"].value
                },
                "pathway_code": result["pathway_code"].value,
                "recommended_pathway": result["recommended_pathway"],
                "clinical_note": "This is a screening support tool, not a diagnostic. Final decision requires clinician review.",
                "gradcam_image": result["gradcam_image"],
                "created_at": screening_record.created_at.isoformat()
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error_code": "SERVER_ERROR",
                "message": f"Inference pipeline error: {str(e)}",
                "action": "retry_or_contact_admin"
            }
        )


# --- 4. SCREENINGS LIST & QUERY ---
@app.get("/screenings", response_model=List[ScreeningListItem])
def list_screenings(
    tier: Optional[TierEnum] = Query(None),
    village: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = visible_screenings(db, current_user).outerjoin(Referral)

    if tier:
        query = query.filter(Screening.tier == tier.value)
    if village:
        query = query.filter(Screening.village.ilike(f"%{village}%"))
    if search:
        query = query.filter(
            (Screening.patient_code.ilike(f"%{search}%")) |
            (Screening.village.ilike(f"%{search}%"))
        )

    screenings = query.order_by(Screening.created_at.desc()).offset(offset).limit(limit).all()

    items = []
    for s in screenings:
        ref_status = s.referral.status if s.referral else "pending"
        items.append({
            "id": s.id,
            "patient_code": s.patient_code,
            "created_at": s.created_at,
            "age": s.age,
            "sex": s.sex,
            "village": s.village,
            "clinical_score": s.clinical_score,
            "audio_calibrated_score": s.audio_calibrated_score,
            "tier": TierEnum(s.tier),
            "pathway_code": PathwayCodeEnum(s.pathway_code),
            "referral_status": ReferralStatusEnum(ref_status),
            "has_gradcam": bool(s.gradcam_image)
        })
    return items


# --- 5. SCREENING DETAIL ---
@app.get("/screenings/{screening_id}")
def get_screening_detail(screening_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    screening = require_screening(db, current_user, screening_id)

    ref_status = screening.referral.status if screening.referral else "pending"
    ref_notes = screening.referral.notes if screening.referral else ""

    return {
        "id": screening.id,
        "patient_code": screening.patient_code,
        "created_at": screening.created_at.isoformat(),
        "patient_demographics": {
            "age": screening.age,
            "sex": screening.sex,
            "village": screening.village
        },
        "answers": screening.get_answers(),
        "uncertain_symptoms": screening.get_uncertain_symptoms(),
        "clinical_score": screening.clinical_score,
        "questionnaire_max": screening.questionnaire_max,
        "red_flag_detected": screening.red_flag_detected,
        "high_risk_factors_present": screening.high_risk_present,
        "audio_model": {
            "raw_score": screening.audio_raw_score,
            "calibrated_score": screening.audio_calibrated_score,
            "target": "respiratory_abnormality_proxy"
        },
        "tier": screening.tier,
        "pathway_code": screening.pathway_code,
        "recommended_pathway": screening.recommended_pathway,
        "gradcam_image": screening.gradcam_image,
        "referral": {
            "status": ref_status,
            "notes": ref_notes,
            "updated_at": screening.referral.updated_at.isoformat() if screening.referral else None
        }
    }


# --- 6. REFERRAL TRACKING UPDATE ---
@app.patch("/screenings/{screening_id}/referral", response_model=ReferralResponse)
def update_referral(
    screening_id: str,
    update_data: ReferralUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "doctor":
        raise HTTPException(403, "A clinician account is required.")
    require_screening(db, current_user, screening_id)
    referral = db.query(Referral).filter(Referral.screening_id == screening_id).first()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral record for this screening not found")

    referral.status = update_data.status.value
    if update_data.notes is not None:
        referral.notes = update_data.notes
    referral.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "screening_id": screening_id,
        "status": ReferralStatusEnum(referral.status),
        "notes": referral.notes,
        "updated_at": referral.updated_at
    }


# --- 7. DASHBOARD & FIELD METRICS (STATS) ---
@app.get("/stats", response_model=StatsResponse)
def get_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total = visible_screenings(db, current_user).count()

    # Tier counts
    tier_counts = {t.value: 0 for t in TierEnum}
    tier_rows = db.query(Screening.tier, func.count(Screening.id)).filter(screening_scope(current_user)).group_by(Screening.tier).all()
    for tier_val, count in tier_rows:
        if tier_val in tier_counts:
            tier_counts[tier_val] = count

    # Referral counts
    referral_counts = {"pending": 0, "tested": 0, "lost": 0}
    ref_rows = db.query(Referral.status, func.count(Referral.id)).join(Screening).filter(screening_scope(current_user)).group_by(Referral.status).all()
    for st, count in ref_rows:
        if st in referral_counts:
            referral_counts[st] = count

    total_referrals = sum(referral_counts.values())
    completion_rate = round((referral_counts["tested"] / total_referrals * 100), 1) if total_referrals > 0 else 0.0

    # Screenings by village
    village_rows = db.query(Screening.village, func.count(Screening.id)).filter(screening_scope(current_user)).group_by(Screening.village).all()
    screenings_by_village = {v: count for v, count in village_rows}

    return {
        "total_screenings": total,
        "tier_counts": tier_counts,
        "referral_counts": referral_counts,
        "referral_completion_rate": completion_rate,
        "screenings_by_village": screenings_by_village
    }


# --- 8. MEDICAL DOCUMENT & PRESCRIPTION OCR ---
@app.post("/ocr/scan")
async def scan_prescription_document(image: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """
    Real-time Tesseract OCR endpoint for medical prescription and OPD slip text extraction.
    Returns empty text if image contains no text (e.g. blank, dark object).
    """
    contents = await image.read(20 * 1024 * 1024 + 1)
    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(413, "Image is too large.")
    if not contents:
        return {"text": "", "length": 0}

    import io
    from PIL import Image
    try:
        import pytesseract
        pil_img = Image.open(io.BytesIO(contents))
        # Convert to grayscale for cleaner document binarization
        gray_img = pil_img.convert("L")
        text = pytesseract.image_to_string(gray_img)
        clean_text = text.strip()
        return {
            "text": clean_text,
            "length": len(clean_text),
            "status": "success"
        }
    except Exception as e:
        return {
            "text": "",
            "length": 0,
            "error": str(e),
            "status": "error"
        }

install_clinical(app)
