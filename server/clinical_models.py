"""Additive tables; existing screenings and scoring remain unchanged."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, UniqueConstraint
from server.db import Base

def now():
    return datetime.now(timezone.utc)

class ClinicalCase(Base):
    __tablename__ = "clinical_cases"
    screening_id = Column(String(64), ForeignKey("screenings.id"), primary_key=True)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="awaiting_review")
    notes = Column(Text, nullable=False, default="")
    next_action = Column(Text, nullable=False, default="")
    reviewer = Column(String(64), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=now)

class Investigation(Base):
    __tablename__ = "clinical_investigations"
    id = Column(String(64), primary_key=True)
    screening_id = Column(String(64), ForeignKey("screenings.id"), nullable=False, index=True)
    kind = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="requested")
    notes = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=now)
    version = Column(Integer, nullable=False, default=1)

class ClinicalDocument(Base):
    __tablename__ = "clinical_documents"
    __table_args__ = (UniqueConstraint("screening_id", "sha256"),)
    id = Column(String(64), primary_key=True)
    screening_id = Column(String(64), ForeignKey("screenings.id"), nullable=False, index=True)
    filename = Column(String(240), nullable=False)
    media_type = Column(String(80), nullable=False)
    sha256 = Column(String(64), nullable=False)
    size = Column(Integer, nullable=False)
    fields_json = Column(Text, nullable=False, default="[]")
    verification = Column(String(32), nullable=False, default="needs_verification")
    confirmed_by = Column(String(64), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=now)

class ImagingInstance(Base):
    __tablename__ = "clinical_imaging"
    id = Column(String(64), primary_key=True)
    screening_id = Column(String(64), ForeignKey("screenings.id"), nullable=False, index=True)
    order_id = Column(String(64), ForeignKey("clinical_investigations.id"), nullable=False)
    sop_uid = Column(String(80), nullable=False, unique=True)
    series_uid = Column(String(80), nullable=False)
    study_uid = Column(String(80), nullable=False, index=True)
    orthanc_id = Column(String(80), nullable=False)
    sha256 = Column(String(64), nullable=False)
    patient_id = Column(String(128), nullable=False)
    identity_check = Column(String(32), nullable=False)
    created_at = Column(DateTime, nullable=False, default=now)

class ImagingStudy(Base):
    __tablename__ = "clinical_imaging_studies"
    study_uid = Column(String(80), primary_key=True)
    screening_id = Column(String(64), ForeignKey("screenings.id"), nullable=False)

class ClinicalMutation(Base):
    __tablename__ = "clinical_mutations"
    event_id = Column(String(64), primary_key=True)
    actor = Column(String(64), nullable=False)
    digest = Column(String(64), nullable=False)
    result_json = Column(Text, nullable=False)

class ClinicalChange(Base):
    __tablename__ = "clinical_changes"
    sequence = Column(Integer, primary_key=True, autoincrement=True)
    screening_id = Column(String(64), ForeignKey("screenings.id"), nullable=False, index=True)
    kind = Column(String(64), nullable=False)
    actor = Column(String(64), nullable=False)
    detail_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False, default=now)

class ClinicalReport(Base):
    __tablename__ = "clinical_reports"
    id = Column(String(64), primary_key=True)
    screening_id = Column(String(64), ForeignKey("screenings.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    snapshot_json = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=now)

