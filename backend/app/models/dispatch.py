from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class DispatchStatus(str, Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Dispatch(BaseModel):
    id: str
    incident_id: str
    rescue_unit_id: str
    status: str
    assigned_at: str
    dispatched_at: Optional[str] = None
    en_route_at: Optional[str] = None
    arrived_at: Optional[str] = None
    completed_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    route_id: Optional[str] = None
    distance_meters: float = 0.0
    estimated_duration_seconds: int = 0
    average_confidence: float = 1.0
    risk_level: str = "low"
    route_geometry: Optional[Dict[str, Any]] = None
    route_steps: Optional[List[Dict[str, Any]]] = None
    created_at: str
    updated_at: str
