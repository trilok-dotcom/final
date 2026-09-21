import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.db.database import get_db_connection
from app.models.dispatch import DispatchStatus
from app.services.incident_service import incident_service
from app.services.rescue_unit_service import rescue_unit_service
from app.services.emergency_routing_service import emergency_routing_service, haversine_distance_km
from app.utils.logging import get_logger

logger = get_logger("app.services.dispatch_service")

# Incident Type -> Preferred Rescue Unit Type mapping
INCIDENT_UNIT_PREFERENCE: Dict[str, List[str]] = {
    "MEDICAL": ["AMBULANCE", "DISASTER_RESPONSE"],
    "ACCIDENT": ["AMBULANCE", "RESCUE_TEAM", "POLICE"],
    "FIRE": ["FIRE_TRUCK", "RESCUE_TEAM"],
    "HAZMAT": ["FIRE_TRUCK", "RESCUE_TEAM"],
    "COLLAPSED_BUILDING": ["RESCUE_TEAM", "FIRE_TRUCK", "AMBULANCE"],
    "EARTHQUAKE": ["RESCUE_TEAM", "DISASTER_RESPONSE", "FIRE_TRUCK"],
    "FLOOD": ["RESCUE_TEAM", "DISASTER_RESPONSE", "AMBULANCE"],
    "LANDSLIDE": ["RESCUE_TEAM", "DISASTER_RESPONSE"],
    "STORM": ["DISASTER_RESPONSE", "RESCUE_TEAM"],
    "TSUNAMI": ["DISASTER_RESPONSE", "RESCUE_TEAM"],
    "MISSING_PERSON": ["POLICE", "RESCUE_TEAM"],
    "OTHER": ["POLICE", "AMBULANCE", "RESCUE_TEAM"],
}

# Unit Type -> AI Vehicle Type parameter mapping
UNIT_TO_AI_VEHICLE: Dict[str, str] = {
    "AMBULANCE": "ambulance",
    "FIRE_TRUCK": "fire_truck",
    "RESCUE_TEAM": "rescue",
    "POLICE": "police",
    "DISASTER_RESPONSE": "rescue",
}

# Allowed Dispatch Status Transitions
VALID_TRANSITIONS: Dict[str, List[str]] = {
    "PENDING": ["DISPATCHED", "CANCELLED"],
    "DISPATCHED": ["EN_ROUTE", "CANCELLED"],
    "EN_ROUTE": ["ON_SCENE", "CANCELLED"],
    "ON_SCENE": ["COMPLETED", "CANCELLED"],
    "COMPLETED": [],
    "CANCELLED": [],
}


class DispatchService:
    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        """Convert SQLite Row to dictionary and parse JSON fields."""
        d = dict(row)
        if "route_geometry_json" in d and d["route_geometry_json"]:
            try:
                d["route_geometry"] = json.loads(d["route_geometry_json"])
            except Exception:
                d["route_geometry"] = None
        if "route_steps_json" in d and d["route_steps_json"]:
            try:
                d["route_steps"] = json.loads(d["route_steps_json"])
            except Exception:
                d["route_steps"] = []
        return d

    @classmethod
    def list_dispatches(cls, status: Optional[str] = None, incident_id: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            query = "SELECT * FROM dispatches WHERE 1=1"
            params = []
            if status:
                query += " AND UPPER(status) = ?"
                params.append(status.upper())
            if incident_id:
                query += " AND incident_id = ?"
                params.append(incident_id)
            query += " ORDER BY created_at DESC;"
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [cls._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    @classmethod
    def get_dispatch(cls, dispatch_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM dispatches WHERE id = ?;", (dispatch_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return cls._row_to_dict(row)
        finally:
            conn.close()

    @classmethod
    def get_active_dispatch_for_incident(cls, incident_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM dispatches
                WHERE incident_id = ? AND UPPER(status) IN ('PENDING', 'DISPATCHED', 'EN_ROUTE', 'ON_SCENE')
                LIMIT 1;
                """,
                (incident_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return cls._row_to_dict(row)
        finally:
            conn.close()

    @classmethod
    def dispatch_unit(cls, incident_id: str, rescue_unit_id: str) -> Dict[str, Any]:
        """
        Dispatch a specific designated rescue unit to an incident with calculated AI route.
        """
        incident = incident_service.get_incident(incident_id)
        if not incident:
            raise ValueError(f"Emergency incident '{incident_id}' not found.")

        selected_unit = rescue_unit_service.get_rescue_unit(rescue_unit_id)
        if not selected_unit:
            raise ValueError(f"Rescue unit '{rescue_unit_id}' not found.")

        inc_lat = float(incident["latitude"])
        inc_lng = float(incident["longitude"])
        unit_lat = float(selected_unit["latitude"])
        unit_lng = float(selected_unit["longitude"])
        unit_type = selected_unit.get("unit_type", "AMBULANCE").upper()
        ai_vehicle_type = UNIT_TO_AI_VEHICLE.get(unit_type, "ambulance")

        # Calculate AI Emergency Route
        route_result = emergency_routing_service.calculate_emergency_route(
            start_lat=unit_lat,
            start_lng=unit_lng,
            dest_lat=inc_lat,
            dest_lng=inc_lng,
            vehicle_type=ai_vehicle_type,
            avoid_low_confidence=True,
        )

        selected_distance_m = haversine_distance_km(unit_lat, unit_lng, inc_lat, inc_lng) * 1000.0

        disp_id = f"disp-{uuid.uuid4().hex[:8]}"
        now_iso = datetime.utcnow().isoformat() + "Z"

        geom_json = json.dumps(route_result.get("geometry", {}))
        steps_json = json.dumps(route_result.get("steps", []))

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO dispatches (
                    id, incident_id, rescue_unit_id, status,
                    assigned_at, dispatched_at, en_route_at, arrived_at, completed_at, cancelled_at,
                    route_id, distance_meters, estimated_duration_seconds, average_confidence, risk_level,
                    route_geometry_json, route_steps_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    disp_id,
                    incident["id"],
                    selected_unit["id"],
                    "DISPATCHED",
                    now_iso,
                    now_iso,
                    None,
                    None,
                    None,
                    None,
                    route_result.get("route_id", f"route_{uuid.uuid4().hex[:6]}"),
                    float(route_result.get("total_distance_meters", selected_distance_m)),
                    int(route_result.get("estimated_duration_seconds", 120)),
                    float(route_result.get("average_confidence", 0.85)),
                    str(route_result.get("risk_level", "low")),
                    geom_json,
                    steps_json,
                    now_iso,
                    now_iso,
                ),
            )

            cursor.execute(
                "UPDATE rescue_units SET status = 'DISPATCHED', current_incident_id = ?, updated_at = ? WHERE id = ?;",
                (incident["id"], now_iso, selected_unit["id"]),
            )

            cursor.execute(
                "UPDATE incidents SET status = 'DISPATCHING', assigned_unit_id = ?, updated_at = ? WHERE id = ?;",
                (selected_unit["id"], now_iso, incident["id"]),
            )

            conn.commit()
            logger.info(f"Successfully dispatched unit {selected_unit['unit_code']} to incident {incident['incident_code']} (Dispatch ID: {disp_id})")

            disp_record = cls.get_dispatch(disp_id)
            return {
                "success": True,
                "dispatch_id": disp_id,
                "incident_id": incident["id"],
                "incident_code": incident["incident_code"],
                "rescue_unit_id": selected_unit["id"],
                "rescue_unit_code": selected_unit["unit_code"],
                "rescue_unit_name": selected_unit["name"],
                "vehicle_type": selected_unit["unit_type"],
                "status": "DISPATCHED",
                "route": {
                    "route_id": disp_record["route_id"],
                    "distance_meters": disp_record["distance_meters"],
                    "estimated_duration_seconds": disp_record["estimated_duration_seconds"],
                    "average_confidence": disp_record["average_confidence"],
                    "risk_level": disp_record["risk_level"],
                    "geometry": disp_record.get("route_geometry", {}),
                    "steps": disp_record.get("route_steps", []),
                },
                "assigned_at": now_iso,
                "dispatched_at": now_iso,
            }
        finally:
            conn.close()

    @classmethod
    def dispatch_incident(cls, incident_id: str) -> Dict[str, Any]:
        """
        Execute automatic rescue unit selection, AI route calculation, and dispatch mission assignment.
        """
        # 1. Fetch target incident
        incident = incident_service.get_incident(incident_id)
        if not incident:
            raise ValueError(f"Emergency incident '{incident_id}' not found.")

        # 2. Check if incident already has an active dispatch
        active_disp = cls.get_active_dispatch_for_incident(incident["id"])
        if active_disp:
            raise ValueError(f"Incident '{incident['incident_code']}' already has an active dispatch mission ({active_disp['id']}).")

        # 3. Retrieve available rescue units
        available_units = rescue_unit_service.list_rescue_units(status="AVAILABLE")
        if not available_units:
            raise ValueError("No available rescue unit is currently suitable for this incident.")

        inc_type = (incident.get("incident_type") or "OTHER").upper()
        inc_lat = float(incident["latitude"])
        inc_lng = float(incident["longitude"])

        # 4. Filter preferred units matching incident type
        preferred_types = INCIDENT_UNIT_PREFERENCE.get(inc_type, ["AMBULANCE", "FIRE_TRUCK", "RESCUE_TEAM", "POLICE"])
        candidate_units = [u for u in available_units if u.get("unit_type", "").upper() in preferred_types]

        # Fallback to any available unit if no preferred type match exists
        if not candidate_units:
            candidate_units = available_units

        # 5. Calculate Haversine geographic distance (in meters) to each candidate
        unit_distances: List[Tuple[float, Dict[str, Any]]] = []
        for u in candidate_units:
            u_lat = float(u["latitude"])
            u_lng = float(u["longitude"])
            dist_km = haversine_distance_km(u_lat, u_lng, inc_lat, inc_lng)
            dist_meters = dist_km * 1000.0
            unit_distances.append((dist_meters, u))

        # Sort candidates by distance (nearest unit first)
        unit_distances.sort(key=lambda x: x[0])
        selected_distance_m, selected_unit = unit_distances[0]

        unit_lat = float(selected_unit["latitude"])
        unit_lng = float(selected_unit["longitude"])
        unit_type = selected_unit.get("unit_type", "AMBULANCE").upper()
        ai_vehicle_type = UNIT_TO_AI_VEHICLE.get(unit_type, "ambulance")

        # 6. Calculate AI Emergency Route (Unit location -> Incident location)
        route_result = emergency_routing_service.calculate_emergency_route(
            start_lat=unit_lat,
            start_lng=unit_lng,
            dest_lat=inc_lat,
            dest_lng=inc_lng,
            vehicle_type=ai_vehicle_type,
            avoid_low_confidence=True,
        )

        if not route_result.get("success", False):
            # Log warning if AI routing fell back or returned off-road/no-path
            logger.warning(f"AI route calculation returned status '{route_result.get('status')}' for dispatch.")

        # 7. Create dispatch record in SQLite
        disp_id = f"disp-{uuid.uuid4().hex[:8]}"
        now_iso = datetime.utcnow().isoformat() + "Z"

        geom_json = json.dumps(route_result.get("geometry", {}))
        steps_json = json.dumps(route_result.get("steps", []))

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            initial_route_id = route_result.get("route_id") or f"route-original-{uuid.uuid4().hex[:6]}"
            initial_dist = float(route_result.get("total_distance_meters", selected_distance_m))
            initial_dur = int(route_result.get("estimated_duration_seconds", 120))
            initial_conf = float(route_result.get("average_confidence", 0.85))
            initial_risk = str(route_result.get("risk_level", "low")).upper()

            cursor.execute(
                """
                INSERT INTO dispatches (
                    id, incident_id, rescue_unit_id, status,
                    assigned_at, dispatched_at, en_route_at, arrived_at, completed_at, cancelled_at,
                    route_id, distance_meters, estimated_duration_seconds, average_confidence, risk_level,
                    route_geometry_json, route_steps_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    disp_id,
                    incident["id"],
                    selected_unit["id"],
                    "DISPATCHED",
                    now_iso,
                    now_iso,
                    None,
                    None,
                    None,
                    None,
                    initial_route_id,
                    initial_dist,
                    initial_dur,
                    initial_conf,
                    initial_risk,
                    geom_json,
                    steps_json,
                    now_iso,
                    now_iso,
                ),
            )

            # Insert original active route into routes table for versioning
            cursor.execute(
                """
                INSERT OR REPLACE INTO routes (
                    id, dispatch_id, route_type, status, distance_meters,
                    estimated_duration_seconds, average_confidence, risk_level,
                    health_score, route_geometry_json, route_steps_json, generated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    initial_route_id,
                    disp_id,
                    "ORIGINAL",
                    "ACTIVE",
                    initial_dist,
                    initial_dur,
                    initial_conf,
                    initial_risk,
                    initial_conf * 100.0,
                    geom_json,
                    steps_json,
                    now_iso,
                ),
            )

            # 8. Synchronize Rescue Unit status -> DISPATCHED
            cursor.execute(
                "UPDATE rescue_units SET status = 'DISPATCHED', current_incident_id = ?, updated_at = ? WHERE id = ?;",
                (incident["id"], now_iso, selected_unit["id"]),
            )

            # 9. Synchronize Incident status -> DISPATCHING
            cursor.execute(
                "UPDATE incidents SET status = 'DISPATCHING', assigned_unit_id = ?, updated_at = ? WHERE id = ?;",
                (selected_unit["id"], now_iso, incident["id"]),
            )

            conn.commit()
            logger.info(f"Successfully dispatched unit {selected_unit['unit_code']} to incident {incident['incident_code']} (Dispatch ID: {disp_id})")

            disp_record = cls.get_dispatch(disp_id)
            return {
                "success": True,
                "dispatch_id": disp_id,
                "incident_id": incident["id"],
                "incident_code": incident["incident_code"],
                "rescue_unit_id": selected_unit["id"],
                "rescue_unit_code": selected_unit["unit_code"],
                "rescue_unit_name": selected_unit["name"],
                "vehicle_type": selected_unit["unit_type"],
                "status": "DISPATCHED",
                "route": {
                    "route_id": disp_record["route_id"],
                    "distance_meters": disp_record["distance_meters"],
                    "estimated_duration_seconds": disp_record["estimated_duration_seconds"],
                    "average_confidence": disp_record["average_confidence"],
                    "risk_level": disp_record["risk_level"],
                    "geometry": disp_record.get("route_geometry", {}),
                    "steps": disp_record.get("route_steps", []),
                },
                "assigned_at": now_iso,
                "dispatched_at": now_iso,
            }
        finally:
            conn.close()

    @classmethod
    def update_dispatch_status(cls, dispatch_id: str, new_status: str) -> Dict[str, Any]:
        """
        Update dispatch mission status and validate state machine transitions.
        Synchronizes rescue unit and incident statuses accordingly.
        """
        new_st_upper = new_status.upper().strip()
        disp = cls.get_dispatch(dispatch_id)
        if not disp:
            raise ValueError(f"Dispatch record '{dispatch_id}' not found.")

        old_status = disp["status"].upper()
        if new_st_upper not in VALID_TRANSITIONS.get(old_status, []):
            raise ValueError(f"Invalid status transition from '{old_status}' to '{new_st_upper}'. Allowed transitions: {VALID_TRANSITIONS.get(old_status, [])}")

        now_iso = datetime.utcnow().isoformat() + "Z"
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            timestamp_col = None
            if new_st_upper == "EN_ROUTE":
                timestamp_col = "en_route_at"
            elif new_st_upper == "ON_SCENE":
                timestamp_col = "arrived_at"
            elif new_st_upper == "COMPLETED":
                timestamp_col = "completed_at"
            elif new_st_upper == "CANCELLED":
                timestamp_col = "cancelled_at"

            if timestamp_col:
                cursor.execute(
                    f"UPDATE dispatches SET status = ?, {timestamp_col} = ?, updated_at = ? WHERE id = ?;",
                    (new_st_upper, now_iso, now_iso, disp["id"]),
                )
            else:
                cursor.execute(
                    "UPDATE dispatches SET status = ?, updated_at = ? WHERE id = ?;",
                    (new_st_upper, now_iso, disp["id"]),
                )

            # Synchronize Rescue Unit status
            if new_st_upper == "EN_ROUTE":
                cursor.execute(
                    "UPDATE rescue_units SET status = 'EN_ROUTE', updated_at = ? WHERE id = ?;",
                    (now_iso, disp["rescue_unit_id"]),
                )
                cursor.execute(
                    "UPDATE incidents SET status = 'ACTIVE', updated_at = ? WHERE id = ?;",
                    (now_iso, disp["incident_id"]),
                )
            elif new_st_upper == "ON_SCENE":
                cursor.execute(
                    "UPDATE rescue_units SET status = 'ON_SCENE', updated_at = ? WHERE id = ?;",
                    (now_iso, disp["rescue_unit_id"]),
                )
                cursor.execute(
                    "UPDATE incidents SET status = 'ACTIVE', updated_at = ? WHERE id = ?;",
                    (now_iso, disp["incident_id"]),
                )
            elif new_st_upper == "COMPLETED":
                # Release unit back to AVAILABLE
                cursor.execute(
                    "UPDATE rescue_units SET status = 'AVAILABLE', current_incident_id = NULL, updated_at = ? WHERE id = ?;",
                    (now_iso, disp["rescue_unit_id"]),
                )
                # Resolve incident
                cursor.execute(
                    "UPDATE incidents SET status = 'RESOLVED', updated_at = ?, resolved_at = ? WHERE id = ?;",
                    (now_iso, now_iso, disp["incident_id"]),
                )
            elif new_st_upper == "CANCELLED":
                # Release unit back to AVAILABLE
                cursor.execute(
                    "UPDATE rescue_units SET status = 'AVAILABLE', current_incident_id = NULL, updated_at = ? WHERE id = ?;",
                    (now_iso, disp["rescue_unit_id"]),
                )
                # Reset incident status to REPORTED
                cursor.execute(
                    "UPDATE incidents SET status = 'REPORTED', assigned_unit_id = NULL, updated_at = ? WHERE id = ?;",
                    (now_iso, disp["incident_id"]),
                )

            conn.commit()
            logger.info(f"Updated dispatch {disp['id']} status to {new_st_upper}")
            updated_disp = cls.get_dispatch(disp["id"])
            return updated_disp
        finally:
            conn.close()


dispatch_service = DispatchService()
