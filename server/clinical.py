"""Clinical API: shares existing records without importing the ML pipeline."""
import hashlib
import io
import json
import os
import secrets
import uuid
from pathlib import Path
from typing import Literal

from PIL import Image
from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from server.db import get_db, init_db, User, Screening
from server.auth import create_access_token, decode_access_token, verify_password
from server.schemas import LoginRequest
from server.clinical_models import (
    ClinicalCase, Investigation, ClinicalDocument, ImagingInstance, ClinicalMutation,
    ClinicalChange, ClinicalReport, now,
)
from server.clinical_access import require_screening, visible_screenings

ROOT = Path(__file__).resolve().parent.parent
FILES = Path(os.getenv("SHWAAS_CLINICAL_FILES", str(ROOT / "data" / "clinical-files")))
DIST = ROOT / "clinical" / "dist"
MAX_FILE = 20 * 1024 * 1024
router = APIRouter(prefix="/clinical", tags=["Clinical workspace"])
init_db()

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class Review(Strict):
    event_id: uuid.UUID
    expected_version: int = Field(ge=0)
    status: Literal["awaiting_review", "under_review", "awaiting_results", "reviewed"]
    notes: str = Field(max_length=10000)
    next_action: str = Field(max_length=2000)

class Order(Strict):
    event_id: uuid.UUID
    kind: Literal["Chest X-ray", "Sputum NAAT", "Smear microscopy", "Other investigation"]
    notes: str = Field(default="", max_length=2000)

class OrderUpdate(Strict):
    event_id: uuid.UUID
    expected_version: int = Field(ge=1)
    status: Literal["requested", "accepted", "result_received", "reviewed", "cancelled"]
    notes: str = Field(max_length=4000)

class ExtractedField(Strict):
    name: str = Field(min_length=1, max_length=120)
    value: str = Field(max_length=2000)
    page: int = Field(ge=1, le=20)

class ConfirmDocument(Strict):
    expected_version: int = Field(ge=1)
    fields: list[ExtractedField] = Field(max_length=100)

def authenticate(request: Request, db: Session = Depends(get_db)):
    header = request.headers.get("authorization", "")
    token = header[7:] if header.lower().startswith("bearer ") else request.cookies.get("clinical_session", "")
    payload = decode_access_token(token) if token else None
    user = db.query(User).filter(User.username == payload.get("sub")).first() if payload else None
    if user is None:
        raise HTTPException(401, "Sign in to continue.")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and not header:
        if request.headers.get("x-requested-with") != "ShwaasClinical":
            raise HTTPException(403, "Missing same-origin request header.")
    return user

def doctor(user=Depends(authenticate)):
    if user.role != "doctor":
        raise HTTPException(403, "A clinician account is required.")
    return user

def state_data(state):
    return {
        "version": state.version if state else 0,
        "status": state.status if state else "awaiting_review",
        "notes": state.notes if state else "",
        "next_action": state.next_action if state else "",
        "reviewer": state.reviewer if state else None,
        "updated_at": state.updated_at.isoformat() if state else None,
    }

def document_data(d):
    return {"id": d.id, "filename": d.filename, "media_type": d.media_type,
            "sha256": d.sha256, "size": d.size, "verification": d.verification,
            "confirmed_by": d.confirmed_by, "version": d.version,
            "fields": json.loads(d.fields_json), "created_at": d.created_at.isoformat()}

def image_data(i):
    return {"id": i.id, "order_id": i.order_id, "study_uid": i.study_uid,
            "series_uid": i.series_uid, "sop_uid": i.sop_uid,
            "identity_check": i.identity_check, "patient_id": i.patient_id,
            "created_at": i.created_at.isoformat()}

def order_data(i):
    return {"id": i.id, "kind": i.kind, "status": i.status, "notes": i.notes,
            "version": i.version, "created_at": i.created_at.isoformat()}

def case_data(db, s, full=False):
    data = {
        "id": s.id, "patient_code": s.patient_code, "age": s.age, "sex": s.sex,
        "village": s.village, "created_at": s.created_at.isoformat(), "tier": s.tier,
        "clinical_score": s.clinical_score, "red_flag": s.red_flag_detected,
        "clinical": state_data(db.get(ClinicalCase, s.id)),
        "document_count": db.query(ClinicalDocument).filter_by(screening_id=s.id).count(),
        "image_count": db.query(ImagingInstance).filter_by(screening_id=s.id).count(),
    }
    if full:
        data.update({
            "answers": s.get_answers(), "uncertain_symptoms": s.get_uncertain_symptoms(),
            "questionnaire_max": s.questionnaire_max,
            "audio_model": {"raw_score": s.audio_raw_score,
                            "calibrated_score": s.audio_calibrated_score,
                            "target": "respiratory_abnormality_proxy", "tb_probability_validated": False},
            "recommended_pathway": s.recommended_pathway, "consent_given": s.consent_given,
            "documents": [document_data(d) for d in db.query(ClinicalDocument).filter_by(screening_id=s.id).all()],
            "investigations": [order_data(i) for i in db.query(Investigation).filter_by(screening_id=s.id).all()],
            "images": [image_data(i) for i in db.query(ImagingInstance).filter_by(screening_id=s.id).all()],
            "timeline": [{"id": e.sequence, "kind": e.kind, "actor": e.actor,
                          "created_at": e.created_at.isoformat(), "detail": json.loads(e.detail_json)}
                         for e in db.query(ClinicalChange).filter_by(screening_id=s.id).order_by(ClinicalChange.sequence.desc()).limit(100)],
            "reports": [{"id": r.id, "version": r.version, "created_at": r.created_at.isoformat()}
                        for r in db.query(ClinicalReport).filter_by(screening_id=s.id).order_by(ClinicalReport.created_at.desc())],
        })
    return data

def event(db, case_id, actor, kind, detail=None):
    db.add(ClinicalChange(screening_id=case_id, actor=actor.username, kind=kind,
                          detail_json=json.dumps(detail or {}, sort_keys=True)))

def run_mutation(db, user, event_id, resource, body, action):
    digest = hashlib.sha256(json.dumps({"resource": resource, "body": body},
                                      sort_keys=True, default=str).encode()).hexdigest()
    old = db.get(ClinicalMutation, str(event_id))
    if old:
        if old.actor != user.username or old.digest != digest:
            raise HTTPException(409, "Idempotency key reused with different content.")
        return json.loads(old.result_json)
    try:
        result = action()
        db.add(ClinicalMutation(event_id=str(event_id), actor=user.username,
                               digest=digest, result_json=json.dumps(result, default=str)))
        db.commit()
        return result
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Concurrent update. Reload and reconcile before retrying.")

@router.post("/session")
def login(data: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    if request.headers.get("x-requested-with") != "ShwaasClinical":
        raise HTTPException(403, "Missing same-origin request header.")
    user = db.query(User).filter_by(username=data.username).first()
    if not user or user.role != "doctor" or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Invalid clinician credentials.")
    response.set_cookie("clinical_session", create_access_token({"sub": user.username}),
                        httponly=True, samesite="strict", max_age=86400,
                        secure=os.getenv("SHWAAS_COOKIE_SECURE", "false").lower() == "true",
                        path="/")
    response.headers["Cache-Control"] = "no-store"
    return {"username": user.username, "full_name": user.full_name, "facility": user.phc_center}

@router.get("/session")
def session(user=Depends(doctor)):
    return {"username": user.username, "full_name": user.full_name, "facility": user.phc_center}

@router.delete("/session")
def logout(response: Response, user=Depends(doctor)):
    response.delete_cookie("clinical_session", path="/")
    return {"status": "signed_out"}

@router.get("/cases")
def cases(user=Depends(doctor), db: Session = Depends(get_db), limit: int = 200):
    rows = visible_screenings(db, user).order_by(Screening.created_at.desc()).limit(min(max(limit, 1), 500)).all()
    return {"cases": [case_data(db, s) for s in rows], "received_at": now().isoformat()}

@router.get("/cases/{case_id}")
def detail(case_id: str, user=Depends(doctor), db: Session = Depends(get_db)):
    return case_data(db, require_screening(db, user, case_id), full=True)

@router.post("/cases/{case_id}/review")
def save_review(case_id: str, data: Review, user=Depends(doctor), db: Session = Depends(get_db)):
    s = require_screening(db, user, case_id)
    if data.status == "reviewed" and (not data.notes or not data.next_action):
        raise HTTPException(422, "Completed review requires notes and a next action.")
    def action():
        state = db.get(ClinicalCase, case_id)
        if (state.version if state else 0) != data.expected_version:
            raise HTTPException(409, "Case changed. Compare the latest version with your draft.")
        if state is None:
            state = ClinicalCase(screening_id=case_id, version=0)
            db.add(state)
            db.flush()
        changed = db.execute(update(ClinicalCase).where(
            ClinicalCase.screening_id == case_id, ClinicalCase.version == data.expected_version
        ).values(version=data.expected_version+1, status=data.status, notes=data.notes,
                 next_action=data.next_action, reviewer=user.username, updated_at=now()))
        if changed.rowcount != 1:
            raise HTTPException(409, "Case changed. Reload and reconcile.")
        db.expire(state)
        event(db, case_id, user, "clinical_review", data.model_dump(mode="json"))
        db.flush()
        result = {"clinical": state_data(state)}
        if data.status == "reviewed":
            report = ClinicalReport(id=str(uuid.uuid4()), screening_id=case_id,
                                    version=state.version, snapshot_json=json.dumps(case_data(db, s, True)))
            db.add(report)
            result["report_id"] = report.id
        return result
    return run_mutation(db, user, data.event_id, f"{case_id}/review", data.model_dump(mode="json"), action)

@router.post("/cases/{case_id}/investigations")
def create_order(case_id: str, data: Order, user=Depends(doctor), db: Session = Depends(get_db)):
    require_screening(db, user, case_id)
    def action():
        obj = Investigation(id=str(uuid.uuid4()), screening_id=case_id, kind=data.kind, notes=data.notes)
        db.add(obj); db.flush()
        event(db, case_id, user, "investigation_requested", {"id": obj.id, "kind": obj.kind})
        return order_data(obj)
    return run_mutation(db, user, data.event_id, f"{case_id}/orders", data.model_dump(mode="json"), action)

@router.post("/cases/{case_id}/investigations/{order_id}")
def change_order(case_id: str, order_id: str, data: OrderUpdate, user=Depends(doctor), db: Session = Depends(get_db)):
    require_screening(db, user, case_id)
    def action():
        obj = db.query(Investigation).filter_by(id=order_id, screening_id=case_id).first()
        if not obj: raise HTTPException(404, "Investigation not found.")
        allowed = {"requested": {"accepted", "cancelled"}, "accepted": {"result_received", "cancelled"},
                   "result_received": {"reviewed"}, "reviewed": set(), "cancelled": set()}
        if data.status not in allowed[obj.status]:
            raise HTTPException(409, "Invalid investigation transition.")
        changed = db.execute(update(Investigation).where(
            Investigation.id == order_id, Investigation.version == data.expected_version
        ).values(status=data.status, notes=data.notes, version=data.expected_version+1))
        if changed.rowcount != 1: raise HTTPException(409, "Investigation changed.")
        db.expire(obj)
        event(db, case_id, user, "investigation_updated", {"id": order_id, "status": data.status})
        return order_data(obj)
    return run_mutation(db, user, data.event_id, f"{case_id}/orders/{order_id}", data.model_dump(mode="json"), action)

@router.get("/changes")
def changes(after: int = 0, user=Depends(doctor), db: Session = Depends(get_db)):
    scope = visible_screenings(db, user).with_entities(Screening.id).subquery()
    rows = db.query(ClinicalChange).filter(ClinicalChange.screening_id.in_(scope.select()),
                                            ClinicalChange.sequence > max(after, 0)).order_by(ClinicalChange.sequence).limit(200).all()
    return {"events": [{"sequence": e.sequence, "case_id": e.screening_id, "kind": e.kind} for e in rows],
            "cursor": rows[-1].sequence if rows else max(after, 0)}

@router.get("/reports/{report_id}")
def report(report_id: str, user=Depends(doctor), db: Session = Depends(get_db)):
    r = db.get(ClinicalReport, report_id)
    if not r: raise HTTPException(404, "Report not found.")
    require_screening(db, user, r.screening_id)
    return {"id": r.id, "version": r.version, "created_at": r.created_at.isoformat(),
            "snapshot": json.loads(r.snapshot_json)}

def detect_document(data):
    if data.startswith(b"%PDF-"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted or len(reader.pages) > 20:
            raise ValueError("PDF must be unencrypted and at most 20 pages.")
        return "application/pdf"
    with Image.open(io.BytesIO(data)) as img:
        if img.format not in {"PNG", "JPEG"} or img.width * img.height > 25_000_000:
            raise ValueError("Only bounded PNG and JPEG images are supported.")
        fmt = img.format
        img.verify()
        return "image/png" if fmt == "PNG" else "image/jpeg"

@router.post("/cases/{case_id}/documents")
async def upload_document(case_id: str, file: UploadFile = File(...),
                          fields_json: str = Form("[]"), expected_sha256: str = Form(""),
                          user=Depends(authenticate), db: Session = Depends(get_db)):
    require_screening(db, user, case_id)
    data = await file.read(MAX_FILE+1)
    if not data or len(data) > MAX_FILE: raise HTTPException(413, "File must be 1 byte to 20 MB.")
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 and not secrets.compare_digest(expected_sha256.lower(), digest):
        raise HTTPException(422, "Checksum mismatch.")
    try:
        media = detect_document(data)
        fields_raw = json.loads(fields_json)
        if not isinstance(fields_raw, list) or len(fields_raw) > 100: raise ValueError()
        fields = [ExtractedField.model_validate(x).model_dump() for x in fields_raw]
    except Exception:
        raise HTTPException(422, "Invalid document or extracted fields.")
    old = db.query(ClinicalDocument).filter_by(screening_id=case_id, sha256=digest).first()
    if old: return {"document": document_data(old), "receipt": "already_received"}
    doc = ClinicalDocument(id=str(uuid.uuid4()), screening_id=case_id,
                           filename=Path(file.filename or "document").name[:240],
                           media_type=media, sha256=digest, size=len(data),
                           fields_json=json.dumps(fields, ensure_ascii=False))
    FILES.mkdir(parents=True, exist_ok=True)
    temp = FILES / (doc.id+".tmp")
    temp.write_bytes(data); os.replace(temp, FILES/doc.id)
    db.add(doc); event(db, case_id, user, "document_received", {"id": doc.id, "sha256": digest})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        (FILES/doc.id).unlink(missing_ok=True)
        old = db.query(ClinicalDocument).filter_by(screening_id=case_id, sha256=digest).first()
        if old: return {"document": document_data(old), "receipt": "already_received"}
        raise HTTPException(409, "Concurrent document upload. Retry.")
    return {"document": document_data(doc), "receipt": "received"}

@router.post("/documents/{document_id}/confirm")
def confirm_document(document_id: str, data: ConfirmDocument, user=Depends(authenticate), db: Session = Depends(get_db)):
    doc = db.get(ClinicalDocument, document_id)
    if not doc: raise HTTPException(404, "Document not found.")
    require_screening(db, user, doc.screening_id)
    changed = db.execute(update(ClinicalDocument).where(
        ClinicalDocument.id == doc.id, ClinicalDocument.version == data.expected_version
    ).values(fields_json=json.dumps([f.model_dump() for f in data.fields], ensure_ascii=False),
             verification="transcription_confirmed", confirmed_by=user.username,
             version=data.expected_version+1))
    if changed.rowcount != 1: raise HTTPException(409, "Document changed.")
    db.expire(doc); event(db, doc.screening_id, user, "transcription_confirmed", {"id": doc.id, "version": data.expected_version+1})
    db.commit()
    return document_data(doc)

@router.get("/documents/{document_id}/file")
def document_file(document_id: str, user=Depends(doctor), db: Session = Depends(get_db)):
    doc = db.get(ClinicalDocument, document_id)
    if not doc: raise HTTPException(404, "Document not found.")
    require_screening(db, user, doc.screening_id)
    path = FILES / doc.id
    if not path.is_file(): raise HTTPException(404, "Original file is unavailable.")
    return FileResponse(path, media_type=doc.media_type,
                        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                                 "Content-Security-Policy": "sandbox"})

from server.clinical_pacs import router as imaging_router
router.include_router(imaging_router)

def install_clinical(target):
    target.include_router(router)
    if DIST.is_dir():
        target.mount("/doctor", StaticFiles(directory=DIST, html=True), name="clinical-ui")

    @target.middleware("http")
    async def private_clinical_responses(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/clinical"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

app = FastAPI(title="ShwaasAI Clinical Workspace", version="0.1.0")
install_clinical(app)

