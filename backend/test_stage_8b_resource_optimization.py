import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure root workspace directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app
from app.db.database import init_db, get_db_connection


def run_stage_8b_resource_optimization_test():
    print("==================================================")
    print("  RESQROUTE — STAGE 8B: RESOURCE OPTIMIZATION TEST")
    print("==================================================")

    init_db()

    with TestClient(app) as client:
        # Reset units to AVAILABLE for clean test isolation
        units = client.get("/api/rescue-units").json()
        for u in units:
            client.patch(f"/api/rescue-units/{u['id']}/status", json={"status": "AVAILABLE"})

        # 1. Create Test Collapsed Building Incident (Requires 2x RESCUE_TEAM, 2x AMBULANCE)
        print("[1/18] Creating Collapsed Building CRITICAL test incident...")
        res_inc = client.post("/api/incidents", json={
            "incident_type": "COLLAPSED_BUILDING",
            "severity": "CRITICAL",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "location_name": "Metro Structural Failure",
            "description": "Building structural collapse requiring multi-unit response.",
        })
        assert res_inc.status_code == 201
        inc_id = res_inc.json()["id"]
        inc_code = res_inc.json()["incident_code"]

        # 2. Trigger AI Resource Optimization
        print(f"[2/18] Optimizing resources via POST /api/incidents/{inc_id}/optimize-resources...")
        res_opt = client.post(f"/api/incidents/{inc_id}/optimize-resources")
        assert res_opt.status_code == 200, f"Expected 200 OK, got {res_opt.status_code}: {res_opt.text}"
        opt_data = res_opt.json()

        # 3. Verify Stage 8A recommendations consumed correctly
        print("[3/18] Verifying Stage 8A recommendations consumed correctly...")
        req_res = opt_data["required_resources"]
        assert len(req_res) >= 2
        print(f"       Required Resources: {req_res}")

        # 4. Verify Candidate Discovery
        print("[4/18] Verifying candidate units discovery...")
        cands = opt_data["candidate_units"]
        assert len(cands) > 0

        # 5. Verify In-Process AI Routing & Haversine Distance
        print("[5/18] Verifying route-aware distance and duration metrics...")
        for c in cands:
            assert c["distance_meters"] > 0
            assert c["estimated_duration_seconds"] > 0
            assert 0.0 <= c["average_confidence"] <= 1.0

        # 6. Verify 6-Factor Optimization Score Calculation
        print("[6/18] Verifying candidate 6-factor optimization scores...")
        for c in cands:
            assert 0.0 <= c["optimization_score"] <= 100.0
            fb = c["factor_breakdown"]
            assert "eta_score" in fb
            assert "route_safety_score" in fb

        # 7. Verify Candidate Ranking & Selection
        print("[7/18] Verifying candidate ranking and top unit selection...")
        sels = opt_data["selected_units"]
        assert len(sels) > 0
        for s in sels:
            assert s["optimization_score"] >= 40.0
            assert "selection_reason" in s

        # 8. Verify No Duplicate Units Selected
        print("[8/18] Verifying no duplicate unit selections...")
        selected_ids = [s["rescue_unit_id"] for s in sels]
        assert len(selected_ids) == len(set(selected_ids))

        # 9. Verify Resource Reservation in Database
        print("[9/18] Verifying selected units reserved in database...")
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            for u_id in selected_ids:
                cursor.execute("SELECT status, current_incident_id FROM rescue_units WHERE id = ?;", (u_id,))
                row = cursor.fetchone()
                assert row[0] == "RESERVED"
                assert row[1] == inc_id
        finally:
            conn.close()

        # 10. Dispatch Operator-Confirmed Multi-Unit Plan
        print(f"[10/18] Dispatching optimized plan via POST /api/incidents/{inc_id}/dispatch-optimized...")
        res_disp = client.post(f"/api/incidents/{inc_id}/dispatch-optimized")
        assert res_disp.status_code == 200, f"Expected 200 OK, got {res_disp.status_code}: {res_disp.text}"
        disp_res_data = res_disp.json()

        # 11. Verify Multiple Dispatch Records Created
        print("[11/18] Verifying multiple dispatch records created...")
        disp_ids = disp_res_data["dispatch_ids"]
        assert len(disp_ids) == len(selected_ids)

        # 12. Verify Units Status Transitioned to DISPATCHED
        print("[12/18] Verifying rescue units transitioned to DISPATCHED status...")
        for u_id in selected_ids:
            u_info = client.get(f"/api/rescue-units/{u_id}").json()
            assert u_info["status"] in ("DISPATCHED", "EN_ROUTE")

        # 13. Verify Already-Dispatched Incident Optimization Protection
        print("[13/18] Testing optimization protection on already-dispatched incident...")
        res_reopt = client.post(f"/api/incidents/{inc_id}/optimize-resources")
        assert res_reopt.status_code == 200
        assert res_reopt.json()["resource_status"] == "ALREADY_DISPATCHED"

        # 14. Create Second Incident to Test Conflict & Insufficient Resources
        print("[14/18] Testing resource shortage handling on concurrent incident...")
        res_inc2 = client.post("/api/incidents", json={
            "incident_type": "FIRE",
            "severity": "HIGH",
            "latitude": 12.978,
            "longitude": 77.585,
            "location_name": "Sector 4 Secondary Fire",
        })
        inc2_id = res_inc2.json()["id"]
        res_opt2 = client.post(f"/api/incidents/{inc2_id}/optimize-resources")
        assert res_opt2.status_code == 200
        assert "resource_status" in res_opt2.json()

        # 15. Test Stale Dispatch Rejection
        print("[15/18] Testing invalid dispatch request when no reservation exists...")
        res_inv = client.post("/api/incidents/non_existent_inc_99/dispatch-optimized")
        assert res_inv.status_code == 404

        # 16. Complete First Mission Dispatches
        print("[16/18] Completing dispatches to release units...")
        for d_id in disp_ids:
            client.patch(f"/api/dispatches/{d_id}/status", json={"status": "EN_ROUTE"})
            client.patch(f"/api/dispatches/{d_id}/status", json={"status": "ON_SCENE"})
            client.patch(f"/api/dispatches/{d_id}/status", json={"status": "COMPLETED"})

        # 17. Verify Units Released Back to AVAILABLE
        print("[17/18] Verifying units released back to AVAILABLE status...")
        for u_id in selected_ids:
            u_info = client.get(f"/api/rescue-units/{u_id}").json()
            assert u_info["status"] == "AVAILABLE"

        # 18. Clean up Test Incidents
        print("[18/18] Cleaning up test records...")
        client.delete(f"/api/incidents/{inc_id}")
        client.delete(f"/api/incidents/{inc2_id}")

        print("\n============================================================")
        print("STAGE 8B RESOURCE OPTIMIZATION TESTS COMPLETED SUCCESSFULLY")
        print("============================================================")


if __name__ == "__main__":
    run_stage_8b_resource_optimization_test()
