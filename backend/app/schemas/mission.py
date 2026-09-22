from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any


class LocationUpdatePayload(BaseModel):
    lat: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Rescue unit current latitude (-90 to 90)")
    lng: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Rescue unit current longitude (-180 to 180)")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Rescue unit current latitude (-90 to 90)")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Rescue unit current longitude (-180 to 180)")
    accuracy: Optional[float] = Field(default=None, ge=0.0, description="GPS location accuracy in meters (>=0)")
    location_accuracy: Optional[float] = Field(default=None, ge=0.0, description="GPS location accuracy in meters (>=0)")
    speed_kmh: Optional[float] = Field(default=0.0, ge=0.0, le=300.0, description="Current speed in km/h")
    heading_degrees: Optional[float] = Field(default=0.0, ge=0.0, le=360.0, description="Compass direction heading (0 to 360)")
    timestamp: Optional[str] = Field(default=None, description="ISO timestamp of location capture")
    mission_id: Optional[str] = Field(default=None, description="Dispatch / Mission ID")
    rescue_unit_id: Optional[str] = Field(default=None, description="Rescue Unit ID")

    @field_validator("latitude", mode="before")
    def populate_lat(cls, v, info):
        return v

    def get_lat(self) -> float:
        val = self.latitude if self.latitude is not None else self.lat
        if val is None:
            raise ValueError("Latitude is required (-90 to 90).")
        if not (-90.0 <= val <= 90.0):
            raise ValueError(f"Invalid latitude '{val}'. Must be between -90 and 90.")
        return float(val)

    def get_lng(self) -> float:
        val = self.longitude if self.longitude is not None else self.lng
        if val is None:
            raise ValueError("Longitude is required (-180 to 180).")
        if not (-180.0 <= val <= 180.0):
            raise ValueError(f"Invalid longitude '{val}'. Must be between -180 and 180.")
        return float(val)

    def get_accuracy(self) -> Optional[float]:
        acc = self.accuracy if self.accuracy is not None else self.location_accuracy
        if acc is not None and acc < 0:
            raise ValueError(f"Invalid accuracy '{acc}'. Must be >= 0.")
        return float(acc) if acc is not None else None


class LiveUnitInfo(BaseModel):
    id: str
    code: str
    type: str
    name: Optional[str] = None
    lat: float
    lng: float
    speed_kmh: float = 0.0
    heading_degrees: float = 0.0
    accuracy: Optional[float] = None


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
