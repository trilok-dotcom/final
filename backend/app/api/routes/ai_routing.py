from typing import List, Optional, Dict, Any, Literal
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.models.location import LocationPoint
from app.services.emergency_routing_service import emergency_routing_service
from app.utils.logging import get_logger

logger = get_logger("api.ai_routing")
router = APIRouter()


class AIRouteRequest(BaseModel):
    start: LocationPoint = Field(..., description="Starting origin geographic location point")
    destination: LocationPoint = Field(..., description="Target destination geographic location point")
    vehicle_type: Optional[str] = Field("ambulance", description="Vehicle type ('ambulance', 'fire_truck', 'rescue', 'police')")
    avoid_low_confidence: Optional[bool] = Field(True, description="Penalize low-confidence AI road segments")


class SnappedPointDetail(BaseModel):
    lat: float
    lng: float
    distance_to_road_meters: float


class RouteStepDetail(BaseModel):
    id: str
    instruction: str
    distance_meters: float
    duration_seconds: int
    road_name: str
    turn_type: str
    location: List[float]  # [lng, lat]


class RouteGeometryDetail(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: List[List[float]]  # List of [lng, lat] GeoJSON pairs


class AIRouteResponse(BaseModel):
    success: bool = True
    route_id: str = Field(..., description="Unique generated route ID")
    status: str = Field("calculated", description="Route calculation status ('calculated', 'off_road', 'no_path_found', 'out_of_bounds')")
    routing_engine: str = Field("resqroute_ai_graph", description="Name of the routing engine used")
    total_distance_meters: float = Field(..., description="Total route length in meters")
    estimated_duration_seconds: int = Field(..., description="Estimated travel time in seconds")
    average_confidence: float = Field(..., description="Mean AI segmentation probability confidence along route (0-1)")
    risk_level: str = Field(..., description="Risk assessment level ('low', 'moderate', 'high')")
    snapped_start: SnappedPointDetail = Field(..., description="Start location snapped onto AI road network")
    snapped_destination: SnappedPointDetail = Field(..., description="Destination location snapped onto AI road network")
    geometry: RouteGeometryDetail = Field(..., description="GeoJSON LineString route polyline")
    steps: List[RouteStepDetail] = Field(..., description="Turn-by-turn maneuver instructions")


class AIRouteErrorResponse(BaseModel):
    success: bool = False
    status: str
    message: str


@router.post(
    "/route",
    response_model=AIRouteResponse,
    responses={
        400: {"model": AIRouteErrorResponse, "description": "Invalid coordinates, out-of-bounds, or off-road location"},
        404: {"model": AIRouteErrorResponse, "description": "No connected AI road route exists between points"},
    },
    summary="RESQROUTE AI Emergency Shortest-Path Route Engine",
    description="Calculates real road-following emergency rescue route using U-Net extracted road graph and confidence-weighted Dijkstra algorithm.",
)
async def calculate_ai_route(request: AIRouteRequest):
    """Calculate shortest-path emergency route on AI extracted road network."""
    # 1. Validate inputs
    start_lat, start_lng = request.start.lat, request.start.lng
    dest_lat, dest_lng = request.destination.lat, request.destination.lng

    if not (-90.0 <= start_lat <= 90.0 and -180.0 <= start_lng <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid start coordinates: [{start_lat}, {start_lng}]",
        )

    if not (-90.0 <= dest_lat <= 90.0 and -180.0 <= dest_lng <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid destination coordinates: [{dest_lat}, {dest_lng}]",
        )

    # 2. Call Emergency Routing Service
    try:
        result = emergency_routing_service.calculate_emergency_route(
            start_lat=start_lat,
            start_lng=start_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            start_name=request.start.name or request.start.address,
            dest_name=request.destination.name or request.destination.address,
            vehicle_type=request.vehicle_type or "ambulance",
            avoid_low_confidence=bool(request.avoid_low_confidence),
        )
    except Exception as e:
        logger.error(f"Unexpected emergency routing failure: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Emergency routing calculation failed: {str(e)}",
        )

    # 3. Handle service error responses
    if not result.get("success"):
        res_status = result.get("status", "error")
        msg = result.get("message", "Route calculation failed")

        if res_status in ("off_road", "out_of_bounds"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "status": res_status, "message": msg},
            )
        elif res_status == "no_path_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "status": res_status, "message": msg},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"success": False, "status": res_status, "message": msg},
            )

    return result
