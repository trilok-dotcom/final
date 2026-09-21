import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from app.db.database import get_db_connection
from app.services.incident_service import incident_service
from app.services.rescue_unit_service import rescue_unit_service
from app.services.dispatch_service import dispatch_service
from app.services.incident_intelligence_service import incident_intelligence_service
from app.services.route_health_service import route_health_service
from app.services.reroute_service import reroute_service
from app.utils.logging import get_logger

logger = get_logger("app.services.command_center_service")


class CommandCenterService:
    """Multi-Incident Disaster Command Center Aggregation & Orchestration Layer for RESQROUTE.

    Aggregates real-time system state across Stage 5-8C services without duplicating
    intelligence, optimization, dispatch, or routing calculation engines.
    """

    @classmethod
    def get_overview(cls) -> Dict[str, Any]:
        now_iso = datetime.utcnow().isoformat() + "Z"

        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # 1. Fetch raw incidents
            cursor.execute("SELECT * FROM incidents ORDER BY created_at DESC;")
            inc_rows = [dict(r) for r in cursor.fetchall()]

            # 2. Fetch raw rescue units
            cursor.execute("SELECT * FROM rescue_units ORDER BY name ASC;")
            unit_rows = [dict(r) for r in cursor.fetchall()]

            # 3. Fetch active dispatches
            cursor.execute(
                """
                SELECT * FROM dispatches 
                WHERE status IN ('PENDING', 'DISPATCHED', 'EN_ROUTE', 'ON_SCENE') 
                ORDER BY created_at DESC;
                """
            )
            disp_rows = [dict(r) for r in cursor.fetchall()]

            # 4. Fetch acknowledged alert IDs
            cursor.execute("SELECT id, alert_type, incident_id, dispatch_id, unit_id, acknowledged, acknowledged_by, acknowledged_at FROM command_center_alerts WHERE acknowledged = 1;")
            ack_alert_map = {row["id"]: dict(row) for row in cursor.fetchall()}

        finally:
            conn.close()

        # Map dispatches by incident_id
        active_disp_by_inc: Dict[str, Dict[str, Any]] = {}
        for d in disp_rows:
            active_disp_by_inc[d["incident_id"]] = d

        # Map units and incidents by id
        units_by_id: Dict[str, Dict[str, Any]] = {u["id"]: u for u in unit_rows}
        incidents_by_id: Dict[str, Dict[str, Any]] = {i["id"]: i for i in inc_rows}

        # -----------------------------------------------------------------
        # A. Build Active Mission Overview & Route Health Aggregation
        # -----------------------------------------------------------------
        active_missions: List[Dict[str, Any]] = []
        degraded_routes_count = 0
        critical_routes_count = 0
        reroute_recommendations_count = 0
        route_deviations_count = 0

        route_health_by_disp: Dict[str, Dict[str, Any]] = {}

        for disp in disp_rows:
            disp_id = disp["id"]
            inc_id = disp["incident_id"]
            u_id = disp["rescue_unit_id"]

            unit = units_by_id.get(u_id, {})
            inc = incidents_by_id.get(inc_id, {})

            # Evaluate Stage 8C Route Health
            try:
                rh_eval = route_health_service.evaluate_route_health(disp_id)
                route_health_by_disp[disp_id] = rh_eval
            except Exception as e:
                logger.warning(f"Error evaluating route health for dispatch '{disp_id}': {e}")
                rh_eval = {
                    "route_health": "HEALTHY",
                    "health_score": 100.0,
                    "confidence_score": 30.0,
                    "risk_score": 25.0,
                    "overall_score": 100.0,
                    "degradation_detected": False,
                    "unit_deviation_meters": 0.0,
                    "reasons": [],
                    "reason_codes": [],
                    "current_route": {
                        "route_id": disp.get("route_id") or f"route-{disp_id[:8]}",
                        "distance_meters": float(disp.get("distance_meters") or 0.0),
                        "eta_seconds": int(disp.get("estimated_duration_seconds") or 0),
                        "confidence": float(disp.get("average_confidence") or 1.0),
                        "risk_level": str(disp.get("risk_level") or "low").upper(),
                    }
                }

            # Evaluate Stage 8C Re-Route Decision
            try:
                rr_eval = reroute_service.evaluate_reroute(disp_id)
            except Exception as e:
                logger.warning(f"Error evaluating reroute for dispatch '{disp_id}': {e}")
                rr_eval = {
                    "decision": "NO_CHANGE",
                    "recommended_route_id": None,
                    "explanation": "Current route is healthy.",
                    "alternatives": [],
                }

            st = rh_eval.get("route_health", "HEALTHY")
            if st == "DEGRADED":
                degraded_routes_count += 1
            elif st == "CRITICAL":
                critical_routes_count += 1

            dec = rr_eval.get("decision", "NO_CHANGE")
            is_reroute_rec = dec in ["REROUTE_RECOMMENDED", "REROUTE_REQUIRED"]
            if is_reroute_rec:
                reroute_recommendations_count += 1

            dev_m = float(rh_eval.get("unit_deviation_meters") or 0.0)
            is_deviation = dev_m > 150.0
            if is_deviation:
                route_deviations_count += 1

            # Fetch latest telemetry update for this dispatch
            conn = get_db_connection()
            latest_tel = None
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM mission_updates 
                    WHERE dispatch_id = ? 
                    ORDER BY timestamp DESC LIMIT 1;
                    """,
                    (disp_id,),
                )
                r = cursor.fetchone()
                if r:
                    latest_tel = dict(r)
            finally:
                conn.close()

            curr_lat = float(latest_tel["latitude"]) if latest_tel else float(unit.get("latitude") or 12.9716)
            curr_lng = float(latest_tel["longitude"]) if latest_tel else float(unit.get("longitude") or 77.5946)
            curr_speed = float(latest_tel["speed_kmh"]) if latest_tel else float(unit.get("speed_kmh") or 0.0)
            curr_heading = float(latest_tel["heading_degrees"]) if latest_tel else float(unit.get("heading_degrees") or 0.0)
            curr_progress = float(latest_tel["progress_percent"]) if latest_tel else 0.0
            curr_dist_rem = float(latest_tel["distance_remaining_meters"]) if latest_tel else float(disp.get("distance_meters") or 0.0)
            curr_eta = int(latest_tel["eta_seconds"]) if latest_tel else int(disp.get("estimated_duration_seconds") or 0)

            cur_route_info = rh_eval.get("current_route", {})

            active_missions.append({
                "dispatch_id": disp_id,
                "incident_id": inc_id,
                "unit_id": u_id,
                "unit_code": unit.get("unit_code") or "AMB-01",
                "unit_name": unit.get("name") or "Rescue Unit",
                "unit_type": unit.get("unit_type") or "AMBULANCE",
                "unit_status": unit.get("status") or "DISPATCHED",
                "incident_title": inc.get("title") or inc.get("location_name") or "Emergency Incident",
                "incident_type": inc.get("incident_type") or "OTHER",
                "incident_severity": str(inc.get("severity") or "HIGH").upper(),
                "status": disp.get("status", "DISPATCHED").upper(),
                "mission_status": disp.get("status", "DISPATCHED").upper(),
                "health_status": st,
                "route_health": st,
                "current_location": [curr_lat, curr_lng],
                "destination": [float(inc.get("latitude") or 12.9716), float(inc.get("longitude") or 77.5946)],
                "current_latitude": curr_lat,
                "current_longitude": curr_lng,
                "heading": curr_heading,
                "speed": curr_speed,
                "progress_percent": curr_progress,
                "eta_seconds": curr_eta,
                "distance_remaining": curr_dist_rem,
                "distance_remaining_km": round(curr_dist_rem / 1000.0, 2),
                "route_id": cur_route_info.get("route_id") or disp.get("route_id") or f"route-{disp_id[:8]}",
                "route_health_score": rh_eval.get("health_score", 100.0),
                "route_confidence": cur_route_info.get("confidence", 1.0),
                "route_risk": cur_route_info.get("risk_level", "LOW"),
                "route_deviation_meters": dev_m,
                "reroute_decision": dec,
                "reroute_recommended": is_reroute_rec,
                "reroute_required": dec == "REROUTE_REQUIRED",
                "recommended_route_id": rr_eval.get("recommended_route_id"),
                "mission_started_at": disp.get("assigned_at") or disp.get("created_at"),
                "last_updated": latest_tel.get("timestamp") if latest_tel else disp.get("updated_at"),
            })

        # -----------------------------------------------------------------
        # B. Build Incident Command Priority Queue (Stage 8A Consumed)
        # -----------------------------------------------------------------
        active_incidents_list: List[Dict[str, Any]] = []

        for inc in inc_rows:
            inc_status = str(inc.get("status") or "REPORTED").upper()
            if inc_status == "RESOLVED":
                continue

            inc_id = inc["id"]
            # Consume existing Stage 8A Intelligence
            try:
                intel = incident_intelligence_service.analyze_incident(inc_id)
            except Exception as e:
                logger.warning(f"Error analyzing incident '{inc_id}' intelligence: {e}")
                intel = {
                    "intelligence_score": 50.0,
                    "priority_level": "MEDIUM",
                    "urgency_classification": "STANDARD",
                    "resource_recommendation": {"required_units": 1, "suggested_unit_types": ["AMBULANCE"]},
                }

            active_disp = active_disp_by_inc.get(inc_id)
            rh_status = "NO_DISPATCH"
            is_reroute_rec = False
            is_reroute_req = False

            if active_disp:
                rh_info = route_health_by_disp.get(active_disp["id"], {})
                rh_status = rh_info.get("route_health", "HEALTHY")
                try:
                    rr_info = reroute_service.evaluate_reroute(active_disp["id"])
                    dec = rr_info.get("decision")
                    is_reroute_rec = dec in ["REROUTE_RECOMMENDED", "REROUTE_REQUIRED"]
                    is_reroute_req = dec == "REROUTE_REQUIRED"
                except Exception:
                    pass

            # Determine assigned unit details
            assigned_units: List[Dict[str, Any]] = []
            if inc.get("assigned_unit_id"):
                u = units_by_id.get(inc["assigned_unit_id"])
                if u:
                    assigned_units.append({
                        "unit_id": u["id"],
                        "unit_code": u["unit_code"],
                        "unit_type": u["unit_type"],
                        "status": u["status"]
                    })

            active_incidents_list.append({
                "incident_id": inc_id,
                "incident_code": inc.get("incident_code") or "INC-000",
                "incident_type": inc.get("incident_type") or "OTHER",
                "severity": str(inc.get("severity") or "HIGH").upper(),
                "location_name": inc.get("location_name") or "Emergency Location",
                "description": inc.get("description") or "",
                "latitude": float(inc.get("latitude") or 12.9716),
                "longitude": float(inc.get("longitude") or 77.5946),
                "status": inc_status,
                "intelligence": intel,
                "intelligence_score": float(intel.get("intelligence_score") or 50.0),
                "priority_level": str(intel.get("priority_level") or "MEDIUM").upper(),
                "urgency_classification": str(intel.get("urgency_classification") or "STANDARD").upper(),
                "urgency_level": str(intel.get("urgency_classification") or "STANDARD").upper(),
                "resource_recommendation": intel.get("resource_recommendation"),
                "recommended_actions": intel.get("recommended_actions") or [],
                "incident": inc,
                "assigned_units": assigned_units,
                "assigned_unit_count": len(assigned_units),
                "active_dispatch": active_disp,
                "assigned_mission": active_disp,
                "has_active_dispatch": active_disp is not None,
                "has_active_mission": active_disp is not None,
                "route_health": rh_status,
                "reroute_recommended": is_reroute_rec,
                "reroute_required": is_reroute_req,
                "created_at": inc.get("created_at") or now_iso,
            })

        # Sort Priority Queue by Stage 8A Intelligence Score Descending
        active_incidents_list.sort(key=lambda x: x["intelligence_score"], reverse=True)

        # -----------------------------------------------------------------
        # C. Build Resource Availability Overview (Stage 7A + 8B Grouped)
        # -----------------------------------------------------------------
        unit_categories = ["FIRE_TRUCK", "AMBULANCE", "RESCUE_TEAM", "POLICE", "DISASTER_RESPONSE"]
        resource_grouped: Dict[str, Dict[str, int]] = {
            cat: {"available": 0, "reserved": 0, "dispatched": 0, "total": 0} for cat in unit_categories
        }

        unit_list_overview: List[Dict[str, Any]] = []

        total_units_count = len(unit_rows)
        available_units_count = 0
        dispatched_units_count = 0
        reserved_units_count = 0

        for u in unit_rows:
            u_type = str(u.get("unit_type") or "AMBULANCE").upper()
            u_status = str(u.get("status") or "AVAILABLE").upper()

            if u_type not in resource_grouped:
                resource_grouped[u_type] = {"available": 0, "reserved": 0, "dispatched": 0, "total": 0}

            resource_grouped[u_type]["total"] += 1

            if u_status == "AVAILABLE":
                resource_grouped[u_type]["available"] += 1
                available_units_count += 1
            elif u_status == "RESERVED":
                resource_grouped[u_type]["reserved"] += 1
                reserved_units_count += 1
            elif u_status in ["DISPATCHED", "EN_ROUTE", "ON_SCENE"]:
                resource_grouped[u_type]["dispatched"] += 1
                dispatched_units_count += 1
            else:
                # Other status (e.g. MAINTENANCE)
                pass

            caps = []
            if u.get("capabilities"):
                try:
                    caps = json.loads(u["capabilities"]) if isinstance(u["capabilities"], str) else u["capabilities"]
                except Exception:
                    caps = []

            unit_list_overview.append({
                "unit_id": u["id"],
                "unit_code": u["unit_code"],
                "name": u.get("name") or u["unit_code"],
                "unit_type": u_type,
                "status": u_status,
                "latitude": float(u.get("latitude") or 12.9716),
                "longitude": float(u.get("longitude") or 77.5946),
                "current_incident_id": u.get("current_incident_id"),
                "capabilities": caps,
                "speed_kmh": float(u.get("speed_kmh") or 0.0),
                "heading_degrees": float(u.get("heading_degrees") or 0.0),
                "last_updated": u.get("last_updated") or u.get("updated_at"),
            })

        # -----------------------------------------------------------------
        # D. Build Centralized Operations Alert Feed (Deterministic & Deduplicated)
        # -----------------------------------------------------------------
        alerts: List[Dict[str, Any]] = []

        # Alert 1: Unassigned Critical Incidents
        for inc in active_incidents_list:
            if inc["severity"] == "CRITICAL" and not inc["has_active_dispatch"]:
                alert_id = f"alert-unassigned-critical-{inc['incident_id']}"
                ack_info = ack_alert_map.get(alert_id)
                alerts.append({
                    "id": alert_id,
                    "severity": "CRITICAL",
                    "type": "UNASSIGNED_CRITICAL",
                    "alert_type": "UNASSIGNED_CRITICAL",
                    "title": "Unassigned Critical Incident",
                    "message": f"Critical Incident {inc['incident_code']} ({inc['incident_type']}) has no active response dispatch.",
                    "incident_id": inc["incident_id"],
                    "dispatch_id": None,
                    "unit_id": None,
                    "acknowledged": ack_info is not None,
                    "acknowledged_by": ack_info.get("acknowledged_by") if ack_info else None,
                    "acknowledged_at": ack_info.get("acknowledged_at") if ack_info else None,
                    "created_at": inc["created_at"],
                })

        # Alert 2: Mission Telemetry & Route Health Alerts
        for m in active_missions:
            disp_id = m["dispatch_id"]
            inc_id = m["incident_id"]
            u_id = m["unit_id"]
            u_code = m["unit_code"]

            # Route Deviation Alert
            if m["route_deviation_meters"] > 150.0:
                alert_id = f"alert-deviation-{disp_id}"
                ack_info = ack_alert_map.get(alert_id)
                alerts.append({
                    "id": alert_id,
                    "severity": "WARNING",
                    "type": "ROUTE_DEVIATION",
                    "alert_type": "ROUTE_DEVIATION",
                    "title": "Rescue Unit Route Deviation",
                    "message": f"Rescue Unit {u_code} is {m['route_deviation_meters']:.0f}m away from its assigned route.",
                    "incident_id": inc_id,
                    "dispatch_id": disp_id,
                    "unit_id": u_id,
                    "acknowledged": ack_info is not None,
                    "acknowledged_by": ack_info.get("acknowledged_by") if ack_info else None,
                    "acknowledged_at": ack_info.get("acknowledged_at") if ack_info else None,
                    "created_at": m["last_updated"] or now_iso,
                })

            # Route Degradation / Critical Health Alert
            if m["route_health"] == "CRITICAL":
                alert_id = f"alert-route-critical-{disp_id}"
                ack_info = ack_alert_map.get(alert_id)
                alerts.append({
                    "id": alert_id,
                    "severity": "CRITICAL",
                    "type": "ROUTE_CRITICAL",
                    "alert_type": "ROUTE_CRITICAL",
                    "title": "Critical Route Blockage",
                    "message": f"Route for mission {disp_id[:8]} ({u_code}) is CRITICAL/disconnected.",
                    "incident_id": inc_id,
                    "dispatch_id": disp_id,
                    "unit_id": u_id,
                    "acknowledged": ack_info is not None,
                    "acknowledged_by": ack_info.get("acknowledged_by") if ack_info else None,
                    "acknowledged_at": ack_info.get("acknowledged_at") if ack_info else None,
                    "created_at": m["last_updated"] or now_iso,
                })
            elif m["route_health"] == "DEGRADED":
                alert_id = f"alert-route-degraded-{disp_id}"
                ack_info = ack_alert_map.get(alert_id)
                alerts.append({
                    "id": alert_id,
                    "severity": "WARNING",
                    "type": "ROUTE_DEGRADATION",
                    "alert_type": "ROUTE_DEGRADATION",
                    "title": "Route Health Degraded",
                    "message": f"Route for mission {disp_id[:8]} ({u_code}) health score dropped to {m['route_health_score']:.0f}/100.",
                    "incident_id": inc_id,
                    "dispatch_id": disp_id,
                    "unit_id": u_id,
                    "acknowledged": ack_info is not None,
                    "acknowledged_by": ack_info.get("acknowledged_by") if ack_info else None,
                    "acknowledged_at": ack_info.get("acknowledged_at") if ack_info else None,
                    "created_at": m["last_updated"] or now_iso,
                })

            # Re-Route Recommendation Alert
            if m["reroute_required"]:
                alert_id = f"alert-reroute-req-{disp_id}"
                ack_info = ack_alert_map.get(alert_id)
                alerts.append({
                    "id": alert_id,
                    "severity": "CRITICAL",
                    "type": "REROUTE_REQUIRED",
                    "alert_type": "REROUTE_REQUIRED",
                    "title": "AI Re-Route Required",
                    "message": f"Mission {disp_id[:8]} ({u_code}) requires urgent re-routing due to road blockage.",
                    "incident_id": inc_id,
                    "dispatch_id": disp_id,
                    "unit_id": u_id,
                    "acknowledged": ack_info is not None,
                    "acknowledged_by": ack_info.get("acknowledged_by") if ack_info else None,
                    "acknowledged_at": ack_info.get("acknowledged_at") if ack_info else None,
                    "created_at": m["last_updated"] or now_iso,
                })
            elif m["reroute_recommended"]:
                alert_id = f"alert-reroute-rec-{disp_id}"
                ack_info = ack_alert_map.get(alert_id)
                alerts.append({
                    "id": alert_id,
                    "severity": "WARNING",
                    "type": "REROUTE_RECOMMENDED",
                    "alert_type": "REROUTE_RECOMMENDED",
                    "title": "AI Re-Route Recommended",
                    "message": f"Alternative AI route available for mission {disp_id[:8]} ({u_code}) offering higher safety/ETA.",
                    "incident_id": inc_id,
                    "dispatch_id": disp_id,
                    "unit_id": u_id,
                    "acknowledged": ack_info is not None,
                    "acknowledged_by": ack_info.get("acknowledged_by") if ack_info else None,
                    "acknowledged_at": ack_info.get("acknowledged_at") if ack_info else None,
                    "created_at": m["last_updated"] or now_iso,
                })

        # Sort Alerts: Unacknowledged first, then CRITICAL > WARNING > INFO, then created_at DESC
        sev_rank = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        alerts.sort(
            key=lambda a: (
                1 if a["acknowledged"] else 0,
                sev_rank.get(a["severity"], 2),
                a["created_at"],
            )
        )

        # -----------------------------------------------------------------
        # E. Assemble Complete Summary KPI Metrics
        # -----------------------------------------------------------------
        active_incidents_count = len(active_incidents_list)
        critical_incidents_count = sum(1 for i in active_incidents_list if i["severity"] == "CRITICAL")
        high_priority_incidents_count = sum(1 for i in active_incidents_list if i["severity"] in ["CRITICAL", "HIGH"])

        unacknowledged_alerts_count = sum(1 for a in alerts if not a["acknowledged"])
        pending_dispatches_count = max(0, active_incidents_count - len(active_missions))

        summary = {
            "total_incidents": len(inc_rows),
            "active_incidents": active_incidents_count,
            "open_incidents": active_incidents_count,
            "critical_incidents": critical_incidents_count,
            "high_priority_incidents": high_priority_incidents_count,
            "high_incidents": high_priority_incidents_count,
            "total_units": total_units_count,
            "available_units": available_units_count,
            "dispatched_units": dispatched_units_count,
            "busy_units": dispatched_units_count,
            "reserved_units": reserved_units_count,
            "active_missions": len(active_missions),
            "pending_dispatches": pending_dispatches_count,
            "degraded_routes": degraded_routes_count,
            "critical_routes": critical_routes_count,
            "reroute_recommendations": reroute_recommendations_count,
            "route_deviations": route_deviations_count,
            "unacknowledged_alerts": unacknowledged_alerts_count,
        }

        # Extract active routes geometry for map layers
        active_routes_list = [
            m.get("route") for m in active_missions if m.get("route")
        ]

        return {
            "success": True,
            "timestamp": now_iso,
            "last_updated": now_iso,
            "summary": summary,
            "priority_queue": active_incidents_list,
            "incidents": active_incidents_list,
            "active_missions": active_missions,
            "resources": {
                "by_category": resource_grouped,
                "units": unit_list_overview,
            },
            "resource_overview": [
                {
                    "unit_type": cat,
                    "total": counts["total"],
                    "available": counts["available"],
                    "dispatched": counts["dispatched"],
                    "maintenance": counts["reserved"],
                    "units": [u for u in unit_list_overview if u["unit_type"] == cat],
                }
                for cat, counts in resource_grouped.items()
            ],
            "alerts": alerts,
            "map_layers": {
                "incidents": inc_rows,
                "units": unit_rows,
                "active_routes": active_routes_list,
            },
        }

    @classmethod
    def acknowledge_alert(
        cls, alert_id: str, acknowledged_by: str = "DISPATCH_OPERATOR", operator_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Acknowledge a Command Center alert without altering underlying incident/unit/mission state."""
        acknowledged_by = operator_id or acknowledged_by
        now_iso = datetime.utcnow().isoformat() + "Z"

        if not alert_id or not alert_id.startswith("alert-"):
            raise ValueError(f"Command Center alert '{alert_id}' not found.")

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Check if alert entry exists in DB
            cursor.execute("SELECT id FROM command_center_alerts WHERE id = ?;", (alert_id,))
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    """
                    UPDATE command_center_alerts 
                    SET acknowledged = 1, acknowledged_by = ?, acknowledged_at = ? 
                    WHERE id = ?;
                    """,
                    (acknowledged_by, now_iso, alert_id),
                )
            else:
                # Insert deterministic alert acknowledgement row
                parts = alert_id.split("-")
                alert_type = parts[1].upper() if len(parts) > 1 else "GENERAL"
                cursor.execute(
                    """
                    INSERT INTO command_center_alerts (
                        id, alert_type, severity, title, message, incident_id, dispatch_id, unit_id,
                        acknowledged, acknowledged_by, acknowledged_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        alert_id,
                        alert_type,
                        "WARNING",
                        "Acknowledged Operational Alert",
                        f"Alert '{alert_id}' acknowledged by operator.",
                        None,
                        None,
                        None,
                        1,
                        acknowledged_by,
                        now_iso,
                        now_iso,
                    ),
                )
            conn.commit()
            logger.info(f"Command center alert '{alert_id}' acknowledged by {acknowledged_by}.")
        finally:
            conn.close()

        return {
            "success": True,
            "alert_id": alert_id,
            "acknowledged": True,
            "acknowledged_by": acknowledged_by,
            "acknowledged_at": now_iso,
        }


command_center_service = CommandCenterService()
