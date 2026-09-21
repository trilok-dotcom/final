import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.db.database import get_db_connection
from app.services.incident_service import incident_service
from app.services.rescue_unit_service import rescue_unit_service
from app.services.incident_intelligence_service import incident_intelligence_service
from app.services.emergency_routing_service import emergency_routing_service, haversine_distance_km
from app.services.dispatch_service import dispatch_service, UNIT_TO_AI_VEHICLE
from app.utils.logging import get_logger

logger = get_logger("app.services.resource_optimizer_service")

# Candidate Optimization Factor Weights (Sum = 1.0)
WEIGHT_ETA = 0.30
WEIGHT_ROUTE_SAFETY = 0.20
WEIGHT_AI_CONFIDENCE = 0.15
WEIGHT_CAPABILITY = 0.20
WEIGHT_AVAILABILITY = 0.10
WEIGHT_OPERATIONAL = 0.05


class ResourceOptimizerService:
    @classmethod
    def optimize_incident_resources(cls, incident_id: str) -> Dict[str, Any]:
        """
        Analyze incident requirement, discover available candidate units, calculate in-process AI routes,
        compute 6-factor suitability score, rank units, reserve optimal units, and persist optimization plan.
        """
        # 1. Fetch Incident
        incident = incident_service.get_incident(incident_id)
        if not incident:
            raise ValueError(f"Emergency incident '{incident_id}' not found.")

        inc_code = incident.get("incident_code") or incident.get("code") or "INC-000"
        inc_lat = float(incident["latitude"])
        inc_lng = float(incident["longitude"])

        # 2. Check if incident already has active dispatches
        existing_dispatches = dispatch_service.list_dispatches(incident_id=incident["id"])
        active_dispatches = [d for d in existing_dispatches if d.get("status") in ("DISPATCHED", "EN_ROUTE", "ON_SCENE")]
        if active_dispatches:
            return {
                "success": True,
                "incident_id": incident["id"],
                "incident_code": inc_code,
                "resource_status": "ALREADY_DISPATCHED",
                "required_resources": [],
                "selected_units": [],
                "candidate_units": [],
                "optimization_summary": f"Incident {inc_code} already has {len(active_dispatches)} active rescue dispatches.",
                "analyzed_at": datetime.utcnow().isoformat() + "Z",
            }

        # 3. Get Stage 8A Incident Intelligence Recommendations
        intelligence = incident_intelligence_service.analyze_incident(incident["id"])
        recommended_resources = intelligence.get("recommended_resources", [])

        # 4. Clear old stale RESERVED assignments for this incident and release units
        cls._clear_incident_reservations(incident["id"])

        # 5. Fetch all rescue units and filter AVAILABLE ones
        all_units = rescue_unit_service.list_rescue_units()
        available_units = [u for u in all_units if u.get("status") == "AVAILABLE"]

        all_candidates: List[Dict[str, Any]] = []
        selected_units: List[Dict[str, Any]] = []
        required_summary: List[Dict[str, Any]] = []

        total_required_count = 0
        total_selected_count = 0

        # Used unit tracking to prevent double-booking
        assigned_unit_ids = set()

        # 6. Evaluate candidate units per required resource category
        for req in recommended_resources:
            unit_type = req["unit_type"]
            req_qty = int(req.get("quantity", 1))
            total_required_count += req_qty

            # Match units of required type (or compatible type)
            matching_units = [
                u for u in available_units
                if u["id"] not in assigned_unit_ids and cls._is_unit_compatible(u.get("unit_type"), unit_type)
            ]

            category_candidates: List[Dict[str, Any]] = []

            for unit in matching_units:
                u_lat = float(unit["latitude"])
                u_lng = float(unit["longitude"])
                u_code = unit.get("unit_code") or unit.get("code") or "UNIT-00"
                u_name = unit.get("name") or u_code
                veh_type = UNIT_TO_AI_VEHICLE.get(unit.get("unit_type", "").upper(), "ambulance")

                # Calculate In-Process AI Emergency Route
                route_res = emergency_routing_service.calculate_emergency_route(
                    start_lat=u_lat,
                    start_lng=u_lng,
                    dest_lat=inc_lat,
                    dest_lng=inc_lng,
                    vehicle_type=veh_type,
                    avoid_low_confidence=True,
                )

                dist_m = route_res.get("distance_meters", haversine_distance_km(u_lat, u_lng, inc_lat, inc_lng) * 1000.0)
                dur_s = int(route_res.get("estimated_duration_seconds", dist_m / 15.0))
                conf = float(route_res.get("average_confidence", 0.85))
                risk = route_res.get("risk_level", "low")
                geometry = route_res.get("route_geometry")

                # Compute 6-Factor Normalized Candidate Suitability Score
                eta_score = max(0.0, min(100.0, 100.0 - (dur_s / 12.0)))
                safety_score = 100.0 if risk == "low" else (70.0 if risk == "moderate" else 40.0)
                conf_score = min(100.0, conf * 100.0)
                cap_score = 100.0 if len(unit.get("capabilities", [])) > 0 or unit.get("crew_size", 1) >= 2 else 80.0
                avail_score = 100.0  # Unit is AVAILABLE
                op_score = 90.0

                opt_score = round(
                    eta_score * WEIGHT_ETA
                    + safety_score * WEIGHT_ROUTE_SAFETY
                    + conf_score * WEIGHT_AI_CONFIDENCE
                    + cap_score * WEIGHT_CAPABILITY
                    + avail_score * WEIGHT_AVAILABILITY
                    + op_score * WEIGHT_OPERATIONAL,
                    1
                )

                reason = (
                    f"Selected for {unit_type.replace('_', ' ')} response: Score {opt_score}/100. "
                    f"Distance {dist_m/1000.0:.2f}km, ETA {dur_s//60}m {dur_s%60}s, "
                    f"AI road confidence {conf*100:.1f}%, {risk} risk route."
                )

                cand = {
                    "rescue_unit_id": unit["id"],
                    "unit_code": u_code,
                    "unit_name": u_name,
                    "unit_type": unit.get("unit_type"),
                    "requested_type": unit_type,
                    "status": unit.get("status"),
                    "optimization_score": opt_score,
                    "distance_meters": round(dist_m, 1),
                    "estimated_duration_seconds": dur_s,
                    "average_confidence": conf,
                    "risk_level": risk,
                    "is_selected": False,
                    "selection_reason": reason,
                    "factor_breakdown": {
                        "eta_score": round(eta_score, 1),
                        "route_safety_score": round(safety_score, 1),
                        "ai_confidence_score": round(conf_score, 1),
                        "capability_score": round(cap_score, 1),
                        "availability_score": round(avail_score, 1),
                        "operational_score": round(op_score, 1),
                    },
                    "route_geometry": geometry,
                }
                category_candidates.append(cand)

            # Sort category candidates by score descending
            category_candidates.sort(key=lambda c: c["optimization_score"], reverse=True)

            # Select top N candidates
            selected_in_category = category_candidates[:req_qty]
            for sel in selected_in_category:
                sel["is_selected"] = True
                assigned_unit_ids.add(sel["rescue_unit_id"])
                selected_units.append(sel)

            all_candidates.extend(category_candidates)

            req_count = len(selected_in_category)
            total_selected_count += req_count

            required_summary.append({
                "unit_type": unit_type,
                "required": req_qty,
                "available": len(matching_units),
                "selected": req_count,
            })

        # Determine overall resource status
        if total_selected_count == total_required_count and total_required_count > 0:
            resource_status = "OPTIMAL"
        elif total_selected_count > 0:
            resource_status = "PARTIAL"
        elif total_required_count > 0 and len(available_units) == 0:
            resource_status = "NO_SUITABLE_UNITS"
        else:
            resource_status = "INSUFFICIENT_RESOURCES"

        # Reserve selected units in DB & persist assignments
        now_iso = datetime.utcnow().isoformat() + "Z"
        cls._reserve_and_persist_assignments(incident["id"], selected_units, now_iso)

        opt_summary = (
            f"Resource optimization completed: {resource_status} status. "
            f"Selected {total_selected_count} optimal rescue units out of {total_required_count} required."
        )

        return {
            "success": True,
            "incident_id": incident["id"],
            "incident_code": inc_code,
            "resource_status": resource_status,
            "required_resources": required_summary,
            "selected_units": selected_units,
            "candidate_units": all_candidates,
            "optimization_summary": opt_summary,
            "analyzed_at": now_iso,
        }

    @classmethod
    def dispatch_optimized_plan(cls, incident_id: str) -> Dict[str, Any]:
        """
        Confirm operator decision and dispatch all reserved units for incident.
        Creates individual Stage 7B dispatch records with AI routes and updates unit states.
        """
        # 1. Fetch Incident
        incident = incident_service.get_incident(incident_id)
        if not incident:
            raise ValueError(f"Emergency incident '{incident_id}' not found.")

        inc_code = incident.get("incident_code") or incident.get("code") or "INC-000"

        # 2. Fetch RESERVED assignments for incident
        conn = get_db_connection()
        reserved_assignments = []
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, rescue_unit_id, unit_type, optimization_score, distance_meters,
                       estimated_duration_seconds, average_confidence, risk_level, selection_reason
                FROM resource_assignments
                WHERE incident_id = ? AND status = 'RESERVED';
                """,
                (incident["id"],)
            )
            rows = cursor.fetchall()
            for r in rows:
                reserved_assignments.append({
                    "assignment_id": r[0],
                    "rescue_unit_id": r[1],
                    "unit_type": r[2],
                    "score": r[3],
                    "distance_meters": r[4],
                    "duration_seconds": r[5],
                    "confidence": r[6],
                    "risk_level": r[7],
                    "selection_reason": r[8],
                })
        finally:
            conn.close()

        if not reserved_assignments:
            raise ValueError("No active resource reservation found for incident. Please run resource optimization first.")

        # 3. Verify units are still RESERVED or AVAILABLE for this incident
        for assign in reserved_assignments:
            unit = rescue_unit_service.get_rescue_unit(assign["rescue_unit_id"])
            if not unit:
                raise ValueError(f"Reserved unit '{assign['rescue_unit_id']}' no longer exists. Re-run optimization.")
            if unit.get("status") not in ("RESERVED", "AVAILABLE") or (unit.get("current_incident_id") and unit.get("current_incident_id") != incident["id"]):
                raise ValueError(f"CONFLICT: Unit '{unit.get('unit_code')}' is no longer available. Re-run resource optimization.")

        # 4. Atomically dispatch each selected unit via Stage 7B dispatch engine
        created_dispatch_ids = []
        created_dispatches = []

        for assign in reserved_assignments:
            disp_result = dispatch_service.dispatch_unit(
                incident_id=incident["id"],
                rescue_unit_id=assign["rescue_unit_id"],
            )
            disp_id = disp_result["dispatch_id"]
            created_dispatch_ids.append(disp_id)
            created_dispatches.append(disp_result)

            # Update assignment status in resource_assignments
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE resource_assignments
                    SET dispatch_id = ?, status = 'DISPATCHED', updated_at = ?
                    WHERE id = ?;
                    """,
                    (disp_id, datetime.utcnow().isoformat() + "Z", assign["assignment_id"])
                )
                conn.commit()
            finally:
                conn.close()

        # Update incident status to ACTIVE / DISPATCHING
        incident_service.update_incident(incident["id"], {"status": "ACTIVE"})

        return {
            "success": True,
            "incident_id": incident["id"],
            "incident_code": inc_code,
            "dispatched_units_count": len(created_dispatch_ids),
            "dispatch_ids": created_dispatch_ids,
            "dispatches": created_dispatches,
            "message": f"Successfully dispatched {len(created_dispatch_ids)} rescue units to incident {inc_code}.",
        }

    @staticmethod
    def _is_unit_compatible(unit_type: Optional[str], req_type: str) -> bool:
        if not unit_type:
            return False
        u_type = unit_type.upper()
        r_type = req_type.upper()
        if u_type == r_type:
            return True
        if r_type == "RESCUE_TEAM" and u_type in ("DISASTER_RESPONSE", "FIRE_TRUCK"):
            return True
        if r_type == "DISASTER_RESPONSE" and u_type in ("RESCUE_TEAM", "FIRE_TRUCK"):
            return True
        return False

    @staticmethod
    def _clear_incident_reservations(incident_id: str) -> None:
        """Release any units reserved by a previous optimization run for this incident."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT rescue_unit_id FROM resource_assignments WHERE incident_id = ? AND status = 'RESERVED';",
                (incident_id,)
            )
            rows = cursor.fetchall()
            for r in rows:
                cursor.execute(
                    "UPDATE rescue_units SET status = 'AVAILABLE', current_incident_id = NULL WHERE id = ? AND status = 'RESERVED';",
                    (r[0],)
                )
            cursor.execute("DELETE FROM resource_assignments WHERE incident_id = ? AND status = 'RESERVED';", (incident_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _reserve_and_persist_assignments(incident_id: str, selected_units: List[Dict[str, Any]], timestamp: str) -> None:
        """Update selected rescue units to RESERVED state and record resource_assignments."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            for sel in selected_units:
                assign_id = f"assign-{uuid.uuid4().hex[:8]}"
                u_id = sel["rescue_unit_id"]
                fb = sel.get("factor_breakdown", {})

                # Update rescue unit status to RESERVED
                cursor.execute(
                    """
                    UPDATE rescue_units
                    SET status = 'RESERVED', current_incident_id = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (incident_id, timestamp, u_id)
                )

                # Insert resource_assignment record
                cursor.execute(
                    """
                    INSERT INTO resource_assignments (
                        id, incident_id, dispatch_id, rescue_unit_id, unit_type,
                        optimization_score, distance_meters, estimated_duration_seconds,
                        average_confidence, risk_level, suitability_score, availability_score,
                        eta_score, route_score, capability_score, selection_reason,
                        status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        assign_id,
                        incident_id,
                        None,
                        u_id,
                        sel["unit_type"],
                        sel["optimization_score"],
                        sel["distance_meters"],
                        sel["estimated_duration_seconds"],
                        sel["average_confidence"],
                        sel["risk_level"],
                        sel["optimization_score"],
                        fb.get("availability_score", 100.0),
                        fb.get("eta_score", 100.0),
                        fb.get("route_safety_score", 100.0),
                        fb.get("capability_score", 100.0),
                        sel["selection_reason"],
                        "RESERVED",
                        timestamp,
                        timestamp,
                    )
                )
            conn.commit()
        finally:
            conn.close()


resource_optimizer_service = ResourceOptimizerService()
