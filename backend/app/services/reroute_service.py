import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from app.db.database import get_db_connection
from app.services.dispatch_service import dispatch_service
from app.services.route_health_service import route_health_service, STALE_ROUTE_THRESHOLD_SECONDS
from app.services.dynamic_routing_service import dynamic_routing_service
from app.api.websocket import ws_manager
from app.utils.logging import get_logger

logger = get_logger("app.services.reroute_service")


class RerouteService:
    """Deterministic Re-Route Decision & Operator Approval Engine for RESQROUTE."""

    @classmethod
    def evaluate_reroute(
        cls, dispatch_id: str, simulated_scenario: Optional[str] = None
    ) -> Dict[str, Any]:
        disp = dispatch_service.get_dispatch(dispatch_id)
        if not disp:
            raise ValueError(f"Dispatch mission '{dispatch_id}' not found.")

        # 1. Evaluate current route health
        health_eval = route_health_service.evaluate_route_health(
            dispatch_id, simulated_scenario=simulated_scenario
        )

        current_route = health_eval["current_route"]
        current_route_id = current_route["route_id"]
        current_health_score = health_eval["health_score"]
        health_status = health_eval["route_health"]
        degradation_detected = health_eval["degradation_detected"]
        reason_codes = health_eval["reason_codes"]
        reasons = health_eval["reasons"]

        # 2. Generate alternative routes
        alt_eval = dynamic_routing_service.generate_alternative_routes(
            dispatch_id, simulated_scenario=simulated_scenario
        )
        alternatives = alt_eval.get("alternatives") or []

        best_alt = None
        if alternatives:
            # Sort alternatives by health score descending
            sorted_alts = sorted(alternatives, key=lambda x: x["health_score"], reverse=True)
            best_alt = sorted_alts[0]

        # 3. Deterministic Decision Logic
        decision = "NO_CHANGE"
        recommended_route_id = None
        health_imp = 0.0
        eta_imp = 0
        conf_imp = 0.0
        risk_change = f"{current_route['risk_level']} → {current_route['risk_level']}"
        explanation = "Current route is healthy and optimal. No rerouting required."

        if "ROUTE_DISCONNECTED" in reason_codes or health_status == "CRITICAL":
            if best_alt:
                decision = "REROUTE_REQUIRED"
                recommended_route_id = best_alt["route_id"]
                health_imp = best_alt["health_improvement"]
                eta_imp = best_alt["eta_improvement_seconds"]
                conf_imp = best_alt["confidence_improvement"]
                risk_change = best_alt["risk_change"]
                reason_codes.append("CRITICAL_ROUTE_BLOCKAGE")
                explanation = (
                    f"Current route is disconnected or blocked. Alternative {best_alt['route_name']} "
                    f"provides valid connectivity with {best_alt['confidence']:.2f} AI confidence and {best_alt['risk_level']} risk."
                )
            else:
                decision = "NO_ALTERNATIVE"
                explanation = "Current route is disconnected, but no valid alternative AI route could be generated."

        elif degradation_detected or current_health_score < 75.0:
            if best_alt and best_alt["health_improvement"] >= 10.0:
                decision = "REROUTE_RECOMMENDED"
                recommended_route_id = best_alt["route_id"]
                health_imp = best_alt["health_improvement"]
                eta_imp = best_alt["eta_improvement_seconds"]
                conf_imp = best_alt["confidence_improvement"]
                risk_change = best_alt["risk_change"]
                reason_codes.append("ALTERNATIVE_HIGHER_CONFIDENCE")
                
                exp_parts = []
                if "LOW_ROUTE_CONFIDENCE" in reason_codes:
                    exp_parts.append(f"AI confidence dropped to {current_route['confidence']:.2f}")
                if "HIGH_ROUTE_RISK" in reason_codes:
                    exp_parts.append(f"risk level increased to {current_route['risk_level']}")
                if "ETA_INCREASE" in reason_codes:
                    exp_parts.append("ETA increased significantly")
                if "ROUTE_DEVIATION" in reason_codes:
                    exp_parts.append("rescue unit deviated from route")

                reasons_str = " and ".join(exp_parts) if exp_parts else "route degradation detected"

                explanation = (
                    f"Current route health degraded ({reasons_str}). "
                    f"Alternative {best_alt['route_name']} provides {best_alt['confidence']:.2f} AI confidence, "
                    f"{best_alt['risk_level']} risk, and +{health_imp:.1f} health points improvement."
                )
            elif best_alt:
                decision = "MONITOR"
                explanation = (
                    "Route degradation detected, but existing alternatives do not provide sufficient health improvement (<10 points). "
                    "Recommend continuous monitoring."
                )
            else:
                decision = "MONITOR"
                explanation = "Route degradation detected, but no alternative routes are available at this time. Monitoring status."

        now_iso = datetime.utcnow().isoformat() + "Z"

        # 4. Store evaluation in database
        eval_id = f"eval-{uuid.uuid4().hex[:8]}"
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO route_evaluations (
                    id, dispatch_id, evaluation_type, current_route_health,
                    current_confidence, current_risk_level, current_eta_seconds,
                    alternative_route_count, recommended_route_id, decision,
                    reason_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    eval_id,
                    dispatch_id,
                    "SIMULATION" if health_eval.get("is_simulated") else "AUTOMATED",
                    health_status,
                    current_route["confidence"],
                    current_route["risk_level"],
                    current_route["eta_seconds"],
                    len(alternatives),
                    recommended_route_id,
                    decision,
                    json.dumps({"reason_codes": reason_codes, "explanation": explanation, "reasons": reasons}),
                    now_iso,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return {
            "success": True,
            "dispatch_id": dispatch_id,
            "decision": decision,
            "route_health": health_status,
            "health_score": current_health_score,
            "current_route_id": current_route_id,
            "recommended_route_id": recommended_route_id,
            "recommended_route": best_alt,
            "health_improvement": health_imp,
            "eta_improvement_seconds": eta_imp,
            "confidence_improvement": conf_imp,
            "risk_change": risk_change,
            "reason_codes": reason_codes,
            "reasons": reasons,
            "explanation": explanation,
            "alternatives": alternatives,
            "evaluated_at": now_iso,
        }

    @classmethod
    def approve_reroute(
        cls,
        dispatch_id: str,
        recommended_route_id: Optional[str] = None,
        approved_by: str = "DISPATCH_OPERATOR",
    ) -> Dict[str, Any]:
        disp = dispatch_service.get_dispatch(dispatch_id)
        if not disp:
            raise ValueError(f"Dispatch mission '{dispatch_id}' not found.")

        disp_status = disp["status"].upper()
        if disp_status in ["COMPLETED", "CANCELLED"]:
            raise ValueError(f"Cannot re-route a {disp_status} dispatch mission.")

        # 1. Fetch candidate route record from database
        conn = get_db_connection()
        candidate_row = None
        try:
            cursor = conn.cursor()
            if recommended_route_id:
                cursor.execute(
                    "SELECT * FROM routes WHERE id = ? AND dispatch_id = ?;",
                    (recommended_route_id, dispatch_id),
                )
                candidate_row = cursor.fetchone()
            else:
                cursor.execute(
                    """
                    SELECT * FROM routes 
                    WHERE dispatch_id = ? AND status = 'CANDIDATE' 
                    ORDER BY generated_at DESC LIMIT 1;
                    """,
                    (dispatch_id,),
                )
                candidate_row = cursor.fetchone()
        finally:
            conn.close()

        if not candidate_row:
            raise ValueError("No valid candidate alternative route found for approval.")

        cand = dict(candidate_row)
        new_route_id = cand["id"]
        gen_time_str = cand["generated_at"]

        # 2. Stale Route Protection Check
        try:
            # Parse ISO timestamp
            gen_time_str_clean = gen_time_str.replace("Z", "")
            gen_dt = datetime.fromisoformat(gen_time_str_clean)
            now_dt = datetime.utcnow()
            elapsed_sec = (now_dt - gen_dt).total_seconds()

            if elapsed_sec > STALE_ROUTE_THRESHOLD_SECONDS:
                return {
                    "success": False,
                    "error": "ROUTE_RECALCULATION_REQUIRED",
                    "message": "The recommended route was generated too long ago. Recalculate alternatives before approval.",
                    "elapsed_seconds": int(elapsed_sec),
                }
        except Exception as e:
            logger.warning(f"Timestamp parse issue during stale check: {e}")

        previous_route_id = disp.get("route_id") or f"route-{dispatch_id[:8]}"
        now_iso = datetime.utcnow().isoformat() + "Z"

        old_dist = float(disp.get("distance_meters") or 0.0)
        old_eta = int(disp.get("estimated_duration_seconds") or 0)
        old_conf = float(disp.get("average_confidence") or 1.0)
        old_risk = str(disp.get("risk_level") or "low").upper()

        new_dist = float(cand["distance_meters"])
        new_eta = int(cand["estimated_duration_seconds"])
        new_conf = float(cand["average_confidence"])
        new_risk = str(cand["risk_level"]).upper()

        # 3. Perform Route Replacement & Versioning in DB
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Ensure previous route entry exists in routes table before archiving
            cursor.execute("SELECT id FROM routes WHERE id = ?;", (previous_route_id,))
            prev_exists = cursor.fetchone()
            if not prev_exists:
                cursor.execute(
                    """
                    INSERT INTO routes (
                        id, dispatch_id, route_type, status, distance_meters,
                        estimated_duration_seconds, average_confidence, risk_level,
                        health_score, route_geometry_json, route_steps_json, generated_at, archived_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        previous_route_id,
                        dispatch_id,
                        "ORIGINAL",
                        "ARCHIVED",
                        old_dist,
                        old_eta,
                        old_conf,
                        old_risk,
                        old_conf * 100.0,
                        disp.get("route_geometry_json") or "{}",
                        disp.get("route_steps_json") or "[]",
                        disp.get("created_at") or now_iso,
                        now_iso,
                    ),
                )
            else:
                cursor.execute(
                    """
                    UPDATE routes 
                    SET status = 'ARCHIVED', archived_at = ? 
                    WHERE dispatch_id = ? AND status = 'ACTIVE';
                    """,
                    (now_iso, dispatch_id),
                )

            # Activate new route
            cursor.execute(
                """
                UPDATE routes 
                SET status = 'ACTIVE' 
                WHERE id = ?;
                """,
                (new_route_id,),
            )

            # Update Dispatch Record
            cursor.execute(
                """
                UPDATE dispatches 
                SET route_id = ?,
                    distance_meters = ?,
                    estimated_duration_seconds = ?,
                    average_confidence = ?,
                    risk_level = ?,
                    route_geometry_json = ?,
                    route_steps_json = ?,
                    updated_at = ?
                WHERE id = ?;
                """,
                (
                    new_route_id,
                    new_dist,
                    new_eta,
                    new_conf,
                    new_risk,
                    cand["route_geometry_json"],
                    cand["route_steps_json"],
                    now_iso,
                    dispatch_id,
                ),
            )

            # Persist Reroute Event
            event_id = f"evt-{uuid.uuid4().hex[:8]}"
            cursor.execute(
                """
                INSERT INTO reroute_events (
                    id, dispatch_id, previous_route_id, new_route_id, trigger, reason,
                    old_distance_meters, new_distance_meters, old_eta_seconds, new_eta_seconds,
                    old_confidence, new_confidence, old_risk_level, new_risk_level,
                    approved_by, approved_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event_id,
                    dispatch_id,
                    previous_route_id,
                    new_route_id,
                    "OPERATOR_APPROVED",
                    "Operator confirmed AI recommended re-route for enhanced safety and reduced ETA.",
                    old_dist,
                    new_dist,
                    old_eta,
                    new_eta,
                    old_conf,
                    new_conf,
                    old_risk,
                    new_risk,
                    approved_by,
                    now_iso,
                    now_iso,
                ),
            )
            conn.commit()
            logger.info(f"Dispatch '{dispatch_id}' successfully re-routed from '{previous_route_id}' to '{new_route_id}'.")
        finally:
            conn.close()

        # 4. Broadcast WebSocket Event `ROUTE_UPDATED`
        try:
            ws_payload = {
                "event": "ROUTE_UPDATED",
                "dispatch_id": dispatch_id,
                "previous_route_id": previous_route_id,
                "new_route_id": new_route_id,
                "distance_remaining_meters": new_dist,
                "eta_seconds": new_eta,
                "confidence": new_conf,
                "risk_level": new_risk,
                "route_geometry": json.loads(cand["route_geometry_json"]),
                "timestamp": now_iso,
            }
            ws_manager.broadcast_sync(ws_payload)
        except Exception as e:
            logger.error(f"WebSocket broadcast error on ROUTE_UPDATED: {e}")

        return {
            "success": True,
            "status": "REROUTED",
            "dispatch_id": dispatch_id,
            "previous_route_id": previous_route_id,
            "new_route_id": new_route_id,
            "distance_meters": new_dist,
            "eta_seconds": new_eta,
            "confidence": new_conf,
            "risk_level": new_risk,
            "approved_at": now_iso,
        }


reroute_service = RerouteService()
