from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ResourceRequirementSchema(BaseModel):
    unit_type: str
    required: int
    available: int
    selected: int


class FactorBreakdownSchema(BaseModel):
    eta_score: float
    route_safety_score: float
    ai_confidence_score: float
    capability_score: float
    availability_score: float
    operational_score: float


class CandidateUnitSchema(BaseModel):
    rescue_unit_id: str
    unit_code: str
    unit_name: str
    unit_type: str
    status: str
    optimization_score: float
    distance_meters: float
    estimated_duration_seconds: int
    average_confidence: float
    risk_level: str
    is_selected: bool
    selection_reason: str
    factor_breakdown: FactorBreakdownSchema
    route_geometry: Optional[Dict[str, Any]] = None


class SelectedUnitSchema(BaseModel):
    rescue_unit_id: str
    unit_code: str
    unit_name: str
    unit_type: str
    optimization_score: float
    distance_meters: float
    estimated_duration_seconds: int
    average_confidence: float
    risk_level: str
    selection_reason: str
    factor_breakdown: FactorBreakdownSchema
    route_geometry: Optional[Dict[str, Any]] = None


class ResourceOptimizationResponse(BaseModel):
    success: bool
    incident_id: str
    incident_code: Optional[str] = None
    resource_status: str
    required_resources: List[ResourceRequirementSchema]
    selected_units: List[SelectedUnitSchema]
    candidate_units: List[CandidateUnitSchema]
    optimization_summary: str
    analyzed_at: str


class OptimizedDispatchResponse(BaseModel):
    success: bool
    incident_id: str
    incident_code: Optional[str] = None
    dispatched_units_count: int
    dispatch_ids: List[str]
    dispatches: List[Dict[str, Any]]
    message: str
