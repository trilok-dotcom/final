import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure root workspace directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app
from app.db.database import init_db


def run_stage_7a_tests():
    print("==================================================")
    print("  RESQROUTE — STAGE 7A: INCIDENTS & UNITS TEST   ")
    print("==================================================")

    init_db()

    with TestClient(app) as client:
        # 1. Create Incident
        print("[1/17] Testing Incident Creation (POST /api/incidents)...")
        new_inc_payload = {
            "incident_type": "FIRE",
            "severity": "CRITICAL",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "location_name": "MG Road Commercial Complex",
            "description": "Large building fire reported on 3rd floor.",
        }
        res = client.post("/api/incidents", json=new_inc_payload)
        assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
        inc_data = res.json()
        assert "id" in inc_data and inc_data["id"].startswith("inc-")
        assert inc_data["incident_type"] == "FIRE"
        assert inc_data["severity"] == "CRITICAL"
        assert inc_data["status"] == "REPORTED"
        inc_id = inc_data["id"]
        print(f"       Created incident: {inc_data['incident_code']} ({inc_id})")

        # 2. Retrieve Incident
        print("[2/17] Testing Get Incident (GET /api/incidents/{id})...")
        res_get = client.get(f"/api/incidents/{inc_id}")
        assert res_get.status_code == 200, f"Expected 200, got {res_get.status_code}"
        assert res_get.json()["id"] == inc_id

        # 3. List Incidents
        print("[3/17] Testing List Incidents (GET /api/incidents)...")
        res_list = client.get("/api/incidents")
        assert res_list.status_code == 200
        incidents = res_list.json()
        assert len(incidents) >= 1

        # 4. Update Incident
        print("[4/17] Testing Update Incident (PATCH /api/incidents/{id})...")
        res_patch = client.patch(f"/api/incidents/{inc_id}", json={"status": "ACTIVE", "description": "Fire crew arriving on scene."})
        assert res_patch.status_code == 200
        assert res_patch.json()["status"] == "ACTIVE"

        # 5. Resolve Incident
        print("[5/17] Testing Resolve Incident (POST /api/incidents/{id}/resolve)...")
        res_resolve = client.post(f"/api/incidents/{inc_id}/resolve")
        assert res_resolve.status_code == 200
        assert res_resolve.json()["status"] == "RESOLVED"
        assert res_resolve.json()["resolved_at"] is not None

        # 6. Create Rescue Unit
        print("[6/17] Testing Rescue Unit Creation (POST /api/rescue-units)...")
        unit_code = "AMB-99"
        new_unit_payload = {
            "unit_code": unit_code,
            "unit_type": "AMBULANCE",
            "status": "AVAILABLE",
            "latitude": 12.9698,
            "longitude": 77.5901,
            "name": "Central Ambulance 99",
            "crew_size": 3,
            "capabilities": ["medical", "first_aid", "patient_transport"],
        }
        res_unit = client.post("/api/rescue-units", json=new_unit_payload)
        assert res_unit.status_code == 201, f"Expected 201, got {res_unit.status_code}: {res_unit.text}"
        unit_data = res_unit.json()
        assert unit_data["unit_code"] == "AMB-99"
        unit_id = unit_data["id"]
        print(f"       Created rescue unit: {unit_code} ({unit_id})")

        # 7. Retrieve Rescue Unit
        print("[7/17] Testing Get Rescue Unit (GET /api/rescue-units/{id})...")
        res_u_get = client.get(f"/api/rescue-units/{unit_id}")
        assert res_u_get.status_code == 200
        assert res_u_get.json()["id"] == unit_id

        # 8. List Rescue Units
        print("[8/17] Testing List Rescue Units (GET /api/rescue-units)...")
        res_u_list = client.get("/api/rescue-units")
        assert res_u_list.status_code == 200
        units = res_u_list.json()
        assert len(units) >= 1

        # 9. Update Rescue Unit Status
        print("[9/17] Testing Update Status (PATCH /api/rescue-units/{id}/status)...")
        res_u_status = client.patch(f"/api/rescue-units/{unit_id}/status", json={"status": "EN_ROUTE"})
        assert res_u_status.status_code == 200
        assert res_u_status.json()["status"] == "EN_ROUTE"

        # 10. Filter Incidents by Status
        print("[10/17] Testing Filtering Incidents (?status=RESOLVED)...")
        res_f_inc = client.get("/api/incidents?status=RESOLVED")
        assert res_f_inc.status_code == 200
        for item in res_f_inc.json():
            assert item["status"] == "RESOLVED"

        # 11. Filter Rescue Units by Type
        print("[11/17] Testing Filtering Rescue Units (?unit_type=AMBULANCE)...")
        res_f_unit = client.get("/api/rescue-units?unit_type=AMBULANCE")
        assert res_f_unit.status_code == 200
        for item in res_f_unit.json():
            assert item["unit_type"] == "AMBULANCE"

        # 12. Invalid Incident Type Validation
        print("[12/17] Testing Invalid Incident Type Validation...")
        bad_type_res = client.post("/api/incidents", json={"incident_type": "INVALID_TYPE", "severity": "HIGH", "latitude": 12.9, "longitude": 77.5})
        assert bad_type_res.status_code in [400, 422], f"Expected 400/422, got {bad_type_res.status_code}"

        # 13. Invalid Severity Validation
        print("[13/17] Testing Invalid Severity Validation...")
        bad_sev_res = client.post("/api/incidents", json={"incident_type": "FIRE", "severity": "EXTREME", "latitude": 12.9, "longitude": 77.5})
        assert bad_sev_res.status_code in [400, 422]

        # 14. Invalid Status Validation
        print("[14/17] Testing Invalid Unit Status Validation...")
        bad_status_res = client.patch(f"/api/rescue-units/{unit_id}/status", json={"status": "INVALID_STATUS"})
        assert bad_status_res.status_code in [400, 422]

        # 15. Invalid Latitude/Longitude Range Validation
        print("[15/17] Testing Invalid Coordinate Range Validation...")
        bad_lat_res = client.post("/api/incidents", json={"incident_type": "FIRE", "severity": "HIGH", "latitude": 120.0, "longitude": 77.5})
        assert bad_lat_res.status_code in [400, 422]

        # 16. Duplicate Unit Code Rejection
        print("[16/17] Testing Duplicate Unit Code Rejection (HTTP 409)...")
        dup_unit_res = client.post("/api/rescue-units", json=new_unit_payload)
        assert dup_unit_res.status_code == 409, f"Expected 409 Conflict, got {dup_unit_res.status_code}"

        # 17. Cleanup Test Unit
        print("[17/17] Cleaning up test records...")
        del_u_res = client.delete(f"/api/rescue-units/{unit_id}")
        assert del_u_res.status_code == 24 or del_u_res.status_code == 204

        print("\n============================================================")
        print("STAGE 7A TESTS COMPLETED SUCCESSFULLY")
        print("============================================================")


if __name__ == "__main__":
    run_stage_7a_tests()
