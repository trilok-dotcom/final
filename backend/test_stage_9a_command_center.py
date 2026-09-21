import sys
import time
from datetime import datetime
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure root workspace directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app
from app.db.database import init_db, get_db_connection


def run_stage_9a_command_center_test():
    print("==================================================")
    print("  RESQROUTE — STAGE 9A: COMMAND CENTER TEST SUITE ")
    print("==================================================")

    init_db()

    passed_tests = 0
    total_tests = 0

    def assert_test(condition: bool, test_name: str, details: str = ""):
        nonlocal passed_tests, total_tests
        total_tests += 1
        if condition:
            passed_tests += 1
            print(f" [PASS] Test {total_tests:02d}: {test_name}")
        else:
            print(f" [FAIL] Test {total_tests:02d}: {test_name} - {details}")
            raise AssertionError(f"Test {test_name} failed: {details}")

    with TestClient(app) as client:
        # Reset all units to AVAILABLE before beginning
        units = client.get("/api/rescue-units").json()
        for u in units:
            client.patch(f"/api/rescue-units/{u['id']}/status", json={"status": "AVAILABLE"})

        # -------------------------------------------------------------
        # TEST 01: GET /api/command-center/overview Endpoint Availability
        # -------------------------------------------------------------
        res1 = client.get("/api/command-center/overview")
        assert_test(res1.status_code == 200, "GET /api/command-center/overview returns 200 OK")
        data1 = res1.json()

        # -------------------------------------------------------------
        # TEST 02: GET /api/v1/command-center/overview Endpoint Availability
        # -------------------------------------------------------------
        res2 = client.get("/api/v1/command-center/overview")
        assert_test(res2.status_code == 200, "GET /api/v1/command-center/overview returns 200 OK")

        # -------------------------------------------------------------
        # TEST 03: Summary Cards Metrics Structure & Non-Negative Validation
        # -------------------------------------------------------------
        summary = data1.get("summary", {})
        expected_summary_keys = [
            "total_incidents", "open_incidents", "critical_incidents", "high_incidents",
            "total_units", "available_units", "busy_units", "active_missions",
            "pending_dispatches", "degraded_routes", "unacknowledged_alerts"
        ]
        has_all_summary_keys = all(k in summary for k in expected_summary_keys)
        all_non_negative = all(isinstance(v, int) and v >= 0 for v in summary.values())
        assert_test(has_all_summary_keys and all_non_negative, "Summary cards contain valid non-negative metrics")

        # -------------------------------------------------------------
        # TEST 04: Priority Queue Structure
        # -------------------------------------------------------------
        pq = data1.get("priority_queue", [])
        assert_test(isinstance(pq, list), "Priority queue is returned as a list")

        # -------------------------------------------------------------
        def get_inc_id(res_json):
            if isinstance(res_json, dict):
                return res_json.get("id") or res_json.get("incident_id") or (res_json.get("incident") or {}).get("id")
            return str(res_json)

        # -------------------------------------------------------------
        # TEST 05: Priority Queue Ordering by Intelligence Score
        # Create multiple incidents with different severities to verify ordering
        # -------------------------------------------------------------
        inc_medium_raw = client.post("/api/incidents", json={
            "incident_type": "MEDICAL",
            "severity": "MEDIUM",
            "latitude": 12.971598,
            "longitude": 77.5946,
            "location_name": "MG Road Clinic",
            "description": "Minor medical call.",
        }).json()
        inc_medium_id = get_inc_id(inc_medium_raw)

        inc_critical_raw = client.post("/api/incidents", json={
            "incident_type": "FIRE",
            "severity": "CRITICAL",
            "latitude": 12.980000,
            "longitude": 77.600000,
            "location_name": "Industrial Complex",
            "description": "Massive building fire with trapped casualties.",
        }).json()
        inc_critical_id = get_inc_id(inc_critical_raw)

        res_overview = client.get("/api/command-center/overview").json()
        pq_latest = res_overview.get("priority_queue", [])
        scores = [item["intelligence_score"] for item in pq_latest]
        is_sorted = all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))
        assert_test(is_sorted and len(pq_latest) >= 2, "Priority queue is correctly sorted descending by intelligence score")

        # -------------------------------------------------------------
        # TEST 06: Priority Queue Intelligence Integration
        # -------------------------------------------------------------
        first_item = pq_latest[0]
        has_intel_fields = "intelligence" in first_item and "urgency_level" in first_item and "recommended_actions" in first_item
        assert_test(has_intel_fields, "Priority queue integrates Stage 8A incident intelligence metadata")

        # -------------------------------------------------------------
        # TEST 07: Active Mission Telemetry Integration
        # Dispatch a unit for the critical incident
        # -------------------------------------------------------------
        res_disp = client.post(f"/api/dispatch/incident/{inc_critical_id}")
        assert_test(res_disp.status_code == 200, "Dispatch critical incident for mission telemetry test", details=f"Status: {res_disp.status_code}, Body: {res_disp.text}")
        disp_data = res_disp.json()
        dispatch_id = disp_data.get("dispatch_id") or disp_data.get("id") or (disp_data.get("dispatch") or {}).get("id")

        overview_after_disp = client.get("/api/command-center/overview").json()
        active_missions = overview_after_disp.get("active_missions", [])
        matching_mission = next((m for m in active_missions if m["dispatch_id"] == dispatch_id), None)
        assert_test(matching_mission is not None, "Dispatched mission appears in Command Center active missions list")

        # -------------------------------------------------------------
        # TEST 08: Active Mission Fields & Health Attributes
        # -------------------------------------------------------------
        has_mission_fields = (
            matching_mission is not None and
            "unit_name" in matching_mission and
            "incident_title" in matching_mission and
            "status" in matching_mission and
            "health_status" in matching_mission and
            "route_health" in matching_mission
        )
        assert_test(has_mission_fields, "Active mission contains unit name, title, status, and route health")

        # -------------------------------------------------------------
        # TEST 09: Resource Overview Grouping & Counts
        # -------------------------------------------------------------
        res_groups = overview_after_disp.get("resource_overview", [])
        assert_test(isinstance(res_groups, list) and len(res_groups) > 0, "Resource overview provides unit type grouping")

        # -------------------------------------------------------------
        # TEST 10: Resource Group Count Calculations
        # -------------------------------------------------------------
        first_group = res_groups[0]
        valid_group_counts = (
            "unit_type" in first_group and
            "total" in first_group and
            "available" in first_group and
            "dispatched" in first_group and
            "maintenance" in first_group and
            first_group["total"] == (first_group["available"] + first_group["dispatched"] + first_group["maintenance"])
        )
        assert_test(valid_group_counts, "Resource group availability breakdown equals total units in group")

        # -------------------------------------------------------------
        # TEST 11: Alert Generation for Unassigned Critical Incident
        # -------------------------------------------------------------
        inc_unassigned_raw = client.post("/api/incidents", json={
            "incident_type": "HAZMAT",
            "severity": "CRITICAL",
            "latitude": 12.950000,
            "longitude": 77.580000,
            "location_name": "Chemical Plant",
            "description": "Toxic gas leak.",
        }).json()
        inc_unassigned_crit_id = get_inc_id(inc_unassigned_raw)

        overview_alerts = client.get("/api/command-center/overview").json()
        alerts = overview_alerts.get("alerts", [])
        unassigned_alert = next((a for a in alerts if a["alert_type"] == "UNASSIGNED_CRITICAL" and a["incident_id"] == inc_unassigned_crit_id), None)
        assert_test(unassigned_alert is not None, "Unassigned CRITICAL incident generates UNASSIGNED_CRITICAL alert in central feed")

        # -------------------------------------------------------------
        # TEST 12: Alert Generation for Route Degradation
        # Simulate route degradation on active mission
        # -------------------------------------------------------------
        client.post(
            f"/api/dispatches/{dispatch_id}/simulate-degradation",
            json={"scenario": "BRIDGE_COLLAPSE"}
        )
        overview_degraded = client.get("/api/command-center/overview").json()
        degraded_alerts = overview_degraded.get("alerts", [])
        deg_alert = next((a for a in degraded_alerts if a["alert_type"] in ["ROUTE_DEGRADATION", "ROUTE_CRITICAL", "REROUTE_REQUIRED"] and a["dispatch_id"] == dispatch_id), None)
        assert_test(deg_alert is not None, "Simulated route degradation generates route health alert in central feed")

        # -------------------------------------------------------------
        # TEST 13: Alert Deduplication Verification
        # -------------------------------------------------------------
        # Fetch overview again and check that alert IDs are unique and unique count equals total alerts
        overview_dup_check = client.get("/api/command-center/overview").json()
        all_alert_ids = [a["id"] for a in overview_dup_check.get("alerts", [])]
        is_unique = len(all_alert_ids) == len(set(all_alert_ids))
        assert_test(is_unique, "Alert feed deduplicates items by deterministic alert key")

        # -------------------------------------------------------------
        # TEST 14: Alert Acknowledge via /api Endpoint
        # -------------------------------------------------------------
        target_alert_id = deg_alert["id"] if deg_alert else (alerts[0]["id"] if alerts else "alert-test")
        res_ack = client.post(f"/api/command-center/alerts/{target_alert_id}/acknowledge", json={"operator_id": "OPERATOR_ALICE"})
        assert_test(res_ack.status_code == 200 and res_ack.json().get("success") is True, "POST /api/command-center/alerts/{id}/acknowledge succeeds")

        # -------------------------------------------------------------
        # TEST 15: Acknowledged Alert Persistence in Database
        # -------------------------------------------------------------
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT acknowledged, acknowledged_by FROM command_center_alerts WHERE id = ?;", (target_alert_id,))
        row = cursor.fetchone()
        conn.close()
        assert_test(row is not None and row["acknowledged"] == 1 and row["acknowledged_by"] == "OPERATOR_ALICE", "Acknowledged alert is persisted in SQLite database")

        # -------------------------------------------------------------
        # TEST 16: Alert Acknowledge via /api/v1 Endpoint
        # -------------------------------------------------------------
        if unassigned_alert:
            res_ack_v1 = client.post(f"/api/v1/command-center/alerts/{unassigned_alert['id']}/acknowledge", json={"operator_id": "OPERATOR_BOB"})
            assert_test(res_ack_v1.status_code == 200, "POST /api/v1/command-center/alerts/{id}/acknowledge works under v1 prefix")

        # -------------------------------------------------------------
        # TEST 17: Acknowledged State Reflected in Overview Feed
        # -------------------------------------------------------------
        overview_after_ack = client.get("/api/command-center/overview").json()
        acked_alert = next((a for a in overview_after_ack.get("alerts", []) if a["id"] == target_alert_id), None)
        assert_test(acked_alert is not None and acked_alert["acknowledged"] is True, "Acknowledged alert status is reflected in Command Center overview")

        # -------------------------------------------------------------
        # TEST 18: Map Layers Export Structure
        # -------------------------------------------------------------
        map_layers = overview_after_ack.get("map_layers", {})
        valid_map_layers = (
            "incidents" in map_layers and
            "units" in map_layers and
            "active_routes" in map_layers and
            isinstance(map_layers["incidents"], list) and
            isinstance(map_layers["units"], list)
        )
        assert_test(valid_map_layers, "Map layers output includes incidents, units, and active routes")

        # -------------------------------------------------------------
        # TEST 19: Degraded Route Summary Counter Increments
        # -------------------------------------------------------------
        degraded_count = overview_after_ack["summary"]["degraded_routes"]
        assert_test(degraded_count >= 1, f"Degraded route metric reflects active degraded mission (count={degraded_count})")

        # -------------------------------------------------------------
        # TEST 20: No Unintended Side-Effects on Incidents or Units
        # -------------------------------------------------------------
        inc_check = client.get(f"/api/incidents/{inc_unassigned_crit_id}").json()
        status_val = inc_check.get("status") or (inc_check.get("incident") or {}).get("status")
        assert_test(status_val in ["OPEN", "UNASSIGNED", "REPORTED", "DISPATCHED"], "Fetching overview does not alter underlying incident status", details=f"Status: {status_val}")

        # -------------------------------------------------------------
        # TEST 21: Invalid Alert Acknowledge Error Handling
        # -------------------------------------------------------------
        res_bad_ack = client.post("/api/command-center/alerts/nonexistent-alert-id/acknowledge", json={"operator_id": "TEST"})
        assert_test(res_bad_ack.status_code == 404, "Acknowledging invalid alert ID returns 404 Not Found")

    print(f"\n==================================================")
    print(f"  STAGE 9A COMMAND CENTER TEST RESULTS: {passed_tests}/{total_tests} PASSED")
    print(f"==================================================")


if __name__ == "__main__":
    run_stage_9a_command_center_test()
