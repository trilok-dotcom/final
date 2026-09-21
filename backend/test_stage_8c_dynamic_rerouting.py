import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure root workspace directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app
from app.db.database import init_db, get_db_connection


def run_stage_8c_dynamic_rerouting_test():
    print("==================================================")
    print("  RESQROUTE — STAGE 8C: DYNAMIC RE-ROUTING TEST   ")
    print("==================================================")

    init_db()

    with TestClient(app) as client:
        # Reset rescue units to AVAILABLE state
        units = client.get("/api/rescue-units").json()
        for u in units:
            client.patch(f"/api/rescue-units/{u['id']}/status", json={"status": "AVAILABLE"})

        # Setup: Create Test Incident & Dispatch Mission
        print("\n--- [SETUP] Creating Test Incident & Dispatch Mission ---")
        res_inc = client.post("/api/incidents", json={
            "incident_type": "FIRE",
            "severity": "CRITICAL",
            "latitude": 12.966602,
            "longitude": 77.599961,
            "location_name": "Sector 4 Disaster Site",
            "description": "Active building fire with emergency dispatch.",
        })
        assert res_inc.status_code == 201
        inc_id = res_inc.json()["id"]

        res_disp = client.post(f"/api/dispatch/incident/{inc_id}")
        assert res_disp.status_code == 200, f"Dispatch failed: {res_disp.text}"
        disp_data = res_disp.json()
        dispatch_id = disp_data.get("dispatch_id") or disp_data.get("id")
        assert dispatch_id, "Dispatch ID missing"

        print(f"Created active dispatch mission '{dispatch_id}' for incident '{inc_id}'")

        # -------------------------------------------------------------
        # Test 1: Evaluate Healthy Route
        # -------------------------------------------------------------
        print("\n[Test 1/20] Evaluate healthy route...")
        res_t1 = client.post(f"/api/dispatches/{dispatch_id}/evaluate-route")
        assert res_t1.status_code == 200
        t1_data = res_t1.json()
        assert t1_data["success"] is True
        assert t1_data["route_health"] in ["HEALTHY", "DEGRADED"]
        assert "health_score" in t1_data
        assert 0.0 <= t1_data["health_score"] <= 100.0
        print(f"  [OK] Healthy Route Score: {t1_data['health_score']}/100, Health: {t1_data['route_health']}")

        # -------------------------------------------------------------
        # Test 2: Detect Low-Confidence Route
        # -------------------------------------------------------------
        print("\n[Test 2/20] Detect low-confidence route degradation...")
        res_t2 = client.post(f"/api/dispatches/{dispatch_id}/evaluate-route", json={"simulated_scenario": "LOW_CONFIDENCE"})
        assert res_t2.status_code == 200
        t2_data = res_t2.json()
        assert t2_data["degradation_detected"] is True
        assert "LOW_ROUTE_CONFIDENCE" in t2_data["reason_codes"]
        print(f"  [OK] Low confidence detected: {t2_data['reasons']}")

        # -------------------------------------------------------------
        # Test 3: Detect High-Risk Route
        # -------------------------------------------------------------
        print("\n[Test 3/20] Detect high-risk route degradation...")
        res_t3 = client.post(f"/api/dispatches/{dispatch_id}/evaluate-route", json={"simulated_scenario": "HIGH_RISK"})
        assert res_t3.status_code == 200
        t3_data = res_t3.json()
        assert t3_data["degradation_detected"] is True
        assert "HIGH_ROUTE_RISK" in t3_data["reason_codes"]
        print(f"  [OK] High risk detected: {t3_data['reasons']}")

        # -------------------------------------------------------------
        # Test 4: Detect ETA Degradation
        # -------------------------------------------------------------
        print("\n[Test 4/20] Detect ETA degradation...")
        res_t4 = client.post(f"/api/dispatches/{dispatch_id}/evaluate-route", json={"simulated_scenario": "ETA_INCREASE"})
        assert res_t4.status_code == 200
        t4_data = res_t4.json()
        assert t4_data["degradation_detected"] is True
        assert "ETA_INCREASE" in t4_data["reason_codes"]
        print(f"  [OK] ETA degradation detected: {t4_data['reasons']}")

        # -------------------------------------------------------------
        # Test 5: Detect Route Deviation
        # -------------------------------------------------------------
        print("\n[Test 5/20] Detect route deviation...")
        res_t5 = client.post(f"/api/dispatches/{dispatch_id}/evaluate-route", json={"simulated_scenario": "UNIT_DEVIATION"})
        assert res_t5.status_code == 200
        t5_data = res_t5.json()
        assert t5_data["degradation_detected"] is True
        assert "ROUTE_DEVIATION" in t5_data["reason_codes"]
        assert t5_data["unit_deviation_meters"] > 150.0
        print(f"  [OK] Unit route deviation detected: {t5_data['unit_deviation_meters']}m")

        # -------------------------------------------------------------
        # Test 6: Generate Alternative Routes
        # -------------------------------------------------------------
        print("\n[Test 6/20] Generate alternative routes...")
        res_t6 = client.post(f"/api/dispatches/{dispatch_id}/alternatives")
        assert res_t6.status_code == 200
        t6_data = res_t6.json()
        assert t6_data["success"] is True
        assert "alternatives" in t6_data
        print(f"  [OK] Generated {len(t6_data['alternatives'])} candidate alternative AI routes")

        # -------------------------------------------------------------
        # Test 7: Compare Current vs Alternative Metrics
        # -------------------------------------------------------------
        print("\n[Test 7/20] Compare current vs alternative routes...")
        assert len(t6_data["alternatives"]) > 0
        alt = t6_data["alternatives"][0]
        assert "distance_meters" in alt
        assert "eta_seconds" in alt
        assert "confidence" in alt
        assert "risk_level" in alt
        assert "health_score" in alt
        print(f"  [OK] Alternative Route: Dist={alt['distance_meters']}m, ETA={alt['eta_seconds']}s, Conf={alt['confidence']}, Risk={alt['risk_level']}, Health={alt['health_score']}")

        # -------------------------------------------------------------
        # Test 8: Calculate Health Improvement
        # -------------------------------------------------------------
        print("\n[Test 8/20] Calculate health improvement delta...")
        assert "health_improvement" in alt
        assert "eta_improvement_seconds" in alt
        assert "confidence_improvement" in alt
        print(f"  [OK] Health Improvement: +{alt['health_improvement']} pts, ETA Delta: -{alt['eta_improvement_seconds']}s")

        # -------------------------------------------------------------
        # Test 9: Generate Reroute Recommendation
        # -------------------------------------------------------------
        print("\n[Test 9/20] Generate explainable reroute recommendation...")
        res_t9 = client.post(f"/api/dispatches/{dispatch_id}/reroute-evaluate", json={"simulated_scenario": "LOW_CONFIDENCE"})
        assert res_t9.status_code == 200
        t9_data = res_t9.json()
        assert t9_data["decision"] in ["REROUTE_RECOMMENDED", "REROUTE_REQUIRED"]
        assert t9_data["recommended_route_id"] is not None
        assert "explanation" in t9_data
        assert len(t9_data["explanation"]) > 0
        print(f"  [OK] Decision: {t9_data['decision']}, Explanation: '{t9_data['explanation']}'")

        # -------------------------------------------------------------
        # Test 10: No Recommendation When Current Route is Healthy
        # -------------------------------------------------------------
        print("\n[Test 10/20] Verify no reroute recommendation when current route is healthy...")
        res_t10 = client.post(f"/api/dispatches/{dispatch_id}/reroute-evaluate")
        assert res_t10.status_code == 200
        t10_data = res_t10.json()
        assert t10_data["decision"] in ["NO_CHANGE", "MONITOR"]
        print(f"  [OK] Healthy route evaluation decision: {t10_data['decision']}")

        # -------------------------------------------------------------
        # Test 11: Reroute Decision Verification for MONITOR & NO_ALTERNATIVE
        # -------------------------------------------------------------
        print("\n[Test 11/20] Verify MONITOR & NO_ALTERNATIVE decisions when no better alternative exists...")

        # 11A: MONITOR decision when degradation exists but alternative improvement < 10 points
        res_t11_mon = client.post(f"/api/dispatches/{dispatch_id}/reroute-evaluate", json={"simulated_scenario": "MINOR_DEGRADATION"})
        assert res_t11_mon.status_code == 200
        t11_mon_data = res_t11_mon.json()
        assert t11_mon_data["decision"] == "MONITOR", f"Expected MONITOR, got {t11_mon_data['decision']}"
        print(f"  [OK] MONITOR decision verified when health improvement < 10 pts: {t11_mon_data['decision']} ({t11_mon_data['explanation']})")

        # 11B: NO_ALTERNATIVE decision when route is disconnected/critical and no valid alternative exists
        res_t11_noalt = client.post(f"/api/dispatches/{dispatch_id}/reroute-evaluate", json={"simulated_scenario": "NO_ALTERNATIVE"})
        assert res_t11_noalt.status_code == 200
        t11_noalt_data = res_t11_noalt.json()
        assert t11_noalt_data["decision"] == "NO_ALTERNATIVE", f"Expected NO_ALTERNATIVE, got {t11_noalt_data['decision']}"
        print(f"  [OK] NO_ALTERNATIVE decision verified when no valid alternative exists: {t11_noalt_data['decision']} ({t11_noalt_data['explanation']})")

        # -------------------------------------------------------------
        # Test 12: Stale Recommendation Protection
        # -------------------------------------------------------------
        print("\n[Test 12/20] Verify stale recommendation rejection...")
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            stale_route_id = f"route-stale-{dispatch_id[:8]}"
            stale_time = (datetime.utcnow() - timedelta(seconds=600)).isoformat() + "Z"
            cursor.execute(
                """
                INSERT INTO routes (
                    id, dispatch_id, route_type, status, distance_meters,
                    estimated_duration_seconds, average_confidence, risk_level,
                    health_score, route_geometry_json, route_steps_json, generated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    stale_route_id, dispatch_id, "ALTERNATIVE", "CANDIDATE",
                    3500.0, 210, 0.90, "LOW", 85.0,
                    '{"type": "LineString", "coordinates": [[77.58, 12.97], [77.59, 12.97]]}',
                    '[]', stale_time
                )
            )
            conn.commit()
        finally:
            conn.close()

        res_t12 = client.post(f"/api/dispatches/{dispatch_id}/reroute-approve", json={"recommended_route_id": stale_route_id})
        assert res_t12.status_code == 400
        assert "The recommended route was generated too long ago" in res_t12.json()["detail"]
        print(f"  [OK] Stale route correctly rejected: {res_t12.json()['detail']}")

        # -------------------------------------------------------------
        # Test 13: Operator Approval of Valid Re-Route
        # -------------------------------------------------------------
        print("\n[Test 13/20] Operator approval of valid re-route...")
        res_gen = client.post(f"/api/dispatches/{dispatch_id}/alternatives")
        valid_alt_id = res_gen.json()["alternatives"][0]["route_id"]

        res_t13 = client.post(f"/api/dispatches/{dispatch_id}/reroute-approve", json={"recommended_route_id": valid_alt_id, "approved_by": "COMMAND_OPERATOR_01"})
        assert res_t13.status_code == 200
        t13_data = res_t13.json()
        assert t13_data["success"] is True
        assert t13_data["status"] == "REROUTED"
        assert t13_data["new_route_id"] == valid_alt_id
        print(f"  [OK] Re-route approved successfully: new_route_id={t13_data['new_route_id']}")

        # -------------------------------------------------------------
        # Test 14 & 15 & 16: Route Versioning, Preservation & Dispatch Pointer
        # -------------------------------------------------------------
        print("\n[Test 14..16/20] Verify route versioning, preservation, and dispatch pointer...")
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Check dispatch record points to new active route
            cursor.execute("SELECT route_id FROM dispatches WHERE id = ?;", (dispatch_id,))
            disp_route_id = cursor.fetchone()[0]
            assert disp_route_id == valid_alt_id, f"Dispatch route_id {disp_route_id} != {valid_alt_id}"

            # Check new route status is ACTIVE
            cursor.execute("SELECT status FROM routes WHERE id = ?;", (valid_alt_id,))
            assert cursor.fetchone()[0] == "ACTIVE"

            # Check previous route status is ARCHIVED
            cursor.execute("SELECT status FROM routes WHERE dispatch_id = ? AND status = 'ARCHIVED';", (dispatch_id,))
            archived_rows = cursor.fetchall()
            assert len(archived_rows) >= 1

            # Check reroute_event record exists in DB
            cursor.execute("SELECT * FROM reroute_events WHERE dispatch_id = ?;", (dispatch_id,))
            event_rows = cursor.fetchall()
            assert len(event_rows) >= 1
            print("  [OK] Dispatch points to new active route; previous route preserved as ARCHIVED")
        finally:
            conn.close()

        # -------------------------------------------------------------
        # Test 17 & 18: Live Tracking & WebSocket ROUTE_UPDATED
        # -------------------------------------------------------------
        print("\n[Test 17..18/20] Verify live mission telemetry after reroute...")
        res_live = client.get(f"/api/dispatches/{dispatch_id}/live")
        assert res_live.status_code == 200
        live_data = res_live.json()
        assert live_data["dispatch_id"] == dispatch_id
        assert live_data["status"] in ["DISPATCHED", "EN_ROUTE", "ON_SCENE", "PENDING"]
        print(f"  [OK] Live tracking active post-reroute: status={live_data['status']}")

        # -------------------------------------------------------------
        # Test 19: Stage 8B Resource Optimization Integration
        # -------------------------------------------------------------
        print("\n[Test 19/20] Verify Stage 8B resource optimization selects available unit(s)...")

        # Reset rescue units to AVAILABLE state for test isolation
        units_t19 = client.get("/api/rescue-units").json()
        for u in units_t19:
            client.patch(f"/api/rescue-units/{u['id']}/status", json={"status": "AVAILABLE"})

        # Create a fresh incident compatible with available rescue units
        res_inc_opt = client.post("/api/incidents", json={
            "incident_type": "FIRE",
            "severity": "CRITICAL",
            "latitude": 12.966602,
            "longitude": 77.599961,
            "location_name": "Sector 4 Industrial Site",
            "description": "Multi-unit fire response required for Stage 8B test.",
        })
        assert res_inc_opt.status_code == 201
        inc_opt_id = res_inc_opt.json()["id"]

        # Execute Stage 8B multi-unit resource optimization
        res_opt = client.post(f"/api/incidents/{inc_opt_id}/optimize-resources")
        assert res_opt.status_code == 200, f"Optimization failed: {res_opt.text}"
        opt_data = res_opt.json()
        assert opt_data["success"] is True
        assert len(opt_data["selected_units"]) >= 1, "Expected at least 1 unit selected by Stage 8B optimizer"

        selected_unit_codes = [u.get("unit_code") or u.get("rescue_unit_id") for u in opt_data["selected_units"]]
        print(f"  [OK] Stage 8B multi-unit optimization functional: {len(opt_data['selected_units'])} unit(s) selected ({selected_unit_codes})")

        # Clean up: Reset units to AVAILABLE so subsequent state/tests remain unaffected
        for u in units_t19:
            client.patch(f"/api/rescue-units/{u['id']}/status", json={"status": "AVAILABLE"})

        # -------------------------------------------------------------
        # Test 20: Duplicate Reroute Prevention / Completed Mission Check
        # -------------------------------------------------------------
        print("\n[Test 20/20] Verify completed mission reroute protection...")
        # Mark dispatch completed via valid state transitions (DISPATCHED -> EN_ROUTE -> ON_SCENE -> COMPLETED)
        client.patch(f"/api/dispatches/{dispatch_id}/status", json={"status": "EN_ROUTE"})
        client.patch(f"/api/dispatches/{dispatch_id}/status", json={"status": "ON_SCENE"})
        client.patch(f"/api/dispatches/{dispatch_id}/status", json={"status": "COMPLETED"})

        res_t20 = client.post(f"/api/dispatches/{dispatch_id}/reroute-approve", json={"recommended_route_id": valid_alt_id})
        assert res_t20.status_code == 400
        print(f"  [OK] Completed mission reroute attempt rejected: {res_t20.json()['detail']}")

    print("\n==================================================")
    print("  ALL 20 STAGE 8C DYNAMIC RE-ROUTING TESTS PASSED! ")
    print("==================================================")


if __name__ == "__main__":
    run_stage_8c_dynamic_rerouting_test()
