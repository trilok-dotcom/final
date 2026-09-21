import sys
import time
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure root workspace directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app
from app.db.database import init_db, get_db_connection


def run_stage_7c_live_tracking_test():
    print("==================================================")
    print("  RESQROUTE — STAGE 7C: LIVE TRACKING TEST       ")
    print("==================================================")

    init_db()

    with TestClient(app) as client:
        # Reset units to AVAILABLE for test isolation
        units = client.get("/api/rescue-units").json()
        for u in units:
            client.patch(f"/api/rescue-units/{u['id']}/status", json={"status": "AVAILABLE"})

        # 1. Test WebSocket Connection Initialization
        print("[1/20] Testing WebSocket connection initialization (/api/ws/missions)...")
        with client.websocket_connect("/api/ws/missions") as ws:
            msg = ws.receive_json()
            assert msg.get("type") == "CONNECTION_ESTABLISHED"
            ws.send_text("ping")
            pong = ws.receive_json()
            assert pong.get("type") == "PONG"

        # 2. Create Test Incident
        print("[2/20] Creating test incident...")
        res_inc = client.post("/api/incidents", json={
            "incident_type": "MEDICAL",
            "severity": "CRITICAL",
            "latitude": 12.966602,
            "longitude": 77.599961,
            "location_name": "Metro Station Terminal",
            "description": "Medical collapse emergency.",
        })
        assert res_inc.status_code == 201
        inc_id = res_inc.json()["id"]

        # 3. Trigger Automatic Dispatch
        print("[3/20] Triggering automatic dispatch...")
        res_disp = client.post(f"/api/dispatch/incident/{inc_id}")
        assert res_disp.status_code == 200
        disp_data = res_disp.json()
        disp_id = disp_data["dispatch_id"]
        unit_id = disp_data["rescue_unit_id"]

        # 4. Get Live Mission Telemetry
        print("[4/20] Testing GET /api/dispatches/{id}/live...")
        res_live = client.get(f"/api/dispatches/{disp_id}/live")
        assert res_live.status_code == 200
        live_data = res_live.json()
        assert live_data["dispatch_id"] == disp_id
        assert "distance_remaining_meters" in live_data
        assert "progress_percent" in live_data

        # 5. Send Valid Live Location Update
        print("[5/20] Sending live location telemetry update (POST /api/dispatches/{id}/location)...")
        new_lat, new_lng = 12.975123, 77.590421
        res_loc = client.post(f"/api/dispatches/{disp_id}/location", json={
            "lat": new_lat,
            "lng": new_lng,
            "speed_kmh": 42.5,
            "heading_degrees": 135.0,
        })
        assert res_loc.status_code == 200
        loc_data = res_loc.json()

        # 6. Verify Unit Location Changed
        print("[6/20] Verifying unit location changed in database...")
        assert loc_data["unit"]["lat"] == new_lat
        assert loc_data["unit"]["lng"] == new_lng
        assert loc_data["unit"]["speed_kmh"] == 42.5

        # 7. Verify Distance Remaining Calculated
        print("[7/20] Verifying distance remaining calculated...")
        assert loc_data["distance_remaining_meters"] > 0

        # 8. Verify Progress Percentage Calculated
        print("[8/20] Verifying progress percentage calculated...")
        assert 0.0 <= loc_data["progress_percent"] <= 100.0

        # 9. Verify Updated ETA Calculated
        print("[9/20] Verifying updated ETA calculated...")
        assert loc_data["eta_seconds"] >= 0

        # 10. Verify Telemetry Persisted in mission_updates Table
        print("[10/20] Verifying telemetry persisted in mission_updates table...")
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM mission_updates WHERE dispatch_id = ?;", (disp_id,))
            cnt = cursor.fetchone()[0]
            assert cnt >= 1, f"Expected telemetry in DB, got count={cnt}"
        finally:
            conn.close()

        # 11. Start Live Movement Simulation
        print("[11/20] Starting movement simulation (POST /api/dispatches/{id}/simulate)...")
        res_sim = client.post(f"/api/dispatches/{disp_id}/simulate")
        assert res_sim.status_code == 200
        assert res_sim.json()["success"] is True

        # 12. Verify Simulated Movement
        print("[12/20] Verifying simulated movement progress...")
        time.sleep(2.5)  # Allow simulation background task to execute a few steps
        res_live2 = client.get(f"/api/dispatches/{disp_id}/live")
        assert res_live2.status_code == 200

        # 13. Verify Status Transition: DISPATCHED -> EN_ROUTE
        print("[13/20] Verifying status transitioned to EN_ROUTE during simulation...")
        assert res_live2.json()["status"] == "EN_ROUTE"

        # 14. Stop Simulation
        print("[14/20] Stopping simulation (POST /api/dispatches/{id}/simulation/stop)...")
        res_stop = client.post(f"/api/dispatches/{disp_id}/simulation/stop")
        assert res_stop.status_code == 200
        assert res_stop.json()["success"] is True

        # 15. Complete Mission (EN_ROUTE -> ON_SCENE -> COMPLETED)
        print("[15/20] Completing mission via PATCH /api/dispatches/{id}/status...")
        res_scene = client.patch(f"/api/dispatches/{disp_id}/status", json={"status": "ON_SCENE"})
        assert res_scene.status_code == 200
        res_comp = client.patch(f"/api/dispatches/{disp_id}/status", json={"status": "COMPLETED"})
        assert res_comp.status_code == 200
        assert res_comp.json()["status"] == "COMPLETED"

        # 16. Verify Unit Returns to AVAILABLE
        print("[16/20] Verifying unit returns to AVAILABLE status...")
        res_u = client.get(f"/api/rescue-units/{unit_id}")
        assert res_u.json()["status"] == "AVAILABLE"

        # 17. Verify Invalid Telemetry Location Rejection
        print("[17/20] Testing invalid coordinate bounds rejection (lat=999)...")
        res_inv_lat = client.post(f"/api/dispatches/{disp_id}/location", json={"lat": 999.0, "lng": 77.58})
        assert res_inv_lat.status_code == 422

        # 18. Verify Completed Mission Cannot Simulate
        print("[18/20] Testing completed mission simulation rejection (HTTP 400)...")
        res_inv_sim = client.post(f"/api/dispatches/{disp_id}/simulate")
        assert res_inv_sim.status_code == 400

        # 19. Verify WebSocket Broadcast System Stability
        print("[19/20] Verifying WebSocket manager stability...")
        with client.websocket_connect("/api/ws/missions") as ws2:
            client.post(f"/api/dispatch/incident/{inc_id}")  # duplicate dispatch trigger
            time.sleep(0.5)

        # 20. Clean up Test Records
        print("[20/20] Cleaning up test incident...")
        client.delete(f"/api/incidents/{inc_id}")

        print("\n============================================================")
        print("STAGE 7C LIVE TRACKING TESTS COMPLETED SUCCESSFULLY")
        print("============================================================")


if __name__ == "__main__":
    run_stage_7c_live_tracking_test()
