from pydantic import BaseModel
from typing import Optional
from enum import Enum


class MissionEventType(str, Enum):
    MISSION_DISPATCHED = "MISSION_DISPATCHED"
    MISSION_EN_ROUTE = "MISSION_EN_ROUTE"
    MISSION_ON_SCENE = "MISSION_ON_SCENE"
    MISSION_COMPLETED = "MISSION_COMPLETED"
    MISSION_CANCELLED = "MISSION_CANCELLED"
    MISSION_UPDATE = "MISSION_UPDATE"


class MissionUpdate(BaseModel):
    id: str
    dispatch_id: str
    rescue_unit_id: str
    incident_id: str
    latitude: float
    longitude: float
    status: str
    distance_remaining_meters: float = 0.0
    eta_seconds: int = 0
    progress_percent: float = 0.0
    speed_kmh: float = 0.0
    heading_degrees: float = 0.0
    timestamp: str
