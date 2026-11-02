"""
Database configuration and SQLAlchemy models for ShwaasAI persistence layer.
Uses SQLite for offline-first resilience.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DB_DIR = Path(__file__).parent.parent / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "shwaasai.db"

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(32), default="worker")  # "worker", "admin"
    full_name = Column(String(128), default="ASHA Worker")
    phc_center = Column(String(128), default="Primary Health Center")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    screenings = relationship("Screening", back_populates="user")

class Screening(Base):
    __tablename__ = "screenings"

    id = Column(String(64), primary_key=True, index=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    patient_code = Column(String(64), index=True, nullable=False)  # Anonymous code, e.g. PAT-RAM-0012
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    age = Column(Integer, nullable=False)
    sex = Column(String(32), default="prefer_not_to_say")
    village = Column(String(128), default="Unknown", index=True)
    
    # Answers stored as JSON string
    answers_json = Column(Text, nullable=False)
    
    # Clinical and Audio Scores
    clinical_score = Column(Integer, nullable=False)
    questionnaire_max = Column(Integer, default=18)
    audio_raw_score = Column(Float, nullable=False)
    audio_calibrated_score = Column(Float, nullable=False)
    
    # Final Routing
    tier = Column(String(32), nullable=False, index=True)
    pathway_code = Column(String(64), nullable=False)
    recommended_pathway = Column(Text, nullable=False)
    
    # Safety and flags
    red_flag_detected = Column(Boolean, default=False)
    high_risk_present = Column(Boolean, default=False)
    uncertain_symptoms_json = Column(Text, default="[]")
    
    # Optional Grad-CAM base64 data URI
    gradcam_image = Column(Text, nullable=True)
    
    # Privacy & Consent
    consent_given = Column(Boolean, default=True)

    user = relationship("User", back_populates="screenings")
    referral = relationship("Referral", back_populates="screening", uselist=False, cascade="all, delete-orphan")

    def get_answers(self):
        try:
            return json.loads(self.answers_json)
        except Exception:
            return {}

    def get_uncertain_symptoms(self):
        try:
            return json.loads(self.uncertain_symptoms_json)
        except Exception:
            return []

class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    screening_id = Column(String(64), ForeignKey("screenings.id"), unique=True, nullable=False)
    status = Column(String(32), default="pending", index=True)  # "pending", "tested", "lost"
    notes = Column(Text, default="")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    screening = relationship("Screening", back_populates="referral")

def init_db():
    Base.metadata.create_all(bind=engine)
