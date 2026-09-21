from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from app.models.rescue_unit import RescueUnitType, RescueUnitStatus


class RescueUnitCreate(BaseModel):
    unit_code: str = Field(..., min_length=2, max_length=20)
    unit_type: str
    status: Optional[str] = "AVAILABLE"
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    name: str = Field(..., min_length=2)
    crew_size: int = Field(default=1, ge=1)
    capabilities: List[str] = Field(default_factory=list)
    current_incident_id: Optional[str] = None

    @field_validator("unit_type")

    def validate_type(cls, v: str) -> str:
        v_upper = v.upper().strip()
        # Map legacy lowercase or alternate names
        mapping = {
            "AMBULANCE": "AMBULANCE",
            "FIRE_TRUCK": "FIRE_TRUCK",
            "POLICE": "POLICE",
            "RESCUE_TEAM": "RESCUE_TEAM",
            "DISASTER_RESPONSE": "DISASTER_RESPONSE",
            "HELICOPTER": "DISASTER_RESPONSE",
            "MEDICAL_TEAM": "AMBULANCE",
            "HEAVY_RESCUE": "RESCUE_TEAM",
            "WATERCRAFT": "RESCUE_TEAM",
            "ATV": "RESCUE_TEAM",
        }
        v_mapped = mapping.get(v_upper, v_upper)
        if v_mapped not in [t.value for t in RescueUnitType]:
            raise ValueError(f"Invalid unit_type: '{v}'. Must be one of {[t.value for t in RescueUnitType]}")
        return v_mapped

    @field_validator("status")

    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return "AVAILABLE"
        v_upper = v.upper().strip()
        if v_upper not in [s.value for s in RescueUnitStatus]:
            raise ValueError(f"Invalid status: '{v}'. Must be one of {[s.value for s in RescueUnitStatus]}")
        return v_upper


class RescueUnitUpdate(BaseModel):
    unit_type: Optional[str] = None
    status: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    name: Optional[str] = None
    crew_size: Optional[int] = Field(None, ge=1)
    capabilities: Optional[List[str]] = None
    current_incident_id: Optional[str] = None

    @field_validator("status")

    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_upper = v.upper().strip()
        if v_upper not in [s.value for s in RescueUnitStatus]:
            raise ValueError(f"Invalid status: '{v}'. Must be one of {[s.value for s in RescueUnitStatus]}")
        return v_upper


class RescueUnitStatusUpdate(BaseModel):
    status: str

    @field_validator("status")

    def validate_status(cls, v: str) -> str:
        v_upper = v.upper().strip()
        if v_upper not in [s.value for s in RescueUnitStatus]:
            raise ValueError(f"Invalid status: '{v}'. Must be one of {[s.value for s in RescueUnitStatus]}")
        return v_upper
