"""
Pydantic schemas and enums matching the locked API Contract for ShwaasAI.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class TierEnum(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    HIGH_RISK_SCREENING = "HIGH_RISK_SCREENING"
    URGENT = "URGENT"

class PathwayCodeEnum(str, Enum):
    STANDARD_HYGIENE = "STANDARD_HYGIENE"
    PHC_EVALUATION = "PHC_EVALUATION"
    CBNAAT_REFERRAL = "CBNAAT_REFERRAL"
    HIGH_RISK_PATHWAY = "HIGH_RISK_PATHWAY"
    IMMEDIATE_TRIAGE = "IMMEDIATE_TRIAGE"
    PEDIATRIC_PATHWAY = "PEDIATRIC_PATHWAY"

class ReferralStatusEnum(str, Enum):
    PENDING = "pending"
    TESTED = "tested"
    LOST = "lost"

# --- AUTH SCHEMAS ---
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    full_name: str
    role: str
    phc_center: str

# --- SCREENING SCHEMAS ---
class Demographics(BaseModel):
    age: int
    sex: str = "prefer_not_to_say"
    village: str = "Unknown"
    bias_note: str = "Excluded from scoring to prevent algorithmic bias."

class AudioModelOutput(BaseModel):
    target: str = "respiratory_abnormality_proxy"
    raw_score: float
    calibrated_score: float
    tb_probability_validated: bool = False

class FusionOutput(BaseModel):
    status: str = "finalized"
    tier: TierEnum

class ScreeningResponse(BaseModel):
    status: str = "success"
    session_id: str
    patient_code: str
    patient_demographics: Demographics
    questionnaire_score: int
    questionnaire_max: int = 18
    red_flag_detected: bool
    high_risk_factors_present: bool
    uncertain_symptoms: List[str] = []
    audio_model: AudioModelOutput
    fusion: FusionOutput
    pathway_code: PathwayCodeEnum
    recommended_pathway: str
    clinical_note: str = "This is a screening support tool, not a diagnostic. Final decision requires clinician review."
    gradcam_image: Optional[str] = None
    created_at: Optional[datetime] = None

class ScreeningListItem(BaseModel):
    id: str
    patient_code: str
    created_at: datetime
    age: int
    sex: str
    village: str
    clinical_score: int
    audio_calibrated_score: float
    tier: TierEnum
    pathway_code: PathwayCodeEnum
    referral_status: ReferralStatusEnum
    has_gradcam: bool

# --- REFERRAL SCHEMAS ---
class ReferralUpdateRequest(BaseModel):
    status: ReferralStatusEnum
    notes: Optional[str] = None

class ReferralResponse(BaseModel):
    screening_id: str
    status: ReferralStatusEnum
    notes: str
    updated_at: datetime

# --- STATS SCHEMAS ---
class StatsResponse(BaseModel):
    total_screenings: int
    tier_counts: Dict[str, int]
    referral_counts: Dict[str, int]
    referral_completion_rate: float
    screenings_by_village: Dict[str, int]
