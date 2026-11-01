"""Transparent prototype routing. Rules are not a trained clinical risk model."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

RULES_VERSION = "demo-referral-rules-v1"

class Questionnaire(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    age: int | None = Field(default=None, ge=0, le=120)
    sex: Literal["male", "female", "other", "prefer_not_to_say"] = "prefer_not_to_say"
    cough_duration_days: int | None = Field(default=None, ge=0, le=36500)
    fever: bool | None = None
    night_sweats: bool | None = None
    weight_loss: bool | None = None
    hemoptysis: bool | None = None
    tb_contact: bool | None = None
    diabetes: bool | None = None
    hiv: bool | None = None
    immunosuppression: bool | None = None
    silica_exposure: bool | None = None

def route(answers: Questionnaire, acoustic_flag: bool | None = None):
    unknown = [name for name, value in answers.model_dump().items()
               if value is None and name != "sex"]
    clinical = []
    if answers.cough_duration_days is not None and answers.cough_duration_days >= 14:
        clinical.append("persistent_cough_reported")
    for name in ("fever", "night_sweats", "weight_loss", "tb_contact", "diabetes",
                 "hiv", "immunosuppression", "silica_exposure"):
        if getattr(answers, name) is True:
            clinical.append(f"{name}_reported")
    if answers.hemoptysis is True:
        priority, action = "URGENT", "Arrange prompt medical assessment for reported blood in cough."
        clinical.append("hemoptysis_reported")
    elif answers.age is not None and answers.age < 18:
        priority, action = "CLINICAL_REVIEW", "Use the pediatric clinical assessment pathway."
        clinical.append("pediatric_pathway")
    elif clinical:
        priority, action = "CLINICAL_REVIEW", "Arrange clinical assessment and document the reported factors."
    elif acoustic_flag is True:
        priority, action = "CLINICAL_REVIEW", "Review the acoustic flag alongside the history."
    elif unknown:
        priority, action = "COMPLETE_QUESTIONNAIRE", "Clarify missing history or record that the person declined."
    else:
        priority, action = "NO_TRIGGER_IDENTIFIED", "No configured referral trigger; seek review for ongoing concerns."
    reasons = clinical + (["acoustic_flag"] if acoustic_flag is True else [])
    return {
        "priority": priority, "reasons": reasons, "unknown_answers": unknown,
        "recommended_pathway": action, "rules_version": RULES_VERSION,
        "clinical_trigger": bool(clinical),
        "channels_disagree": bool(clinical) != acoustic_flag if acoustic_flag is not None else None,
    }
