from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class ResourceAssignmentStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    RECOMMENDED = "RECOMMENDED"
    RESERVED = "RESERVED"
    DISPATCHED = "DISPATCHED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class ResourceOptimizationStatus(str, Enum):
    OPTIMAL = "OPTIMAL"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_RESOURCES = "INSUFFICIENT_RESOURCES"
    NO_SUITABLE_UNITS = "NO_SUITABLE_UNITS"
    CONFLICT = "CONFLICT"
    ALREADY_DISPATCHED = "ALREADY_DISPATCHED"


class ResourceAssignment(BaseModel):
    id: str
    incident_id: str
    dispatch_id: Optional[str] = None
    rescue_unit_id: str
    unit_type: str
    optimization_score: float = Field(..., ge=0.0, le=100.0)
    distance_meters: float
    estimated_duration_seconds: int
    average_confidence: float
    risk_level: str
    suitability_score: float
    availability_score: float
    eta_score: float
    route_score: float
    capability_score: float
    selection_reason: str
    status: ResourceAssignmentStatus
    created_at: str
    updated_at: str
