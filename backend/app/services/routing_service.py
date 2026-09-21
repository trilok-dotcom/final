import httpx
import uuid
from datetime import datetime
from fastapi import HTTPException, status
from app.config import settings
from app.models.route import RouteRequest, RouteResponse, RouteStep, RouteGeometry
from app.utils.logging import get_logger

logger = get_logger("routing_service")

class RoutingService:
    def __init__(self):
        self.base_url = settings.OSRM_BASE_URL.rstrip('/')

    async def calculate_route(self, request: RouteRequest) -> RouteResponse:
        start_lat = request.start.lat
        start_lng = request.start.lng
        dest_lat = request.destination.lat
        dest_lng = request.destination.lng

        # Validate coordinates
        if not (-90.0 <= start_lat <= 90.0 and -180.0 <= start_lng <= 180.0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid start coordinates: [{start_lat}, {start_lng}]"
            )
        if not (-90.0 <= dest_lat <= 90.0 and -180.0 <= dest_lng <= 180.0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid destination coordinates: [{dest_lat}, {dest_lng}]"
            )

        # Build OSRM request URL
        # Format: /route/v1/driving/{lng1},{lat1};{lng2},{lat2}?overview=full&geometries=geojson&steps=true
        osrm_url = f"{self.base_url}/route/v1/driving/{start_lng},{start_lat};{dest_lng},{dest_lat}?overview=full&geometries=geojson&steps=true"
        logger.info(f"Requesting OSRM route: [{start_lat}, {start_lng}] -> [{dest_lat}, {dest_lng}]")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(osrm_url)
                if response.status_code != 200:
                    logger.error(f"OSRM service error status: {response.status_code}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Routing provider service error or unavailable."
                    )
                data = response.json()
        except httpx.TimeoutException:
            logger.error("OSRM service request timed out.")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Routing provider request timed out. Please try again."
            )
        except httpx.RequestError as e:
            logger.error(f"OSRM connection failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to reach routing provider service."
            )

        if data.get("code") != "Ok" or not data.get("routes"):
            logger.warning(f"No route found by OSRM: {data.get('code')}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No navigable road route found between selected points."
            )

        primary_route = data["routes"][0]
        total_distance = float(primary_route.get("distance", 0.0))
        total_duration = float(primary_route.get("duration", 0.0))
        geometry_data = primary_route.get("geometry", {})
        raw_coordinates = geometry_data.get("coordinates", [])

        # Parse steps and build turn-by-turn directions
        parsed_steps: List[RouteStep] = []
        legs = primary_route.get("legs", [])
        step_index = 1

        for leg in legs:
            osrm_steps = leg.get("steps", [])
            for s in osrm_steps:
                maneuver = s.get("maneuver", {})
                m_type = maneuver.get("type", "turn")
                modifier = maneuver.get("modifier", "")
                road_name = s.get("name") or "Road"
                distance = float(s.get("distance", 0.0))
                duration = float(s.get("duration", 0.0))
                loc = maneuver.get("location", [0.0, 0.0])

                # Determine turn_type
                turn_type = "straight"
                if m_type == "arrive":
                    turn_type = "arrive"
                elif "left" in modifier:
                    turn_type = "left"
                elif "right" in modifier:
                    turn_type = "right"
                elif "u_turn" in modifier or "uturn" in modifier:
                    turn_type = "u_turn"

                # Generate clean human instruction
                instruction = self._format_instruction(m_type, modifier, road_name)

                parsed_steps.append(
                    RouteStep(
                        id=f"step-{step_index}",
                        instruction=instruction,
                        distance_meters=round(distance, 1),
                        duration_seconds=round(duration, 1),
                        road_name=road_name,
                        turn_type=turn_type,
                        risk_level='low',
                        location=loc
                    )
                )
                step_index += 1

        route_id = f"route-{uuid.uuid4().hex[:8]}"

        return RouteResponse(
            id=route_id,
            total_distance_meters=round(total_distance, 1),
            estimated_duration_seconds=round(total_duration, 1),
            status='calculated',
            risk_level='low',
            steps=parsed_steps,
            geometry=RouteGeometry(
                type='LineString',
                coordinates=raw_coordinates
            ),
            road_conditions=[],
            calculated_at=datetime.utcnow().isoformat() + "Z"
        )

    def _format_instruction(self, m_type: str, modifier: str, road_name: str) -> str:
        if m_type == "depart":
            return f"Head {modifier or 'on'} {road_name}"
        elif m_type == "arrive":
            return f"Arrive at rescue destination"
        elif m_type == "turn":
            mod_str = modifier.replace("_", " ") if modifier else ""
            return f"Turn {mod_str} onto {road_name}".strip()
        elif m_type == "new name" or m_type == "continue":
            return f"Continue onto {road_name}"
        elif m_type == "merge":
            return f"Merge onto {road_name}"
        elif m_type == "ramp":
            return f"Take ramp onto {road_name}"
        elif m_type == "roundabout":
            return f"At roundabout, take exit onto {road_name}"
        else:
            action = m_type.capitalize()
            mod = f" {modifier}" if modifier else ""
            return f"{action}{mod} onto {road_name}"

routing_service = RoutingService()
