from fastapi import APIRouter
from app.models.route import RouteRequest, RouteResponse
from app.services.routing_service import routing_service

router = APIRouter()

@router.post("/route", response_model=RouteResponse, summary="Calculate Rescue Route")
async def calculate_route(request: RouteRequest):
    """
    Calculates a real road-following rescue route using OSRM geographic routing data.
    Returns GeoJSON LineString geometry, total distance, duration, and turn-by-turn maneuvers.
    """
    return await routing_service.calculate_route(request)
