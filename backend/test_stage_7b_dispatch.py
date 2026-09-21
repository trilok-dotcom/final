import sys
import math
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure root workspace directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app
from app.db.database import init_db


def run_stage_7b_dispatch_test():
    print("==================================================")
    print("  RESQROUTE — STAGE 7B: AUTOMATIC DISPATCH TEST  ")
    print("==================================================")

    init_db()

    with TestClient(app) as client:
        # Reset units to AVAILABLE for test isolation
        units = client.get("/api/rescue-units").json()
        for u in units:
            client.patch(f"/api/rescue-units/{u['id']}/status", json={"status": "AVAILABLE"})

        # 1. Prepare Test Incident inside AI georeferenced bounds
        print("[1/17] Creating test incident for dispatch...")
        inc_payload = {
            "incident_type": "FIRE",
            "severity": "CRITICAL",
            "latitude": 12.966602,
            "longitude": 77.599961,
            "location_name": "Sector 4 Command Area Fire",
            "description": "Commercial fire requiring rapid automatic unit dispatch.",
        }
        res_inc = client.post("/api/incidents", json=inc_payload)
        assert res_inc.status_code == 201
        inc_data = res_inc.json()
        inc_id = inc_data["id"]
        inc_code = inc_data["incident_code"]
        print(f"       Incident created: {inc_code} ({inc_id})")

        # 2. Trigger Automatic Dispatch
        print("[2/17] Triggering automatic dispatch via POST /api/dispatch/incident/{id}...")
        res_disp = client.post(f"/api/dispatch/incident/{inc_id}")
        assert res_disp.status_code == 200, f"Expected 200 OK, got {res_disp.status_code}: {res_disp.text}"
        disp_data = res_disp.json()
        assert disp_data.get("success") is True
        disp_id = disp_data["dispatch_id"]
        unit_id = disp_data["rescue_unit_id"]
        unit_code = disp_data["rescue_unit_code"]
        print(f"       Dispatch created: {disp_id} (Assigned Unit: {unit_code})")

        # 3. Verify Rescue Unit status changed to DISPATCHED
        print("[3/17] Verifying rescue unit status changed to DISPATCHED...")
        res_u = client.get(f"/api/rescue-units/{unit_id}")
        assert res_u.status_code == 200
        assert res_u.json()["status"] == "DISPATCHED"
        assert res_u.json()["current_incident_id"] == inc_id

        # 4. Verify Dispatch record exists
        print("[4/17] Verifying dispatch record exists via GET /api/dispatches/{id}...")
        res_d_get = client.get(f"/api/dispatches/{disp_id}")
        assert res_d_get.status_code == 200
        assert res_d_get.json()["id"] == disp_id
        assert res_d_get.json()["status"] == "DISPATCHED"

        # 5. Verify Internal AI Route Metrics
        print("[5/17] Verifying calculated internal AI route distance & duration...")
        route = disp_data.get("route", {})
        assert "route_id" in route
        assert route.get("distance_meters", 0) > 0, "Distance should be > 0"
        assert route.get("estimated_duration_seconds", 0) > 0, "ETA should be > 0"
        assert 0.0 <= route.get("average_confidence", -1) <= 1.0, "Average confidence invalid"

        # 6. Verify Route Geometry
        print("[6/17] Verifying GeoJSON route geometry LineString...")
        geom = route.get("geometry", {})
        assert geom.get("type") == "LineString"
        coords = geom.get("coordinates", [])
        assert len(coords) >= 2, f"Expected at least 2 route coordinates, got {len(coords)}"

        # 7. Test Duplicate Dispatch Rejection
        print("[7/17] Testing duplicate dispatch rejection for same incident...")
        res_dup = client.post(f"/api/dispatch/incident/{inc_id}")
        assert res_dup.status_code == 400
        assert res_dup.json()["detail"]["status"] == "ALREADY_DISPATCHED"

        # 8. Test Status Progression: DISPATCHED -> EN_ROUTE
        print("[8/17] Testing status transition: DISPATCHED -> EN_ROUTE...")
        res_st1 = client.patch(f"/api/dispatches/{disp_id}/status", json={"status": "EN_ROUTE"})
        assert res_st1.status_code == 200
        assert res_st1.json()["status"] == "EN_ROUTE"

        # Verify unit status updated to EN_ROUTE
        res_u_en = client.get(f"/api/rescue-units/{unit_id}")
        assert res_u_en.json()["status"] == "EN_ROUTE"

        # 9. Test Status Progression: EN_ROUTE -> ON_SCENE
        print("[9/17] Testing status transition: EN_ROUTE -> ON_SCENE...")
        res_st2 = client.patch(f"/api/dispatches/{disp_id}/status", json={"status": "ON_SCENE"})
        assert res_st2.status_code == 200
        assert res_st2.json()["status"] == "ON_SCENE"

        # Verify unit status updated to ON_SCENE
        res_u_scene = client.get(f"/api/rescue-units/{unit_id}")
        assert res_u_scene.json()["status"] == "ON_SCENE"

        # 10. Test Status Progression: ON_SCENE -> COMPLETED
        print("[10/17] Testing status transition: ON_SCENE -> COMPLETED...")
        res_st3 = client.patch(f"/api/dispatches/{disp_id}/status", json={"status": "COMPLETED"})
        assert res_st3.status_code == 200
        assert res_st3.json()["status"] == "COMPLETED"

        # 11. Verify Unit becomes AVAILABLE after COMPLETED
        print("[11/17] Verifying rescue unit status returned to AVAILABLE...")
        res_u_avail = client.get(f"/api/rescue-units/{unit_id}")
        assert res_u_avail.json()["status"] == "AVAILABLE"
        assert res_u_avail.json()["current_incident_id"] is None

        # 12. Verify Incident becomes RESOLVED after COMPLETED
        print("[12/17] Verifying incident status updated to RESOLVED...")
        res_inc_res = client.get(f"/api/incidents/{inc_id}")
        assert res_inc_res.json()["status"] == "RESOLVED"
        assert res_inc_res.json()["resolved_at"] is not None

        # 13. Test Invalid Status Transition Rejection
        print("[13/17] Testing invalid status transition rejection (COMPLETED -> EN_ROUTE)...")
        res_inv = client.patch(f"/api/dispatches/{disp_id}/status", json={"status": "EN_ROUTE"})
        assert res_inv.status_code == 400
        assert res_inv.json()["detail"]["status"] == "INVALID_TRANSITION"

        # 14. Test No Available Unit Handling
        print("[14/17] Testing no available unit error handling...")
        # Mark all rescue units OFFLINE temporarily
        all_units = client.get("/api/rescue-units").json()
        for u in all_units:
            client.patch(f"/api/rescue-units/{u['id']}/status", json={"status": "OFFLINE"})

        # Create new incident & attempt dispatch
        inc2_res = client.post("/api/incidents", json={"incident_type": "MEDICAL", "severity": "HIGH", "latitude": 12.97, "longitude": 77.58})
        inc2_id = inc2_res.json()["id"]

        no_unit_res = client.post(f"/api/dispatch/incident/{inc2_id}")
        assert no_unit_res.status_code == 400
        assert no_unit_res.json()["detail"]["status"] == "NO_AVAILABLE_UNIT"

        # 15. Restore rescue units back to AVAILABLE
        print("[15/17] Restoring rescue units status...")
        for u in all_units:
            client.patch(f"/api/rescue-units/{u['id']}/status", json={"status": "AVAILABLE"})

        # 16. Verify listing all dispatches
        print("[16/17] Testing GET /api/dispatches...")
        res_all_disp = client.get("/api/dispatches")
        assert res_all_disp.status_code == 200
        assert len(res_all_disp.json()) >= 1

        # 17. Cleanup test records
        print("[17/17] Cleaning up test incidents...")
        client.delete(f"/api/incidents/{inc_id}")
        client.delete(f"/api/incidents/{inc2_id}")

        print("\n============================================================")
        print("STAGE 7B AUTOMATIC DISPATCH TESTS COMPLETED SUCCESSFULLY")
        print("============================================================")


if __name__ == "__main__":
    run_stage_7b_dispatch_test()
