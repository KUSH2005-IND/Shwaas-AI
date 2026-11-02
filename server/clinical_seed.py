"""Add fictional demo records without deleting or replacing existing data."""
import json
import os
import uuid
from datetime import timedelta

from server.db import SessionLocal, User, Screening, Referral, init_db
from server.auth import hash_password
from server.clinical_models import ClinicalCase, Investigation, ClinicalChange, now

def seed():
    password = os.getenv("SHWAAS_DEMO_PASSWORD", "")
    if len(password) < 12:
        raise SystemExit("Set SHWAAS_DEMO_PASSWORD to at least 12 characters. Demo data is fictional.")
    init_db()
    with SessionLocal() as db:
        facility = "ShwaasAI Demo PHC"
        for username, role, name in [("doctor_demo", "doctor", "Dr. Asha · Demo"),
                                     ("worker_demo", "worker", "Meera · Demo Volunteer")]:
            existing = db.query(User).filter_by(username=username).first()
            if existing:
                if existing.phc_center != facility or existing.role != role:
                    raise SystemExit(f"Refusing to replace an existing account: {username}")
            else:
                db.add(User(username=username, role=role, full_name=name, phc_center=facility,
                            hashed_password=hash_password(password)))
        db.flush()
        worker = db.query(User).filter_by(username="worker_demo").one()
        villages = ["Rampur", "Bishanpur", "Devgaon", "Kalyanpur", "Sundarpur", "Rampur", "Devgaon", "Bishanpur"]
        for i, village in enumerate(villages):
            sid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"shwaas-clinical-demo-{i}"))
            if db.get(Screening, sid): continue
            tier = ["URGENT", "HIGH", "MODERATE", "LOW", "MODERATE", "LOW", "MODERATE", "HIGH"][i]
            answers = dict.fromkeys(["cough_duration", "fever", "night_sweats", "weight_loss", "hemoptysis",
                                     "tb_contact", "diabetes", "hiv", "immunosuppression", "silica_exposure"], 0)
            if tier != "LOW": answers.update(cough_duration=2, fever=2, night_sweats=1)
            if i == 0: answers["hemoptysis"] = 2
            db.add(Screening(id=sid, user_id=worker.id, patient_code=f"DEMO-{1042+i}", age=28+i*4,
                             sex="female" if i%2 else "male", village=village,
                             created_at=now()-timedelta(minutes=18+i*43), answers_json=json.dumps(answers),
                             clinical_score=8 if tier in {"HIGH", "URGENT"} else 4 if tier=="MODERATE" else 0,
                             questionnaire_max=18, audio_raw_score=.62, audio_calibrated_score=.58,
                             tier=tier, pathway_code="PHC_EVALUATION", recommended_pathway="Fictional demo pathway. Clinician review required.",
                             red_flag_detected=i==0, high_risk_present=i==2, consent_given=True,
                             uncertain_symptoms_json=json.dumps(["night_sweats"] if tier!="LOW" else [])))
            db.flush()
            db.add(Referral(screening_id=sid, status="pending", notes="Fictional demo record"))
            db.add(ClinicalChange(screening_id=sid, actor="worker_demo", kind="screening_received",
                                  detail_json='{"demo": true}'))
            if i in (1,2):
                db.add(ClinicalCase(screening_id=sid, version=1, status="awaiting_results", reviewer="doctor_demo",
                                    notes="DEMO: Investigations requested for clinician assessment.",
                                    next_action="Review the investigation results when received."))
                db.add(Investigation(id=str(uuid.uuid4()), screening_id=sid, kind="Chest X-ray" if i==1 else "Sputum NAAT",
                                     status="accepted", notes="Fictional demonstration order"))
        db.commit()
    print("Demo records added. Sign in at /doctor/ as doctor_demo. Existing passwords were not changed.")

if __name__ == "__main__": seed()
