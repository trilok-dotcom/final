from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class PriorityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class UrgencyLevel(str, Enum):
    IMMEDIATE = "IMMEDIATE"
    URGENT = "URGENT"
    PRIORITY = "PRIORITY"
    ROUTINE = "ROUTINE"


class IntelligenceRiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ResourceRecommendation(BaseModel):
    unit_type: str
    quantity: int = 1
    reason: str


class ScoringFactor(BaseModel):
    name: str
    raw_score: float
    weight: float
    weighted_score: float
    reason: str


class IncidentIntelligence(BaseModel):
    incident_id: str
    incident_code: Optional[str] = None
    priority_score: float = Field(..., ge=0.0, le=100.0)
    priority: PriorityLevel
    risk_level: IntelligenceRiskLevel
    urgency: UrgencyLevel
    recommended_resources: List[ResourceRecommendation]
    factors: List[ScoringFactor]
    explanation: str
    analyzed_at: str
