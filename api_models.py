from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class MedicalData(BaseModel):
    condition: str = Field(default="Unknown", description="Primary medical condition")
    severity: str = Field(default="Unknown")
    urgency: str = Field(default="Stable")
    summary: str = Field(default="")

    model_config = {"extra": "allow"}

    @model_validator(mode="before")
    @classmethod
    def model_validate_legacy(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "condition" not in data and "diagnosis" in data:
                data["condition"] = data["diagnosis"]
            if "condition" not in data:
                data["condition"] = "Unknown"
        return data


class MatchRequest(BaseModel):
    medical_data: MedicalData
    origin_country: str = Field(default="Indonesia", description="Where the patient is flying from")
    user_origin: Optional[str] = Field(default=None, description="Optional user-origin city override")
    budget_local: float = Field(default=5000.0, description="Patient's maximum budget in local currency")
    currency: str = Field(default="USD", description="Currency of the budget")
    preferred_month: str = Field(default="Next Month", description="User's preferred month for travel")
    preferred_language: str = Field(default="English", description="Target language for outputs")
    user_priority_preference: str = Field(default="balanced", description="How to rank accessible packages")
    manual_override: bool = Field(default=False, description="Bypass accessibility reranking and preserve raw semantic hits")
    session_id: Optional[str] = Field(default=None, description="Session ID for memory and regeneration")
    rejected_hospitals: List[str] = Field(default_factory=list, description="Hospital names already rejected by user")


class LayerRequest(BaseModel):
    medical_data: MedicalData
    origin_country: str = Field(default="Indonesia", description="Where the patient is flying from")
    language: Optional[str] = "en"


class CombinePackageRequest(BaseModel):
    hospital: Dict[str, Any]
    logistics_data: Dict[str, Any]
    flight: Optional[Dict[str, Any]] = None
    charity: Optional[Dict[str, Any]] = None
    origin_country: str = Field(default="Indonesia")
    budget_usd: int = Field(default=5000)


class UserCreate(BaseModel):
    username: str
    password: str


class SaveSelectionRequest(BaseModel):
    doctor_id: str
    charity_id: str


class TranslateTemplateRequest(BaseModel):
    template_key: str
    target_language: str


class TranslateTextRequest(BaseModel):
    text: str
    target_language: str


class TranslateBatchRequest(BaseModel):
    texts: Dict[str, str]
    target_language: str


class DoctorProfileRequest(BaseModel):
    doctor_name: str
    hospital_name: str


class GenerateLetterRequest(BaseModel):
    template_key: str
    user_data: Dict[str, Any] = Field(default_factory=dict)
    medical_data: Optional[Dict[str, Any]] = None
    package_data: Optional[Dict[str, Any]] = None
    target_language: Optional[str] = None
