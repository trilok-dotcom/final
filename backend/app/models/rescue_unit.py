from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class RescueUnitType(str, Enum):
    AMBULANCE = "AMBULANCE"
    FIRE_TRUCK = "FIRE_TRUCK"
    POLICE = "POLICE"
    RESCUE_TEAM = "RESCUE_TEAM"
    DISASTER_RESPONSE = "DISASTER_RESPONSE"


class RescueUnitStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    DISPATCHED = "DISPATCHED"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    RETURNING = "RETURNING"
    OFFLINE = "OFFLINE"


class RescueUnit(BaseModel):
    id: str
    unit_code: str
    unit_type: str
    status: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    name: str
    crew_size: int = Field(default=1, ge=1)
    capabilities: List[str] = Field(default_factory=list)
    current_incident_id: Optional[str] = None
    created_at: str
    updated_at: str
