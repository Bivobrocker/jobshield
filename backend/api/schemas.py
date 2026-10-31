
from pydantic import BaseModel, Field
from typing import Optional, Any


class JobAnalysisRequest(BaseModel):
    job_text: str = Field(
        ..., min_length=10, max_length=20000
    )

    company_name: Optional[str] = None
    company_website: Optional[str] = None
    job_url: Optional[str] = None
    recruiter_email: Optional[str] = None

    # Official vacancy verification details
    job_title: Optional[str] = None
    job_location: Optional[str] = None
    job_id: Optional[str] = None
    careers_url: Optional[str] = None


class ModelResult(BaseModel):
    prediction: str
    score: Optional[float] = None
    score_type: str = "uncalibrated_model_score"


class EvidenceItem(BaseModel):
    category: str
    status: str
    severity: str
    finding: str
    source_url: Optional[str] = None
    checked_at: str


class JobAnalysisResponse(BaseModel):
    analysis_id: str
    verdict: str
    model: Optional[ModelResult] = None

    # Complete official vacancy verification result
    vacancy_verification: Optional[dict[str, Any]] = None

    evidence: list[EvidenceItem] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
