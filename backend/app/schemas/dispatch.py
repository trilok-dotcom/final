from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from app.models.dispatch import DispatchStatus


class DispatchStatusUpdate(BaseModel):
    status: str

    @field_validator("status")

    def validate_status(cls, v: str) -> str:
        v_upper = v.upper().strip()
        if v_upper not in [s.value for s in DispatchStatus]:
            raise ValueError(f"Invalid dispatch status: '{v}'. Must be one of {[s.value for s in DispatchStatus]}")
        return v_upper


class DispatchResponse(BaseModel):
    success: bool = True
    dispatch_id: str
    incident_id: str
    rescue_unit_id: str
    rescue_unit_code: str
    rescue_unit_name: Optional[str] = None
    vehicle_type: Optional[str] = None
    status: str
    route: Optional[Dict[str, Any]] = None
    assigned_at: str
    dispatched_at: Optional[str] = None
    en_route_at: Optional[str] = None
    arrived_at: Optional[str] = None
    completed_at: Optional[str] = None
    cancelled_at: Optional[str] = None
