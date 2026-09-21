from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


class IncidentType(str, Enum):
    FIRE = "FIRE"
    MEDICAL = "MEDICAL"
    ACCIDENT = "ACCIDENT"
    FLOOD = "FLOOD"
    COLLAPSED_BUILDING = "COLLAPSED_BUILDING"
    EARTHQUAKE = "EARTHQUAKE"
    MISSING_PERSON = "MISSING_PERSON"
    HAZMAT = "HAZMAT"
    OTHER = "OTHER"


class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(str, Enum):
    REPORTED = "REPORTED"
    VERIFIED = "VERIFIED"
    DISPATCHING = "DISPATCHING"
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class Incident(BaseModel):
    id: str
    incident_code: str
    incident_type: str
    severity: str
    status: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    location_name: Optional[str] = None
    description: Optional[str] = None
    reported_by: Optional[str] = "DISPATCH_CENTER"
    assigned_unit_id: Optional[str] = None
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None
