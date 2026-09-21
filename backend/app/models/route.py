from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from .location import LocationPoint

RiskLevel = Literal['low', 'moderate', 'high', 'critical']

class RoadCondition(BaseModel):
    id: str
    name: str
    status: Literal['passable', 'blocked', 'flooded', 'damaged']
    description: Optional[str] = None

class RouteStep(BaseModel):
    id: str
    instruction: str
    distance_meters: float
    duration_seconds: float
    road_name: str
    turn_type: Literal['straight', 'left', 'right', 'u_turn', 'arrive']
    risk_level: RiskLevel = 'low'
    location: Optional[List[float]] = None # [lng, lat]

class RouteGeometry(BaseModel):
    type: Literal['LineString'] = 'LineString'
    coordinates: List[List[float]] # List of [lng, lat] coordinate pairs

class RouteRequest(BaseModel):
    start: LocationPoint
    destination: LocationPoint
    incident_id: Optional[str] = None
    vehicle_type: Optional[str] = "rescue_vehicle"

class RouteResponse(BaseModel):
    id: str
    total_distance_meters: float
    estimated_duration_seconds: float
    status: Literal['calculated', 'failed', 'no_path_found']
    risk_level: RiskLevel = 'low'
    steps: List[RouteStep]
    geometry: RouteGeometry
    road_conditions: List[RoadCondition] = []
    calculated_at: str
