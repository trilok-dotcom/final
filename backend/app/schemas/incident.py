from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from app.models.incident import IncidentType, IncidentSeverity, IncidentStatus


class IncidentCreate(BaseModel):
    incident_type: str
    severity: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    location_name: Optional[str] = None
    description: Optional[str] = None
    reported_by: Optional[str] = "DISPATCH_CENTER"

    @field_validator("incident_type")

    def validate_type(cls, v: str) -> str:
        v_upper = v.upper().strip()
        valid = [t.value for t in IncidentType] + ["FLOOD", "BUILDING_COLLAPSE", "LANDSLIDE", "STORM", "TSUNAMI"]
        if v_upper not in valid:
            # Map legacy lowercase to enum
            mapping = {
                "FLOOD": "FLOOD",
                "BUILDING_COLLAPSE": "COLLAPSED_BUILDING",
                "FIRE": "FIRE",
                "EARTHQUAKE": "EARTHQUAKE",
                "ACCIDENT": "ACCIDENT",
                "MEDICAL": "MEDICAL",
            }
            if v_upper in mapping:
                return mapping[v_upper]
            raise ValueError(f"Invalid incident_type: '{v}'. Must be one of {[t.value for t in IncidentType]}")
        return v_upper

    @field_validator("severity")

    def validate_severity(cls, v: str) -> str:
        v_upper = v.upper().strip()
        # Map legacy 'MODERATE' to 'MEDIUM' if needed
        if v_upper == "MODERATE":
            return "MEDIUM"
        if v_upper not in [s.value for s in IncidentSeverity]:
            raise ValueError(f"Invalid severity: '{v}'. Must be one of {[s.value for s in IncidentSeverity]}")
        return v_upper


class IncidentUpdate(BaseModel):
    incident_type: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    location_name: Optional[str] = None
    description: Optional[str] = None
    assigned_unit_id: Optional[str] = None

    @field_validator("status")

    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_upper = v.upper().strip()
        # Map legacy status
        mapping = {
            "UNASSIGNED": "REPORTED",
            "IN_PROGRESS": "ACTIVE",
            "DISPATCHED": "DISPATCHING",
        }
        v_mapped = mapping.get(v_upper, v_upper)
        if v_mapped not in [s.value for s in IncidentStatus]:
            raise ValueError(f"Invalid status: '{v}'. Must be one of {[s.value for s in IncidentStatus]}")
        return v_mapped
