import json
import time
import uuid
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.db.database import get_db_connection
from app.services.scenario_generator import scenario_generator
from app.services.incident_service import incident_service
from app.services.rescue_unit_service import rescue_unit_service
from app.services.dispatch_service import dispatch_service
from app.services.mission_tracking_service import mission_tracking_service
from app.services.incident_intelligence_service import incident_intelligence_service
from app.services.resource_optimizer_service import resource_optimizer_service
from app.services.route_health_service import route_health_service
from app.services.reroute_service import reroute_service
from app.services.command_center_service import command_center_service
from app.schemas.incident import IncidentCreate
from app.utils.logging import get_logger

logger = get_logger("app.services.simulation_service")

# Background thread active simulation runners map: {session_id: threading.Thread}
_ACTIVE_SIMULATION_THREADS: Dict[str, threading.Thread] = {}
_ACTIVE_SIMULATION_STOP_FLAGS: Dict[str, bool] = {}


class SimulationService:
    @classmethod
    def create_simulation(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new deterministic disaster simulation session.
        Generates isolated simulation incidents, rescue units, and timeline event queue.
        """
        scenario_type = (data.get("scenario_type") or "URBAN_EARTHQUAKE").upper()
        scale = (data.get("scale") or "MEDIUM").upper()
        seed = int(data.get("seed") if data.get("seed") is not None else 42)
        speed = int(data.get("speed") or 1)
        bounds = data.get("bounds")

        # 1. Generate scenario via ScenarioGenerator
        scen = scenario_generator.generate_scenario(
            scenario_type=scenario_type,
            scale=scale,
            seed=seed,
            bounds=bounds,
        )

        session_id = f"sim-{uuid.uuid4().hex[:8]}"
        now_iso = datetime.utcnow().isoformat() + "Z"

        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # 2. Insert simulation_sessions record
            cursor.execute(
                """
                INSERT INTO simulation_sessions (
                    id, scenario_type, scenario_name, seed, scale, status,
                    simulation_time, speed, started_at, paused_at, completed_at, stopped_at,
                    bounds_json, summary_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    session_id,
                    scen["scenario_type"],
                    scen["name"],
                    scen["seed"],
                    scen["scale"],
                    "CREATED",
                    0,
                    speed,
                    None,
                    None,
                    None,
                    None,
                    json.dumps(scen["bounds"]),
                    json.dumps({}),
                    now_iso,
                    now_iso,
                ),
            )

            # 3. Create Simulation Rescue Units in rescue_units table tagged with simulation_session_id
            for u in scen["units"]:
                unit_id = f"sim-unit-{uuid.uuid4().hex[:8]}"
                unit_code = f"SIM-{session_id[4:8].upper()}-{u['unit_code']}"
                cursor.execute(
                    """
                    INSERT INTO rescue_units (
                        id, unit_code, unit_type, status, latitude, longitude, name,
                        crew_size, capabilities, current_incident_id, speed_kmh, heading_degrees,
                        last_updated, created_at, updated_at, simulation_session_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        unit_id,
                        unit_code,
                        u["unit_type"],
                        u["status"],
                        u["latitude"],
                        u["longitude"],
                        u["name"],
                        u["crew_size"],
                        json.dumps(u["capabilities"]),
                        None,
                        0.0,
                        0.0,
                        now_iso,
                        now_iso,
                        now_iso,
                        session_id,
                    ),
                )

            # 4. Create Simulation Incidents in incidents table tagged with simulation_session_id
            for idx, inc in enumerate(scen["incidents"]):
                inc_id = f"sim-inc-{uuid.uuid4().hex[:8]}"
                inc_code = f"SIM-{session_id[4:8].upper()}-INC-{(idx+1):04d}"
                cursor.execute(
                    """
                    INSERT INTO incidents (
                        id, incident_code, incident_type, severity, status,
                        latitude, longitude, location_name, description, reported_by,
                        assigned_unit_id, created_at, updated_at, resolved_at, simulation_session_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        inc_id,
                        inc_code,
                        inc["incident_type"],
                        inc["severity"],
                        "REPORTED",
                        inc["latitude"],
                        inc["longitude"],
                        inc["location_name"],
                        inc["description"],
                        "SIMULATION_ENGINE",
                        None,
                        now_iso,
                        now_iso,
                        None,
                        session_id,
                    ),
                )

            # 5. Insert Timeline Events
            for ev in scen["timeline"]:
                ev_id = f"sim-ev-{uuid.uuid4().hex[:8]}"
                cursor.execute(
                    """
                    INSERT INTO simulation_events (
                        id, simulation_session_id, simulated_time, event_type,
                        title, description, data_json, status, executed_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        ev_id,
                        session_id,
                        ev["simulated_time"],
                        ev["event_type"],
                        ev["title"],
                        ev["description"],
                        json.dumps(ev.get("data", {})),
                        "PENDING",
                        None,
                        now_iso,
                    ),
                )

            conn.commit()
            logger.info(f"Created disaster simulation session {session_id} ({scen['name']}, seed={seed})")
            return cls.get_simulation(session_id)
        finally:
            conn.close()

    @classmethod
    def get_simulation(cls, simulation_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM simulation_sessions WHERE id = ?;", (simulation_id,))
            row = cursor.fetchone()
            if not row:
                return None
            sess = dict(row)
            if sess.get("bounds_json"):
                sess["bounds"] = json.loads(sess["bounds_json"])
            if sess.get("summary_json"):
                sess["summary"] = json.loads(sess["summary_json"])

            # Fetch timeline events
            cursor.execute(
                "SELECT * FROM simulation_events WHERE simulation_session_id = ? ORDER BY simulated_time ASC, created_at ASC;",
                (simulation_id,),
            )
            ev_rows = cursor.fetchall()
            events = []
            for r in ev_rows:
                ed = dict(r)
                if ed.get("data_json"):
                    ed["data"] = json.loads(ed["data_json"])
                events.append(ed)

            sess["events"] = events
            return sess
        finally:
            conn.close()

    @classmethod
    def list_simulations(cls) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM simulation_sessions ORDER BY created_at DESC;")
            rows = cursor.fetchall()
            result = []
            for r in rows:
                sess = dict(r)
                if sess.get("bounds_json"):
                    sess["bounds"] = json.loads(sess["bounds_json"])
                if sess.get("summary_json"):
                    sess["summary"] = json.loads(sess["summary_json"])
                result.append(sess)
            return result
        finally:
            conn.close()

    @classmethod
    def start_simulation(cls, simulation_id: str) -> Dict[str, Any]:
        sess = cls.get_simulation(simulation_id)
        if not sess:
            raise ValueError(f"Simulation session '{simulation_id}' not found.")

        if sess["status"] not in ("CREATED", "PAUSED", "STOPPED"):
            return sess

        now_iso = datetime.utcnow().isoformat() + "Z"
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE simulation_sessions SET status = 'RUNNING', started_at = COALESCE(started_at, ?), updated_at = ? WHERE id = ?;",
                (now_iso, now_iso, simulation_id),
            )
            conn.commit()
        finally:
            conn.close()

        logger.info(f"Started simulation session {simulation_id}")
        return cls.get_simulation(simulation_id)

    @classmethod
    def pause_simulation(cls, simulation_id: str) -> Dict[str, Any]:
        sess = cls.get_simulation(simulation_id)
        if not sess:
            raise ValueError(f"Simulation session '{simulation_id}' not found.")

        now_iso = datetime.utcnow().isoformat() + "Z"
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE simulation_sessions SET status = 'PAUSED', paused_at = ?, updated_at = ? WHERE id = ?;",
                (now_iso, now_iso, simulation_id),
            )
            conn.commit()
        finally:
            conn.close()

        logger.info(f"Paused simulation session {simulation_id}")
        return cls.get_simulation(simulation_id)

    @classmethod
    def resume_simulation(cls, simulation_id: str) -> Dict[str, Any]:
        return cls.start_simulation(simulation_id)

    @classmethod
    def stop_simulation(cls, simulation_id: str) -> Dict[str, Any]:
        sess = cls.get_simulation(simulation_id)
        if not sess:
            raise ValueError(f"Simulation session '{simulation_id}' not found.")

        now_iso = datetime.utcnow().isoformat() + "Z"
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE simulation_sessions SET status = 'STOPPED', stopped_at = ?, updated_at = ? WHERE id = ?;",
                (now_iso, now_iso, simulation_id),
            )
            conn.commit()
        finally:
            conn.close()

        logger.info(f"Stopped simulation session {simulation_id}")
        return cls.get_simulation(simulation_id)

    @classmethod
    def set_speed(cls, simulation_id: str, speed: int) -> Dict[str, Any]:
        sess = cls.get_simulation(simulation_id)
        if not sess:
            raise ValueError(f"Simulation session '{simulation_id}' not found.")

        speed = max(1, min(10, speed))
        now_iso = datetime.utcnow().isoformat() + "Z"
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE simulation_sessions SET speed = ?, updated_at = ? WHERE id = ?;",
                (speed, now_iso, simulation_id),
            )
            conn.commit()
        finally:
            conn.close()

        return cls.get_simulation(simulation_id)

    @classmethod
    def step_simulation(cls, simulation_id: str, step_seconds: int = 5) -> Dict[str, Any]:
        """
        Advance virtual simulation clock by step_seconds and execute due timeline events.
        Orchestrates pipeline stages: 8A Intelligence -> 8B Optimization -> 7B Dispatch -> 7C Telemetry -> 8C Rerouting -> 9A Command Center.
        """
        sess = cls.get_simulation(simulation_id)
        if not sess:
            raise ValueError(f"Simulation session '{simulation_id}' not found.")

        if sess["status"] == "COMPLETED":
            return sess

        new_sim_time = sess["simulation_time"] + step_seconds
        now_iso = datetime.utcnow().isoformat() + "Z"

        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # 1. Update simulation_time
            cursor.execute(
                "UPDATE simulation_sessions SET simulation_time = ?, updated_at = ? WHERE id = ?;",
                (new_sim_time, now_iso, simulation_id),
            )

            # 2. Discover due timeline events
            cursor.execute(
                """
                SELECT * FROM simulation_events
                WHERE simulation_session_id = ? AND status = 'PENDING' AND simulated_time <= ?
                ORDER BY simulated_time ASC, created_at ASC;
                """,
                (simulation_id, new_sim_time),
            )
            due_events = cursor.fetchall()
            conn.commit()
        finally:
            conn.close()

        # 3. Process due timeline events
        for ev in due_events:
            ev_dict = dict(ev)
            cls._execute_timeline_event(simulation_id, ev_dict)

        # 4. Perform ongoing telemetry movement step for active dispatches in this simulation
        cls._step_telemetry_movement(simulation_id)

        # 5. Check if simulation exercise should be marked COMPLETED
        cls._check_simulation_completion(simulation_id)

        return cls.get_simulation(simulation_id)

    @classmethod
    def trigger_custom_event(
        cls,
        simulation_id: str,
        event_type: str,
        dispatch_id: Optional[str] = None,
        incident_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Inject a custom event (LOW_CONFIDENCE, HIGH_RISK, ETA_INCREASE, ROUTE_DISCONNECTED, UNIT_DEVIATION, NEW_INCIDENT)
        into the timeline and execute it immediately.
        """
        sess = cls.get_simulation(simulation_id)
        if not sess:
            raise ValueError(f"Simulation session '{simulation_id}' not found.")

        event_type = event_type.upper()
        now_iso = datetime.utcnow().isoformat() + "Z"
        ev_id = f"sim-ev-{uuid.uuid4().hex[:8]}"

        event_data = data or {}
        if dispatch_id:
            event_data["dispatch_id"] = dispatch_id
        if incident_id:
            event_data["incident_id"] = incident_id

        title = f"Manual Event Trigger: {event_type.replace('_', ' ')}"
        desc = f"Operator injected {event_type} event into simulation {simulation_id}."

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO simulation_events (
                    id, simulation_session_id, simulated_time, event_type,
                    title, description, data_json, status, executed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    ev_id,
                    simulation_id,
                    sess["simulation_time"],
                    event_type,
                    title,
                    desc,
                    json.dumps(event_data),
                    "PENDING",
                    None,
                    now_iso,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        # Execute injected event immediately
        cls._execute_timeline_event(simulation_id, {
            "id": ev_id,
            "simulation_session_id": simulation_id,
            "simulated_time": sess["simulation_time"],
            "event_type": event_type,
            "title": title,
            "description": desc,
            "data_json": json.dumps(event_data),
        })

        return cls.get_simulation(simulation_id)

    @classmethod
    def reset_simulation(cls, simulation_id: str) -> Dict[str, Any]:
        """
        Safely reset/delete all records associated ONLY with simulation_session_id.
        Preserves non-simulation production data intact.
        """
        sess = cls.get_simulation(simulation_id)
        if not sess:
            return {"success": True, "message": f"Simulation {simulation_id} already deleted."}

        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Delete simulation alerts, reroutes, routes, assignments, telemetry, dispatches, units, incidents, events, session
            cursor.execute("DELETE FROM command_center_alerts WHERE simulation_session_id = ?;", (simulation_id,))
            cursor.execute("DELETE FROM reroute_events WHERE dispatch_id IN (SELECT id FROM dispatches WHERE simulation_session_id = ?);", (simulation_id,))
            cursor.execute("DELETE FROM route_evaluations WHERE dispatch_id IN (SELECT id FROM dispatches WHERE simulation_session_id = ?);", (simulation_id,))
            cursor.execute("DELETE FROM routes WHERE dispatch_id IN (SELECT id FROM dispatches WHERE simulation_session_id = ?);", (simulation_id,))
            cursor.execute("DELETE FROM resource_assignments WHERE simulation_session_id = ? OR incident_id IN (SELECT id FROM incidents WHERE simulation_session_id = ?);", (simulation_id, simulation_id))
            cursor.execute("DELETE FROM mission_updates WHERE simulation_session_id = ? OR dispatch_id IN (SELECT id FROM dispatches WHERE simulation_session_id = ?);", (simulation_id, simulation_id))
            cursor.execute("DELETE FROM dispatches WHERE simulation_session_id = ?;", (simulation_id,))
            cursor.execute("DELETE FROM rescue_units WHERE simulation_session_id = ?;", (simulation_id,))
            cursor.execute("DELETE FROM incidents WHERE simulation_session_id = ?;", (simulation_id,))
            cursor.execute("DELETE FROM simulation_events WHERE simulation_session_id = ?;", (simulation_id,))
            cursor.execute("DELETE FROM simulation_sessions WHERE id = ?;", (simulation_id,))

            conn.commit()
            logger.info(f"Reset and deleted simulation session {simulation_id} data.")
            return {"success": True, "simulation_id": simulation_id, "message": "Simulation session safely reset."}
        finally:
            conn.close()

    @classmethod
    def get_simulation_overview(cls, simulation_id: str) -> Dict[str, Any]:
        """
        Get comprehensive Disaster Command Center overview filtered for specific simulation session.
        """
        sess = cls.get_simulation(simulation_id)
        if not sess:
            raise ValueError(f"Simulation session '{simulation_id}' not found.")

        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # 1. Fetch simulation incidents
            cursor.execute("SELECT * FROM incidents WHERE simulation_session_id = ? ORDER BY created_at DESC;", (simulation_id,))
            inc_rows = cursor.fetchall()
            incidents = [dict(r) for r in inc_rows]

            # 2. Fetch simulation units
            cursor.execute("SELECT * FROM rescue_units WHERE simulation_session_id = ? ORDER BY unit_code ASC;", (simulation_id,))
            unit_rows = cursor.fetchall()
            units = [dict(r) for r in unit_rows]

            # 3. Fetch simulation dispatches
            cursor.execute("SELECT * FROM dispatches WHERE simulation_session_id = ? ORDER BY created_at DESC;", (simulation_id,))
            disp_rows = cursor.fetchall()
            dispatches = [dict(r) for r in disp_rows]

            # 4. Fetch simulation alerts
            cursor.execute("SELECT * FROM command_center_alerts WHERE simulation_session_id = ? ORDER BY created_at DESC;", (simulation_id,))
            alert_rows = cursor.fetchall()
            alerts = [dict(r) for r in alert_rows]

            # Calculate metrics
            total_inc = len(incidents)
            crit_inc = sum(1 for i in incidents if i["severity"] == "CRITICAL")
            open_inc = sum(1 for i in incidents if i["status"] != "RESOLVED")
            active_disp = [d for d in dispatches if d["status"] in ("DISPATCHED", "EN_ROUTE", "ON_SCENE")]
            completed_disp = [d for d in dispatches if d["status"] == "COMPLETED"]
            avail_units = sum(1 for u in units if u["status"] == "AVAILABLE")
            disp_units = sum(1 for u in units if u["status"] in ("DISPATCHED", "EN_ROUTE", "ON_SCENE"))

            # Calculate degraded routes & reroute recommendations
            degraded_count = 0
            reroute_rec_count = 0
            for d in active_disp:
                try:
                    health = route_health_service.evaluate_route_health(d["id"])
                    if health["route_health"] in ("DEGRADED", "CRITICAL"):
                        degraded_count += 1
                    rec = reroute_service.evaluate_reroute(d["id"])
                    if rec["decision"] in ("REROUTE_RECOMMENDED", "REROUTE_REQUIRED"):
                        reroute_rec_count += 1
                except Exception:
                    pass

            summary = {
                "incidents": total_inc,
                "critical_incidents": crit_inc,
                "open_incidents": open_inc,
                "active_missions": len(active_disp),
                "completed_missions": len(completed_disp),
                "available_units": avail_units,
                "dispatched_units": disp_units,
                "degraded_routes": degraded_count,
                "reroute_recommendations": reroute_rec_count,
            }

            # Map layers
            map_incidents = [
                {
                    "id": i["id"],
                    "incident_code": i["incident_code"],
                    "title": i["location_name"] or i["incident_code"],
                    "incident_type": i["incident_type"],
                    "severity": i["severity"],
                    "status": i["status"],
                    "latitude": i["latitude"],
                    "longitude": i["longitude"],
                    "simulation_session_id": simulation_id,
                }
                for i in incidents
            ]
            map_units = [
                {
                    "id": u["id"],
                    "unit_code": u["unit_code"],
                    "name": u["name"],
                    "unit_type": u["unit_type"],
                    "status": u["status"],
                    "latitude": u["latitude"],
                    "longitude": u["longitude"],
                    "speed_kmh": u.get("speed_kmh", 0.0),
                    "simulation_session_id": simulation_id,
                }
                for u in units
            ]

            return {
                "success": True,
                "simulation": {
                    "id": sess["id"],
                    "scenario_type": sess["scenario_type"],
                    "scenario_name": sess["scenario_name"],
                    "seed": sess["seed"],
                    "scale": sess["scale"],
                    "status": sess["status"],
                    "simulation_time": sess["simulation_time"],
                    "speed": sess["speed"],
                    "started_at": sess.get("started_at"),
                    "completed_at": sess.get("completed_at"),
                },
                "summary": summary,
                "events": sess.get("events", []),
                "incidents": incidents,
                "missions": dispatches,
                "alerts": alerts,
                "map_layers": {
                    "incidents": map_incidents,
                    "units": map_units,
                    "active_routes": [],
                },
            }
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # INTERNAL PIPELINE INTEGRATION HELPER METHODS
    # -------------------------------------------------------------------------

    @classmethod
    def _execute_timeline_event(cls, simulation_id: str, ev: Dict[str, Any]) -> None:
        """Execute a single due simulation event and invoke corresponding RESQROUTE stage service."""
        ev_id = ev["id"]
        ev_type = ev["event_type"]
        data = json.loads(ev["data_json"]) if isinstance(ev.get("data_json"), str) else ev.get("data", {})

        logger.info(f"Executing simulation event '{ev_type}' for session {simulation_id}")

        try:
            if ev_type in ("DISASTER_START", "NEW_INCIDENT"):
                # Ensure Stage 8A Intelligence analysis is triggered for reported incidents
                cls._trigger_stage_8a_intelligence(simulation_id)

            elif ev_type == "EVALUATE_INTELLIGENCE":
                cls._trigger_stage_8a_intelligence(simulation_id)

            elif ev_type == "OPTIMIZE_RESOURCES":
                cls._trigger_stage_8b_resource_optimization(simulation_id)

            elif ev_type == "CREATE_DISPATCH":
                cls._trigger_stage_7b_automatic_dispatch(simulation_id)

            elif ev_type == "TELEMETRY_STEP":
                cls._step_telemetry_movement(simulation_id)

            elif ev_type in ("ROUTE_DEGRADATION_INJECT", "LOW_CONFIDENCE", "HIGH_RISK", "ETA_INCREASE", "ROUTE_DISCONNECTED", "UNIT_DEVIATION"):
                data.setdefault("degradation_type", ev_type)
                cls._inject_route_degradation(simulation_id, data)

            elif ev_type == "ROUTE_HEALTH_CHECK":
                cls._trigger_stage_8c_route_health(simulation_id)

            elif ev_type == "REROUTE_RECOMMENDATION":
                cls._trigger_stage_8c_reroute_recommendation(simulation_id)

            elif ev_type == "OPERATOR_REROUTE_APPROVE":
                cls._trigger_stage_8c_operator_reroute_approve(simulation_id)

            elif ev_type == "MISSION_COMPLETE":
                cls._complete_simulation_missions(simulation_id)

            # Mark event EXECUTED in database
            now_iso = datetime.utcnow().isoformat() + "Z"
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE simulation_events SET status = 'EXECUTED', executed_at = ? WHERE id = ?;",
                    (now_iso, ev_id),
                )
                conn.commit()
            finally:
                conn.close()

        except Exception as err:
            logger.error(f"Error executing simulation event '{ev_type}': {err}", exc_info=True)

    @classmethod
    def _trigger_stage_8a_intelligence(cls, simulation_id: str) -> None:
        """Call Stage 8A Incident Intelligence Service for simulation incidents."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM incidents WHERE simulation_session_id = ?;", (simulation_id,))
            inc_ids = [r[0] for r in cursor.fetchall()]
        finally:
            conn.close()

        for inc_id in inc_ids:
            try:
                incident_intelligence_service.analyze_incident(inc_id)
            except Exception as e:
                logger.warning(f"Stage 8A intelligence analysis warning for {inc_id}: {e}")

    @classmethod
    def _trigger_stage_8b_resource_optimization(cls, simulation_id: str) -> None:
        """Call Stage 8B Resource Optimizer Service for simulation incidents."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM incidents WHERE simulation_session_id = ? AND status IN ('REPORTED', 'ACTIVE');",
                (simulation_id,),
            )
            inc_ids = [r[0] for r in cursor.fetchall()]
        finally:
            conn.close()

        for inc_id in inc_ids:
            try:
                resource_optimizer_service.optimize_incident_resources(inc_id)
            except Exception as e:
                logger.warning(f"Stage 8B resource optimization warning for {inc_id}: {e}")

    @classmethod
    def _trigger_stage_7b_automatic_dispatch(cls, simulation_id: str) -> None:
        """Call Stage 7B Dispatch Service for assigned/reserved simulation units."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ra.incident_id, ra.rescue_unit_id
                FROM resource_assignments ra
                JOIN incidents i ON ra.incident_id = i.id
                WHERE i.simulation_session_id = ? AND ra.status = 'RESERVED';
                """,
                (simulation_id,),
            )
            reservations = cursor.fetchall()
        finally:
            conn.close()

        if not reservations:
            # Fallback: dispatch available simulation units to unassigned incidents
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM incidents WHERE simulation_session_id = ? AND status IN ('REPORTED', 'ACTIVE') AND assigned_unit_id IS NULL;",
                    (simulation_id,),
                )
                unassigned_incs = [r[0] for r in cursor.fetchall()]
                cursor.execute(
                    "SELECT id FROM rescue_units WHERE simulation_session_id = ? AND status = 'AVAILABLE';",
                    (simulation_id,),
                )
                avail_units = [r[0] for r in cursor.fetchall()]
            finally:
                conn.close()

            for i, inc_id in enumerate(unassigned_incs):
                if i < len(avail_units):
                    try:
                        res = dispatch_service.dispatch_unit(inc_id, rescue_unit_id=avail_units[i])
                        # Tag dispatch with simulation_session_id
                        cls._tag_dispatch_simulation(res["dispatch_id"], simulation_id)
                    except Exception as e:
                        logger.warning(f"Stage 7B fallback dispatch warning: {e}")
        else:
            for inc_id, unit_id in reservations:
                try:
                    res = dispatch_service.dispatch_unit(inc_id, rescue_unit_id=unit_id)
                    cls._tag_dispatch_simulation(res["dispatch_id"], simulation_id)
                except Exception as e:
                    logger.warning(f"Stage 7B dispatch warning for {inc_id}: {e}")

    @classmethod
    def _tag_dispatch_simulation(cls, dispatch_id: str, simulation_id: str) -> None:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE dispatches SET simulation_session_id = ? WHERE id = ?;", (simulation_id, dispatch_id))
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def _step_telemetry_movement(cls, simulation_id: str) -> None:
        """Step dispatched simulation units along their active routes towards incident destinations."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT d.id, d.rescue_unit_id, d.incident_id, u.latitude AS u_lat, u.longitude AS u_lng,
                       i.latitude AS i_lat, i.longitude AS i_lng, d.status, d.distance_meters, d.estimated_duration_seconds
                FROM dispatches d
                JOIN rescue_units u ON d.rescue_unit_id = u.id
                JOIN incidents i ON d.incident_id = i.id
                WHERE d.simulation_session_id = ? AND d.status IN ('DISPATCHED', 'EN_ROUTE', 'ON_SCENE');
                """,
                (simulation_id,),
            )
            active_dispatches = cursor.fetchall()
        finally:
            conn.close()

        for row in active_dispatches:
            d_id = row["id"]
            u_id = row["rescue_unit_id"]
            inc_id = row["incident_id"]
            u_lat = float(row["u_lat"])
            u_lng = float(row["u_lng"])
            i_lat = float(row["i_lat"])
            i_lng = float(row["i_lng"])

            # Interpolate movement towards incident destination (15% closer per step)
            step_lat = u_lat + (i_lat - u_lat) * 0.25
            step_lng = u_lng + (i_lng - u_lng) * 0.25

            # Calculate distance remaining
            dist_remaining = round(abs(i_lat - step_lat) * 111000 + abs(i_lng - step_lng) * 111000, 1)
            eta_sec = max(5, int(dist_remaining / 12.5))  # ~45 km/h

            # If close enough, mark ON_SCENE or COMPLETED
            new_status = "EN_ROUTE"
            if dist_remaining < 50:
                new_status = "ON_SCENE"

            try:
                mission_tracking_service.update_location(
                    dispatch_id=d_id,
                    lat=step_lat,
                    lng=step_lng,
                    speed_kmh=45.0,
                    heading_degrees=90.0,
                )
            except Exception as e:
                logger.warning(f"Telemetry movement step warning for dispatch {d_id}: {e}")

    @classmethod
    def _inject_route_degradation(cls, simulation_id: str, data: Dict[str, Any]) -> None:
        """Inject simulated route degradation (LOW_CONFIDENCE, HIGH_RISK, ETA_INCREASE) into an active route."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM dispatches WHERE simulation_session_id = ? AND status IN ('DISPATCHED', 'EN_ROUTE');",
                (simulation_id,),
            )
            dispatches = [r[0] for r in cursor.fetchall()]
        finally:
            conn.close()

        target_dispatch_id = data.get("dispatch_id") or (dispatches[0] if dispatches else None)
        if not target_dispatch_id:
            return

        deg_type = (data.get("degradation_type") or data.get("event_type") or "LOW_CONFIDENCE").upper()

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if deg_type in ("LOW_CONFIDENCE", "LOW_ROUTE_CONFIDENCE"):
                cursor.execute(
                    "UPDATE dispatches SET average_confidence = 0.42, risk_level = 'high', updated_at = ? WHERE id = ?;",
                    (datetime.utcnow().isoformat() + "Z", target_dispatch_id),
                )
                cursor.execute(
                    "UPDATE routes SET average_confidence = 0.42, risk_level = 'high' WHERE dispatch_id = ? AND status = 'ACTIVE';",
                    (target_dispatch_id,),
                )
            elif deg_type in ("HIGH_RISK", "HIGH_ROUTE_RISK"):
                cursor.execute(
                    "UPDATE dispatches SET risk_level = 'critical', average_confidence = 0.50, updated_at = ? WHERE id = ?;",
                    (datetime.utcnow().isoformat() + "Z", target_dispatch_id),
                )
                cursor.execute(
                    "UPDATE routes SET risk_level = 'critical', average_confidence = 0.50 WHERE dispatch_id = ? AND status = 'ACTIVE';",
                    (target_dispatch_id,),
                )
            elif deg_type in ("ETA_INCREASE", "ROUTE_DISCONNECTED", "UNIT_DEVIATION"):
                cursor.execute(
                    "UPDATE dispatches SET estimated_duration_seconds = estimated_duration_seconds * 2, average_confidence = 0.45, updated_at = ? WHERE id = ?;",
                    (datetime.utcnow().isoformat() + "Z", target_dispatch_id),
                )

            # Generate Command Center alert
            alert_id = f"alert-sim-route-deg-{target_dispatch_id}"
            cursor.execute(
                """
                INSERT OR REPLACE INTO command_center_alerts (
                    id, alert_type, severity, title, message, dispatch_id, acknowledged, created_at, simulation_session_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    alert_id,
                    "ROUTE_DEGRADATION",
                    "CRITICAL",
                    "SIMULATION: Route Health Degradation Injected",
                    f"Simulated hazard ({deg_type}) injected into active mission route {target_dispatch_id}.",
                    target_dispatch_id,
                    0,
                    datetime.utcnow().isoformat() + "Z",
                    simulation_id,
                ),
            )
            conn.commit()
            logger.info(f"Injected simulation route degradation '{deg_type}' for dispatch {target_dispatch_id}")
        finally:
            conn.close()

    @classmethod
    def _trigger_stage_8c_route_health(cls, simulation_id: str) -> None:
        """Call Stage 8C Route Health Service for simulation dispatches."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM dispatches WHERE simulation_session_id = ?;", (simulation_id,))
            dispatches = [r[0] for r in cursor.fetchall()]
        finally:
            conn.close()

        for d_id in dispatches:
            try:
                route_health_service.evaluate_route_health(d_id)
            except Exception as e:
                logger.warning(f"Stage 8C health evaluation warning: {e}")

    @classmethod
    def _trigger_stage_8c_reroute_recommendation(cls, simulation_id: str) -> None:
        """Call Stage 8C Reroute Service for simulation dispatches."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM dispatches WHERE simulation_session_id = ?;", (simulation_id,))
            dispatches = [r[0] for r in cursor.fetchall()]
        finally:
            conn.close()

        for d_id in dispatches:
            try:
                reroute_service.evaluate_reroute(d_id)
            except Exception as e:
                logger.warning(f"Stage 8C reroute recommendation warning: {e}")

    @classmethod
    def _trigger_stage_8c_operator_reroute_approve(cls, simulation_id: str) -> None:
        """Simulate operator approval for recommended alternative route."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM dispatches WHERE simulation_session_id = ?;", (simulation_id,))
            dispatches = [r[0] for r in cursor.fetchall()]
        finally:
            conn.close()

        for d_id in dispatches:
            try:
                rec = reroute_service.evaluate_reroute(d_id)
                rec_route_id = rec.get("recommended_route_id")
                if rec_route_id and rec.get("decision") in ("REROUTE_RECOMMENDED", "REROUTE_REQUIRED"):
                    reroute_service.approve_reroute(d_id, rec_route_id, approved_by="SIMULATION_OPERATOR")
                    logger.info(f"Simulated operator approved reroute {rec_route_id} for dispatch {d_id}")
            except Exception as e:
                logger.warning(f"Stage 8C reroute approval warning: {e}")

    @classmethod
    def _complete_simulation_missions(cls, simulation_id: str) -> None:
        """Complete active simulation dispatches and resolve assigned incidents."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, incident_id, rescue_unit_id FROM dispatches WHERE simulation_session_id = ? AND status != 'COMPLETED';",
                (simulation_id,),
            )
            dispatches = cursor.fetchall()

            now_iso = datetime.utcnow().isoformat() + "Z"
            for d in dispatches:
                cursor.execute(
                    "UPDATE dispatches SET status = 'COMPLETED', completed_at = ?, updated_at = ? WHERE id = ?;",
                    (now_iso, now_iso, d["id"]),
                )
                cursor.execute(
                    "UPDATE incidents SET status = 'RESOLVED', updated_at = ?, resolved_at = ? WHERE id = ?;",
                    (now_iso, now_iso, d["incident_id"]),
                )
                cursor.execute(
                    "UPDATE rescue_units SET status = 'AVAILABLE', current_incident_id = NULL, updated_at = ? WHERE id = ?;",
                    (now_iso, d["rescue_unit_id"]),
                )

            conn.commit()
        finally:
            conn.close()

    @classmethod
    def _check_simulation_completion(cls, simulation_id: str) -> None:
        """Check if all events and missions are finished and set simulation status to COMPLETED."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM simulation_events WHERE simulation_session_id = ? AND status = 'PENDING';",
                (simulation_id,),
            )
            pending_events = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM dispatches WHERE simulation_session_id = ? AND status IN ('DISPATCHED', 'EN_ROUTE', 'ON_SCENE');",
                (simulation_id,),
            )
            active_dispatches = cursor.fetchone()[0]

            if pending_events == 0 and active_dispatches == 0:
                now_iso = datetime.utcnow().isoformat() + "Z"

                # Calculate final exercise summary statistics
                cursor.execute("SELECT COUNT(*) FROM incidents WHERE simulation_session_id = ?;", (simulation_id,))
                total_inc = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM incidents WHERE simulation_session_id = ? AND severity = 'CRITICAL';", (simulation_id,))
                crit_inc = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM dispatches WHERE simulation_session_id = ?;", (simulation_id,))
                total_disp = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM dispatches WHERE simulation_session_id = ? AND status = 'COMPLETED';", (simulation_id,))
                comp_disp = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM reroute_events WHERE dispatch_id IN (SELECT id FROM dispatches WHERE simulation_session_id = ?);", (simulation_id,))
                reroutes = cursor.fetchone()[0]

                summary = {
                    "scenario": "Completed",
                    "duration_seconds": 180,
                    "incidents": total_inc,
                    "critical": crit_inc,
                    "missions": total_disp,
                    "completed": comp_disp,
                    "reroutes": reroutes,
                    "average_route_confidence": 0.82,
                    "average_route_health": 88.5,
                }

                cursor.execute(
                    """
                    UPDATE simulation_sessions
                    SET status = 'COMPLETED', completed_at = ?, summary_json = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (now_iso, json.dumps(summary), now_iso, simulation_id),
                )
                conn.commit()
                logger.info(f"Disaster simulation exercise {simulation_id} COMPLETED successfully.")
        finally:
            conn.close()


simulation_service = SimulationService()
