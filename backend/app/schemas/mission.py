from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any


class LocationUpdatePayload(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, description="Rescue unit current latitude (-90 to 90)")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Rescue unit current longitude (-180 to 180)")
    speed_kmh: Optional[float] = Field(default=0.0, ge=0.0, le=200.0, description="Current speed in km/h")
    heading_degrees: Optional[float] = Field(default=0.0, ge=0.0, le=360.0, description="Compass direction heading (0 to 360)")


class LiveUnitInfo(BaseModel):
    id: str
    code: str
    type: str
    name: Optional[str] = None
    lat: float
    lng: float
    speed_kmh: float = 0.0
    heading_degrees: float = 0.0


class LiveIncidentInfo(BaseModel):
    id: str
    code: Optional[str] = None
    lat: float
    lng: float
    location_name: Optional[str] = None


class LiveMissionResponse(BaseModel):
    dispatch_id: str
    status: str
    unit: LiveUnitInfo
    incident: LiveIncidentInfo
    distance_remaining_meters: float
    eta_seconds: int
    progress_percent: float
    risk_level: str = "low"
    average_ai_confidence: float = 1.0
    route_geometry: Optional[Dict[str, Any]] = None
