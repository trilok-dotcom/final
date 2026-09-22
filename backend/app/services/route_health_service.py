import json
import math
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from app.db.database import get_db_connection
from app.services.dispatch_service import dispatch_service
from app.services.incident_service import incident_service
from app.services.rescue_unit_service import rescue_unit_service
from app.services.emergency_routing_service import haversine_distance_km
from app.utils.logging import get_logger

logger = get_logger("app.services.route_health_service")

# Configurable Route Health & Degradation Thresholds
CONFIDENCE_THRESHOLD = 0.65
RISK_WARNING_LEVELS = ["HIGH", "CRITICAL"]
ETA_INCREASE_THRESHOLD = 0.25  # 25% increase
DEVIATION_THRESHOLD_METERS = 150.0  # 150 meters
HEALTH_IMPROVEMENT_THRESHOLD = 10.0  # 10 points
STALE_ROUTE_THRESHOLD_SECONDS = 300  # 5 minutes


def _min_distance_to_polyline_meters(
    point_lat: float, point_lng: float, coords_lng_lat: List[List[float]]
) -> float:
    """Calculate the minimum distance in meters between point (lat, lng) and a GeoJSON polyline [[lng, lat], ...]."""
    if not coords_lng_lat or len(coords_lng_lat) == 0:
        return 0.0

    min_dist_m = float("inf")
    for i in range(len(coords_lng_lat)):
        c_lng, c_lat = coords_lng_lat[i][0], coords_lng_lat[i][1]
        d_m = haversine_distance_km(point_lat, point_lng, c_lat, c_lng) * 1000.0
        if d_m < min_dist_m:
            min_dist_m = d_m

    return min_dist_m


class RouteHealthService:
    """Deterministic Explainable Route Health Assessment Engine for RESQROUTE.

    Evaluates active route telemetry, AI confidence, route risk level, ETA stability,
    connectivity, and rescue unit route deviation against configurable thresholds.
    """

    @classmethod
    def evaluate_route_health(
        cls, dispatch_id: str, simulated_scenario: Optional[str] = None
    ) -> Dict[str, Any]:
        disp = dispatch_service.get_dispatch(dispatch_id)
        if not disp:
            raise ValueError(f"Dispatch mission '{dispatch_id}' not found.")

        unit = rescue_unit_service.get_rescue_unit(disp["rescue_unit_id"])
        incident = incident_service.get_incident(disp["incident_id"])

        if not unit or not incident:
            raise ValueError("Associated rescue unit or incident record missing.")

        # Fetch latest mission telemetry update if available
        conn = get_db_connection()
        latest_telemetry = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM mission_updates 
                WHERE dispatch_id = ? 
                ORDER BY timestamp DESC LIMIT 1;
                """,
                (dispatch_id,),
            )
            row = cursor.fetchone()
            if row:
                latest_telemetry = dict(row)
        finally:
            conn.close()

        # Baseline parameters from dispatch
        route_id = disp.get("route_id") or f"route-{dispatch_id[:8]}"
        dist_m = float(disp.get("distance_meters") or 0.0)
        orig_eta_sec = int(disp.get("estimated_duration_seconds") or 0)
        avg_conf = float(disp.get("average_confidence") or 1.0)
        risk_lvl = (disp.get("risk_level") or "low").upper()
        route_geom = disp.get("route_geometry") or {}
        coords = route_geom.get("coordinates", [])

        # Extract current unit coordinates
        if latest_telemetry:
            unit_lat = float(latest_telemetry["latitude"])
            unit_lng = float(latest_telemetry["longitude"])
        elif coords and len(coords) >= 1:
            unit_lat = float(coords[0][1])
            unit_lng = float(coords[0][0])
        else:
            unit_lat = float(unit.get("latitude") or 12.9716)
            unit_lng = float(unit.get("longitude") or 77.5946)

        # Current telemetry ETA (or remaining duration)
        if latest_telemetry and latest_telemetry.get("eta_seconds"):
            curr_eta_sec = int(latest_telemetry["eta_seconds"])
        else:
            curr_eta_sec = orig_eta_sec

        # Compute Unit Deviation from route polyline
        deviation_m = 0.0
        if coords and len(coords) >= 2:
            deviation_m = round(_min_distance_to_polyline_meters(unit_lat, unit_lng, coords), 1)

        is_connected = True

        # Check active post-disaster road condition assessment (Stage 7E)
        post_disaster_blocked = False
        try:
            from app.services.road_condition_service import road_condition_service
            active_assessment = road_condition_service.get_active_assessment()
            if active_assessment and active_assessment.get("blocked_count", 0) > 0:
                for seg in active_assessment.get("segments", []):
                    if seg.get("condition") == "BLOCKED" and not seg.get("traversable", True):
                        post_disaster_blocked = True
                        break
        except Exception as err:
            logger.warning(f"Could not check active assessment in route health: {err}")

        if post_disaster_blocked:
            is_connected = False
            avg_conf = min(avg_conf, 0.35)

        # Apply Simulation Overrides if requested
        is_simulated = False
        if simulated_scenario:
            is_simulated = True
            scenario_upper = simulated_scenario.upper()
            if scenario_upper == "LOW_CONFIDENCE":
                avg_conf = 0.48
            elif scenario_upper == "HIGH_RISK":
                risk_lvl = "HIGH"
            elif scenario_upper == "ETA_INCREASE":
                curr_eta_sec = int(orig_eta_sec * 1.40)  # +40% delay
            elif scenario_upper == "ROUTE_DISCONNECTED":
                is_connected = False
                avg_conf = 0.30
                risk_lvl = "CRITICAL"
            elif scenario_upper == "NO_ALTERNATIVE":
                is_connected = False
                avg_conf = 0.20
                risk_lvl = "CRITICAL"
            elif scenario_upper == "MINOR_DEGRADATION":
                avg_conf = 0.63
            elif scenario_upper == "UNIT_DEVIATION":
                deviation_m = 185.5  # 185.5m away


        # Calculate Deterministic Explainable Scores (100% total)
        # 1. AI Confidence Component (30%)
        conf_pts = max(0.0, min(30.0, avg_conf * 30.0))

        # 2. Risk Level Component (25%)
        if risk_lvl == "LOW":
            risk_pts = 25.0
        elif risk_lvl == "MODERATE":
            risk_pts = 15.0
        elif risk_lvl == "HIGH":
            risk_pts = 5.0
        else:  # CRITICAL
            risk_pts = 0.0

        # 3. ETA Stability Component (20%)
        if orig_eta_sec > 0 and curr_eta_sec > orig_eta_sec:
            eta_increase_ratio = (curr_eta_sec - orig_eta_sec) / float(orig_eta_sec)
            eta_pts = max(0.0, 20.0 - (eta_increase_ratio * 40.0))
        else:
            eta_increase_ratio = 0.0
            eta_pts = 20.0

        # 4. Route Connectivity Component (15%)
        conn_pts = 15.0 if is_connected else 0.0

        # 5. Unit Route Deviation Component (10%)
        if deviation_m <= 50.0:
            dev_pts = 10.0
        elif deviation_m <= DEVIATION_THRESHOLD_METERS:
            dev_pts = max(5.0, 10.0 - ((deviation_m - 50.0) / 100.0) * 5.0)
        else:
            dev_pts = max(0.0, 5.0 - ((deviation_m - DEVIATION_THRESHOLD_METERS) / 150.0) * 5.0)

        overall_score = round(conf_pts + risk_pts + eta_pts + conn_pts + dev_pts, 1)

        # Degradation Detection & Reason formulation
        reasons: List[str] = []
        reason_codes: List[str] = []
        degradation_detected = False

        if not is_connected:
            degradation_detected = True
            reasons.append("Route network segment is disconnected or impassable")
            reason_codes.append("ROUTE_DISCONNECTED")
            if post_disaster_blocked:
                reasons.append("Post-disaster road assessment detected blocked route segment")
                reason_codes.append("POST_DISASTER_ROAD_BLOCKED")


        if avg_conf < CONFIDENCE_THRESHOLD:
            degradation_detected = True
            reasons.append(f"AI road confidence ({avg_conf:.2f}) below threshold ({CONFIDENCE_THRESHOLD})")
            reason_codes.append("LOW_ROUTE_CONFIDENCE")

        if risk_lvl in RISK_WARNING_LEVELS:
            degradation_detected = True
            reasons.append(f"Current route risk level increased to {risk_lvl}")
            reason_codes.append("HIGH_ROUTE_RISK")

        if eta_increase_ratio > ETA_INCREASE_THRESHOLD:
            degradation_detected = True
            pct_inc = int(eta_increase_ratio * 100)
            reasons.append(f"ETA increased significantly (+{pct_inc}% delay)")
            reason_codes.append("ETA_INCREASE")

        if deviation_m > DEVIATION_THRESHOLD_METERS:
            degradation_detected = True
            unit_code = unit.get("unit_code") or "Rescue Unit"
            reasons.append(f"Unit {unit_code} is {deviation_m:.0f}m away from its assigned route")
            reason_codes.append("ROUTE_DEVIATION")

        # Route Health Category
        if not is_connected or overall_score < 50.0:
            health_status = "CRITICAL"
        elif degradation_detected or overall_score < 75.0:
            health_status = "DEGRADED"
        else:
            health_status = "HEALTHY"

        return {
            "success": True,
            "dispatch_id": dispatch_id,
            "route_health": health_status,
            "health_score": overall_score,
            "overall_score": overall_score,
            "confidence_score": round(conf_pts, 1),
            "risk_score": round(risk_pts, 1),
            "eta_score": round(eta_pts, 1),
            "connectivity_score": round(conn_pts, 1),
            "deviation_score": round(dev_pts, 1),
            "degradation_detected": degradation_detected,
            "current_route": {
                "route_id": route_id,
                "distance_meters": dist_m,
                "eta_seconds": curr_eta_sec,
                "confidence": avg_conf,
                "risk_level": risk_lvl,
                "health_score": overall_score,
            },
            "unit_deviation_meters": deviation_m,
            "reasons": reasons,
            "reason_codes": reason_codes,
            "is_simulated": is_simulated,
            "evaluated_at": datetime.utcnow().isoformat() + "Z",
        }


route_health_service = RouteHealthService()
