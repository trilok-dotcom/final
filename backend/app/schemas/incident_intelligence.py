from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.models.incident_intelligence import PriorityLevel, UrgencyLevel, IntelligenceRiskLevel


class ResourceRecommendationSchema(BaseModel):
    unit_type: str
    quantity: int = 1
    reason: str


class ScoringFactorSchema(BaseModel):
    name: str
    raw_score: float
    weight: float
    weighted_score: float
    reason: str


class IncidentIntelligenceResponse(BaseModel):
    incident_id: str
    incident_code: Optional[str] = None
    priority_score: float = Field(..., ge=0.0, le=100.0)
    priority: str
    risk_level: str
    urgency: str
    recommended_resources: List[ResourceRecommendationSchema]
    factors: List[ScoringFactorSchema]
    explanation: str
    analyzed_at: str
