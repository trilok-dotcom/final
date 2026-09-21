from pydantic import BaseModel, Field
from typing import Optional

class LocationPoint(BaseModel):
    lat: float = Field(..., description="Latitude coordinate", ge=-90.0, le=90.0)
    lng: float = Field(..., description="Longitude coordinate", ge=-180.0, le=180.0)
    address: Optional[str] = Field(None, description="Optional street address or land description")
    name: Optional[str] = Field(None, description="Optional waypoint name")

class Coordinates(BaseModel):
    lat: float
    lng: float
