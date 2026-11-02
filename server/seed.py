"""
Seeds demo users and 30 realistic screenings with referral records
for ShwaasAI testing and demo readiness.
"""

import uuid
import json
import random
from datetime import datetime, timedelta, timezone

from server.db import SessionLocal, init_db, User, Screening, Referral
from server.auth import hash_password
from server.schemas import TierEnum, PathwayCodeEnum

VILLAGES = ["Rampur", "Sundarpur", "Belagavi", "Kalyan"]
SEXES = ["male", "female", "prefer_not_to_say"]

TIER_CONFIGS = [
    {
        "tier": TierEnum.LOW,
        "pathway_code": PathwayCodeEnum.STANDARD_HYGIENE,
        "recommended": "Low immediate risk. Maintain standard respiratory hygiene.",
        "score_range": (0, 3),
        "audio_range": (0.02, 0.35),
        "red_flag": False,
        "high_risk": False,
        "referral_status": "tested",
        "notes": "Patient advised standard hygiene and warm fluids. Routine follow-up in 1 month."
    },
    {
        "tier": TierEnum.MODERATE,
        "pathway_code": PathwayCodeEnum.PHC_EVALUATION,
        "recommended": "Clinical evaluation recommended. Persistent cough warrants PHC visit.",
        "score_range": (4, 7),
        "audio_range": (0.45, 0.65),
        "red_flag": False,
        "high_risk": False,
        "referral_status": "pending",
        "notes": "ASHA worker scheduled appointment at Rampur PHC on Tuesday."
    },
    {
        "tier": TierEnum.HIGH,
        "pathway_code": PathwayCodeEnum.CBNAAT_REFERRAL,
        "recommended": "Urgent referral for CBNAAT testing recommended.",
        "score_range": (8, 14),
        "audio_range": (0.70, 0.92),
        "red_flag": False,
        "high_risk": True,
        "referral_status": "tested",
        "notes": "Sputum collected for GeneXpert / CBNAAT test at District TB Centre."
    },
    {
        "tier": TierEnum.URGENT,
        "pathway_code": PathwayCodeEnum.IMMEDIATE_TRIAGE,
        "recommended": "Immediate medical assessment required (hemoptysis detected).",
        "score_range": (6, 12),
        "audio_range": (0.50, 0.88),
        "red_flag": True,
        "high_risk": False,
        "referral_status": "tested",
        "notes": "Hemoptysis reported. Transported to Sub-District Hospital emergency unit."
    },
    {
        "tier": TierEnum.HIGH_RISK_SCREENING,
        "pathway_code": PathwayCodeEnum.HIGH_RISK_PATHWAY,
        "recommended": "High-risk profile detected (HIV/contact). Prioritized screening pathway recommended.",
        "score_range": (2, 3),
        "audio_range": (0.20, 0.40),
        "red_flag": False,
        "high_risk": True,
        "referral_status": "pending",
        "notes": "Household TB contact identified. Enrolled in household prophylactic screening."
    },
]

def seed_database():
    print("🌱 Seeding ShwaasAI database...")
    init_db()
    db = SessionLocal()

    try:
        # 1. Clean existing records for idempotent runs
        db.query(Referral).delete()
        db.query(Screening).delete()
        db.query(User).delete()
        db.commit()

        # 2. Seed Users
        users = [
            User(
                username="asha_rani",
                hashed_password=hash_password("asha123"),
                role="worker",
                full_name="Rani Devi (ASHA)",
                phc_center="Rampur Community Health Centre"
            ),
            User(
                username="asha_priya",
                hashed_password=hash_password("asha123"),
                role="worker",
                full_name="Priya Sharma (ASHA)",
                phc_center="Sundarpur Sub-Centre"
            ),
            User(
                username="admin",
                hashed_password=hash_password("admin123"),
                role="admin",
                full_name="Dr. Alok Verma (MO)",
                phc_center="District TB Centre"
            ),
        ]
        db.add_all(users)
        db.commit()
        print(f"✅ Seeded {len(users)} users (asha_rani, asha_priya, admin).")

        # 3. Seed 30 Screenings & Referrals
        now = datetime.now(timezone.utc)
        screenings_list = []
        referrals_list = []

        for i in range(1, 31):
            config = TIER_CONFIGS[i % len(TIER_CONFIGS)]
            village = VILLAGES[i % len(VILLAGES)]
            sex = SEXES[i % len(SEXES)]
            age = random.randint(20, 72)
            created_time = now - timedelta(days=random.randint(0, 14), hours=random.randint(1, 23))

            screening_id = str(uuid.uuid4())
            patient_code = f"PAT-{village[:3].upper()}-{1000 + i}"

            score = random.randint(*config["score_range"])
            cal_audio = round(random.uniform(*config["audio_range"]), 4)
            raw_audio = round(max(0.01, cal_audio - random.uniform(0.02, 0.08)), 4)

            # Answers dict
            answers = {
                "cough_duration": 2 if score >= 2 else 0,
                "fever": 2 if score >= 4 else 0,
                "night_sweats": 2 if score >= 6 else 0,
                "weight_loss": 2 if score >= 8 else 0,
                "hemoptysis": 2 if config["red_flag"] else 0,
                "tb_contact": 2 if config["high_risk"] else 0,
                "diabetes": 2 if i % 4 == 0 else 0,
                "hiv": 2 if (config["high_risk"] and i % 3 == 0) else 0,
                "immunosuppression": 1 if i % 5 == 0 else 0,
                "silica_exposure": 1 if (village == "Kalyan" and i % 2 == 0) else 0,
            }

            uncertain = ["cough_duration"] if i % 7 == 0 else []

            # Assigned user
            assigned_user = users[0] if village in ["Rampur", "Kalyan"] else users[1]

            screening = Screening(
                id=screening_id,
                user_id=assigned_user.id,
                patient_code=patient_code,
                created_at=created_time,
                age=age,
                sex=sex,
                village=village,
                answers_json=json.dumps(answers),
                clinical_score=score,
                questionnaire_max=18,
                audio_raw_score=raw_audio,
                audio_calibrated_score=cal_audio,
                tier=config["tier"].value,
                pathway_code=config["pathway_code"].value,
                recommended_pathway=config["recommended"],
                red_flag_detected=config["red_flag"],
                high_risk_present=config["high_risk"],
                uncertain_symptoms_json=json.dumps(uncertain),
                gradcam_image=None,
                consent_given=True
            )
            screenings_list.append(screening)

            # Determine referral status variation
            ref_status = config["referral_status"]
            if i % 8 == 0:
                ref_status = "lost"
                ref_notes = "Patient moved to seasonal agricultural work; unable to contact for 2 weeks."
            else:
                ref_notes = config["notes"]

            referral = Referral(
                screening_id=screening_id,
                status=ref_status,
                notes=ref_notes,
                updated_at=created_time + timedelta(hours=random.randint(2, 48))
            )
            referrals_list.append(referral)

        db.add_all(screenings_list)
        db.add_all(referrals_list)
        db.commit()
        print(f"✅ Seeded {len(screenings_list)} screenings and referrals across {len(VILLAGES)} villages.")

    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
