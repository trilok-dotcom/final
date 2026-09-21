import asyncio
import json
import math
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.db.database import get_db_connection
from app.services.dispatch_service import dispatch_service
from app.services.incident_service import incident_service
from app.services.rescue_unit_service import rescue_unit_service
from app.services.emergency_routing_service import haversine_distance_km
from app.api.websocket import ws_manager
from app.utils.logging import get_logger

logger = get_logger("app.services.mission_tracking_service")

# Vehicle speeds in m/s for ETA calculations when speed_kmh == 0
VEHICLE_SPEEDS_MPS = {
    "AMBULANCE": 13.88,  # ~50 km/h
    "FIRE_TRUCK": 11.11, # ~40 km/h
    "RESCUE_TEAM": 12.5, # ~45 km/h
    "POLICE": 15.27,     # ~55 km/h
    "DEFAULT": 11.11,
}


def _bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate compass bearing in degrees between two geographic coordinates."""
    if abs(lat1 - lat2) < 1e-6 and abs(lon1 - lon2) < 1e-6:
        return 0.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)

    theta = math.atan2(y, x)
    bearing = (math.degrees(theta) + 360.0) % 360.0
    return round(bearing, 1)


class MissionTrackingService:
    def __init__(self):
        self._active_simulations: Dict[str, asyncio.Task] = {}

    @classmethod
    def _row_to_dict(cls, row) -> Dict[str, Any]:
        return dict(row)

    def update_location(
        self,
        dispatch_id: str,
        lat: float,
        lng: float,
        speed_kmh: float = 0.0,
        heading_degrees: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Update rescue unit location, calculate distance remaining, ETA, progress %,
        persist telemetry, and broadcast over WebSocket.
        """
        # 1. Fetch target dispatch
        disp = dispatch_service.get_dispatch(dispatch_id)
        if not disp:
            raise ValueError(f"Dispatch mission '{dispatch_id}' not found.")

        disp_status = disp["status"].upper()
        if disp_status in ("COMPLETED", "CANCELLED"):
            raise ValueError(f"Cannot update location for a {disp_status} dispatch mission.")

        unit = rescue_unit_service.get_rescue_unit(disp["rescue_unit_id"])
        incident = incident_service.get_incident(disp["incident_id"])

        if not unit or not incident:
            raise ValueError("Associated rescue unit or incident record missing.")

        inc_lat = float(incident["latitude"])
        inc_lng = float(incident["longitude"])

        # 2. Parse stored AI route geometry coordinates [[lng, lat], ...]
        route_geom = disp.get("route_geometry") or {}
        coords = route_geom.get("coordinates", [])

        total_route_dist_m = float(disp.get("distance_meters") or 0.0)

        # 3. Calculate distance remaining to incident
        if coords and len(coords) >= 2:
            # Find index of closest coordinate point along polyline
            min_dist_km = float("inf")
            closest_idx = 0
            for idx, (c_lng, c_lat) in enumerate(coords):
                d = haversine_distance_km(lat, lng, c_lat, c_lng)
                if d < min_dist_km:
                    min_dist_km = d
                    closest_idx = idx

            # Calculate remaining polyline segment lengths from closest_idx to end
            dist_rem_m = haversine_distance_km(lat, lng, coords[closest_idx][1], coords[closest_idx][0]) * 1000.0
            for k in range(closest_idx, len(coords) - 1):
                p1_lng, p1_lat = coords[k]
                p2_lng, p2_lat = coords[k + 1]
                dist_rem_m += haversine_distance_km(p1_lat, p1_lng, p2_lat, p2_lng) * 1000.0
        else:
            # Fallback to direct Haversine distance
            dist_rem_m = haversine_distance_km(lat, lng, inc_lat, inc_lng) * 1000.0

        dist_rem_m = round(max(0.0, dist_rem_m), 1)

        # 4. Calculate progress percentage
        if total_route_dist_m > 0:
            progress_pct = round(min(100.0, max(0.0, ((total_route_dist_m - dist_rem_m) / total_route_dist_m) * 100.0)), 1)
        else:
            progress_pct = 100.0 if dist_rem_m < 10.0 else 0.0

        # 5. Calculate updated ETA in seconds
        unit_type = (unit.get("unit_type") or "AMBULANCE").upper()
        default_mps = VEHICLE_SPEEDS_MPS.get(unit_type, VEHICLE_SPEEDS_MPS["DEFAULT"])
        speed_mps = (speed_kmh * 1000.0) / 3600.0 if speed_kmh > 3.0 else default_mps

        eta_sec = int(round(dist_rem_m / speed_mps)) if speed_mps > 0 else 0

        now_iso = datetime.utcnow().isoformat() + "Z"

        # 6. Update rescue unit current location in SQLite
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE rescue_units
                SET latitude = ?, longitude = ?, speed_kmh = ?, heading_degrees = ?, last_updated = ?, updated_at = ?
                WHERE id = ?;
                """,
                (lat, lng, speed_kmh, heading_degrees, now_iso, now_iso, unit["id"]),
            )

            # 7. Insert mission update telemetry record
            telemetry_id = f"upd-{uuid.uuid4().hex[:8]}"
            cursor.execute(
                """
                INSERT INTO mission_updates (
                    id, dispatch_id, rescue_unit_id, incident_id, latitude, longitude, status,
                    distance_remaining_meters, eta_seconds, progress_percent, speed_kmh, heading_degrees, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    telemetry_id,
                    disp["id"],
                    unit["id"],
                    incident["id"],
                    lat,
                    lng,
                    disp_status,
                    dist_rem_m,
                    eta_sec,
                    progress_pct,
                    speed_kmh,
                    heading_degrees,
                    now_iso,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        # 8. Broadcast update over WebSocket
        payload = {
            "type": "MISSION_UPDATE",
            "dispatch_id": disp["id"],
            "unit_id": unit["id"],
            "incident_id": incident["id"],
            "status": disp_status,
            "location": {"lat": lat, "lng": lng},
            "speed_kmh": speed_kmh,
            "heading_degrees": heading_degrees,
            "distance_remaining_meters": dist_rem_m,
            "eta_seconds": eta_sec,
            "progress_percent": progress_pct,
            "timestamp": now_iso,
        }
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(ws_manager.broadcast(payload))
        except RuntimeError:
            pass

        return {
            "dispatch_id": disp["id"],
            "status": disp_status,
            "unit": {
                "id": unit["id"],
                "code": unit["unit_code"],
                "type": unit["unit_type"],
                "name": unit["name"],
                "lat": lat,
                "lng": lng,
                "speed_kmh": speed_kmh,
                "heading_degrees": heading_degrees,
            },
            "incident": {
                "id": incident["id"],
                "code": incident["incident_code"],
                "lat": inc_lat,
                "lng": inc_lng,
                "location_name": incident.get("location_name"),
            },
            "distance_remaining_meters": dist_rem_m,
            "eta_seconds": eta_sec,
            "progress_percent": progress_pct,
            "risk_level": disp.get("risk_level", "low"),
            "average_ai_confidence": disp.get("average_confidence", 0.85),
            "route_geometry": route_geom,
        }

    def get_live_mission(self, dispatch_id: str) -> Dict[str, Any]:
        """Retrieve live mission status and telemetry for the specified dispatch ID."""
        disp = dispatch_service.get_dispatch(dispatch_id)
        if not disp:
            raise ValueError(f"Dispatch mission '{dispatch_id}' not found.")

        unit = rescue_unit_service.get_rescue_unit(disp["rescue_unit_id"])
        incident = incident_service.get_incident(disp["incident_id"])

        if not unit or not incident:
            raise ValueError("Associated rescue unit or incident record missing.")

        unit_lat = float(unit["latitude"])
        unit_lng = float(unit["longitude"])
        speed_kmh = float(unit.get("speed_kmh") or 0.0)
        heading_deg = float(unit.get("heading_degrees") or 0.0)

        # Trigger update calculation to get accurate distance remaining & progress
        return self.update_location(
            dispatch_id=disp["id"],
            lat=unit_lat,
            lng=unit_lng,
            speed_kmh=speed_kmh,
            heading_degrees=heading_deg,
        )

    def start_simulation(self, dispatch_id: str) -> Dict[str, Any]:
        """Start async background simulation moving rescue unit along AI route geometry."""
        disp = dispatch_service.get_dispatch(dispatch_id)
        if not disp:
            raise ValueError(f"Dispatch mission '{dispatch_id}' not found.")

        disp_status = disp["status"].upper()
        if disp_status in ("COMPLETED", "CANCELLED"):
            raise ValueError(f"Cannot start simulation for a {disp_status} dispatch mission.")

        # Check if already running
        if dispatch_id in self._active_simulations and not self._active_simulations[dispatch_id].done():
            return {
                "success": True,
                "status": "SIMULATION_RUNNING",
                "dispatch_id": dispatch_id,
                "message": "Simulation is already actively running.",
            }

        # If DISPATCHED, advance status to EN_ROUTE
        if disp_status == "DISPATCHED":
            dispatch_service.update_dispatch_status(dispatch_id, "EN_ROUTE")
            asyncio.create_task(
                ws_manager.broadcast({
                    "type": "MISSION_EN_ROUTE",
                    "dispatch_id": dispatch_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })
            )

        # Launch background task
        task = asyncio.create_task(self._run_simulation_task(dispatch_id))
        self._active_simulations[dispatch_id] = task

        logger.info(f"Started AI route movement simulation for dispatch {dispatch_id}")
        return {
            "success": True,
            "status": "SIMULATION_STARTED",
            "dispatch_id": dispatch_id,
            "message": "Rescue unit AI route simulation started successfully.",
        }

    def stop_simulation(self, dispatch_id: str) -> Dict[str, Any]:
        """Cancel active background movement simulation for dispatch ID."""
        task = self._active_simulations.get(dispatch_id)
        if task and not task.done():
            task.cancel()
            del self._active_simulations[dispatch_id]
            logger.info(f"Stopped simulation for dispatch {dispatch_id}")
            return {
                "success": True,
                "status": "SIMULATION_STOPPED",
                "dispatch_id": dispatch_id,
                "message": "Simulation stopped successfully.",
            }
        return {
            "success": True,
            "status": "SIMULATION_NOT_RUNNING",
            "dispatch_id": dispatch_id,
            "message": "No active simulation task found.",
        }

    async def _run_simulation_task(self, dispatch_id: str):
        """Async background task that steps rescue unit along AI route geometry coordinates."""
        try:
            disp = dispatch_service.get_dispatch(dispatch_id)
            if not disp:
                return

            route_geom = disp.get("route_geometry") or {}
            coords = route_geom.get("coordinates", [])
            if not coords or len(coords) < 2:
                logger.warning(f"No route geometry coordinates available to simulate dispatch {dispatch_id}")
                return

            # Move unit along each polyline coordinate point
            for i in range(len(coords)):
                # Refresh dispatch status to ensure mission wasn't cancelled or completed
                cur_disp = dispatch_service.get_dispatch(dispatch_id)
                if not cur_disp or cur_disp["status"].upper() in ("COMPLETED", "CANCELLED"):
                    logger.info(f"Simulation exiting for dispatch {dispatch_id} due to status change.")
                    break

                c_lng, c_lat = coords[i]
                heading = 0.0
                if i > 0:
                    prev_lng, prev_lat = coords[i - 1]
                    heading = _bearing_degrees(prev_lat, prev_lng, c_lat, c_lng)
                elif len(coords) > 1:
                    next_lng, next_lat = coords[1]
                    heading = _bearing_degrees(c_lat, c_lng, next_lat, next_lng)

                # Update unit location with simulated speed (e.g., 45.0 km/h)
                self.update_location(
                    dispatch_id=dispatch_id,
                    lat=c_lat,
                    lng=c_lng,
                    speed_kmh=45.0,
                    heading_degrees=heading,
                )

                # 1.0s delay between steps for smooth live movement
                await asyncio.sleep(1.0)

            # Check if simulation reached destination
            final_disp = dispatch_service.get_dispatch(dispatch_id)
            if final_disp and final_disp["status"].upper() == "EN_ROUTE":
                dispatch_service.update_dispatch_status(dispatch_id, "ON_SCENE")
                await ws_manager.broadcast({
                    "type": "MISSION_ON_SCENE",
                    "dispatch_id": dispatch_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })

        except asyncio.CancelledError:
            logger.info(f"Simulation task cancelled for dispatch {dispatch_id}")
        except Exception as e:
            logger.error(f"Error in simulation task for dispatch {dispatch_id}: {e}", exc_info=True)
        finally:
            self._active_simulations.pop(dispatch_id, None)


mission_tracking_service = MissionTrackingService()
