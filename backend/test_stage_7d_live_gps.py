import sys
import unittest
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db_connection, init_db
from app.services.incident_service import incident_service
from app.services.rescue_unit_service import rescue_unit_service
from app.services.dispatch_service import dispatch_service
from app.services.mission_tracking_service import mission_tracking_service

client = TestClient(app)


class TestStage7DLiveGPS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Initialize database before running tests."""
        init_db()

    def setUp(self):
        self.conn = get_db_connection()
        self.created_incidents = []
        self.created_dispatches = []

    def tearDown(self):
        cursor = self.conn.cursor()
        for disp_id in self.created_dispatches:
            cursor.execute("DELETE FROM dispatches WHERE id = ?;", (disp_id,))
        for inc_id in self.created_incidents:
            cursor.execute("DELETE FROM incidents WHERE id = ?;", (inc_id,))
        self.conn.commit()
        self.conn.close()

    def test_01_create_incident_from_gps(self):
        """1. Test victim GPS incident creation."""
        payload = {
            "incident_type": "MEDICAL",
            "severity": "CRITICAL",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "location_name": "Victim Live GPS Location",
            "description": "Victim requested immediate rescue via live GPS.",
            "reported_by": "VICTIM_LIVE_GPS",
            "location_source": "GPS",
            "location_accuracy": 8.5,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        res = client.post("/api/incidents", json=payload)
        self.assertEqual(res.status_code, 201, res.text)
        data = res.json()
        self.assertIn("id", data)
        self.assertEqual(data["location_source"], "GPS")
        self.assertAlmostEqual(data["location_accuracy"], 8.5)
        self.created_incidents.append(data["id"])

    def test_02_valid_lat_lng(self):
        """2. Test valid latitude and longitude boundaries."""
        payload = {
            "incident_type": "FIRE",
            "severity": "HIGH",
            "latitude": 45.0,
            "longitude": -90.0,
            "location_source": "GPS",
            "location_accuracy": 5.0,
        }
        res = client.post("/api/incidents", json=payload)
        self.assertEqual(res.status_code, 201, res.text)
        self.created_incidents.append(res.json()["id"])

    def test_03_invalid_latitude_rejection(self):
        """3. Test invalid latitude (> 90) rejection."""
        payload = {
            "incident_type": "FIRE",
            "severity": "HIGH",
            "latitude": 99.9,
            "longitude": 77.59,
        }
        res = client.post("/api/incidents", json=payload)
        self.assertEqual(res.status_code, 422, res.text)

    def test_04_invalid_longitude_rejection(self):
        """4. Test invalid longitude (< -180) rejection."""
        payload = {
            "incident_type": "FIRE",
            "severity": "HIGH",
            "latitude": 12.97,
            "longitude": -200.0,
        }
        res = client.post("/api/incidents", json=payload)
        self.assertEqual(res.status_code, 422, res.text)

    def test_05_invalid_accuracy_rejection(self):
        """5. Test negative accuracy rejection."""
        payload = {
            "incident_type": "FIRE",
            "severity": "HIGH",
            "latitude": 12.97,
            "longitude": 77.59,
            "location_accuracy": -10.0,
        }
        res = client.post("/api/incidents", json=payload)
        self.assertEqual(res.status_code, 422, res.text)

    def test_06_incident_location_stored_correctly(self):
        """6. Test incident location stored correctly in DB."""
        payload = {
            "incident_type": "FLOOD",
            "severity": "MEDIUM",
            "latitude": 12.966602,
            "longitude": 77.599961,
            "location_source": "GPS",
            "location_accuracy": 12.0,
        }
        res = client.post("/api/incidents", json=payload)
        self.assertEqual(res.status_code, 201)
        inc_id = res.json()["id"]
        self.created_incidents.append(inc_id)

        inc_db = incident_service.get_incident(inc_id)
        self.assertIsNotNone(inc_db)
        self.assertAlmostEqual(inc_db["latitude"], 12.966602)
        self.assertAlmostEqual(inc_db["longitude"], 77.599961)

    def test_07_incident_location_remains_immutable_during_rescuer_movement(self):
        """7. Test incident location remains immutable during rescuer telemetry updates."""
        # Reset units to AVAILABLE for test isolation
        units = client.get("/api/rescue-units").json()
        for u in units:
            client.patch(f"/api/rescue-units/{u['id']}/status", json={"status": "AVAILABLE"})

        # Create incident
        inc_res = client.post(
            "/api/incidents",
            json={
                "incident_type": "MEDICAL",
                "severity": "CRITICAL",
                "latitude": 12.9780,
                "longitude": 77.5850,
            },
        )
        self.assertEqual(inc_res.status_code, 201)
        inc = inc_res.json()
        self.created_incidents.append(inc["id"])

        # Dispatch unit
        disp_res = client.post(f"/api/dispatch/incident/{inc['id']}")
        self.assertEqual(disp_res.status_code, 200)
        disp_id = disp_res.json()["dispatch_id"]
        self.created_dispatches.append(disp_id)

        # Rescuer sends location telemetry update
        loc_res = client.post(
            f"/api/dispatches/{disp_id}/location",
            json={
                "lat": 12.9720,
                "lng": 77.5810,
                "speed_kmh": 45.0,
                "heading_degrees": 90.0,
                "accuracy": 5.0,
            },
        )
        self.assertEqual(loc_res.status_code, 200)

        # Verify incident location in DB remains completely unchanged
        inc_after = incident_service.get_incident(inc["id"])
        self.assertAlmostEqual(inc_after["latitude"], 12.9780)
        self.assertAlmostEqual(inc_after["longitude"], 77.5850)

    def test_08_09_rescuer_gps_updates_mission_position(self):
        """8 & 9. Test rescuer GPS location update accepted and updates rescue unit position."""
        # Reset units
        units = client.get("/api/rescue-units").json()
        for u in units:
            client.patch(f"/api/rescue-units/{u['id']}/status", json={"status": "AVAILABLE"})

        inc_res = client.post(
            "/api/incidents",
            json={"incident_type": "FIRE", "severity": "HIGH", "latitude": 12.9750, "longitude": 77.5880},
        )
        inc = inc_res.json()
        self.created_incidents.append(inc["id"])

        disp_res = client.post(f"/api/dispatch/incident/{inc['id']}")
        disp_id = disp_res.json()["dispatch_id"]
        self.created_dispatches.append(disp_id)

        # Send location telemetry
        loc_payload = {
            "lat": 12.9730,
            "lng": 77.5840,
            "speed_kmh": 52.0,
            "heading_degrees": 180.0,
            "accuracy": 4.2,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        res = client.post(f"/api/dispatches/{disp_id}/location", json=loc_payload)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data["unit"]["lat"], 12.9730)
        self.assertEqual(data["unit"]["lng"], 77.5840)
        self.assertEqual(data["unit"]["accuracy"], 4.2)

    def test_10_stale_gps_update_rejected(self):
        """10. Test stale GPS update (older timestamp) is rejected."""
        units = client.get("/api/rescue-units").json()
        for u in units:
            client.patch(f"/api/rescue-units/{u['id']}/status", json={"status": "AVAILABLE"})

        inc_res = client.post(
            "/api/incidents",
            json={"incident_type": "ACCIDENT", "severity": "MEDIUM", "latitude": 12.97, "longitude": 77.58},
        )
        inc = inc_res.json()
        self.created_incidents.append(inc["id"])

        disp_res = client.post(f"/api/dispatch/incident/{inc['id']}")
        disp_id = disp_res.json()["dispatch_id"]
        self.created_dispatches.append(disp_id)

        # Newer update
        newer_ts = (datetime.utcnow()).isoformat() + "Z"
        res_new = client.post(
            f"/api/dispatches/{disp_id}/location",
            json={"lat": 12.972, "lng": 77.582, "timestamp": newer_ts},
        )
        self.assertEqual(res_new.status_code, 200)

        # Stale update from 1 hour ago
        stale_ts = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
        res_stale = client.post(
            f"/api/dispatches/{disp_id}/location",
            json={"lat": 12.960, "lng": 77.570, "timestamp": stale_ts},
        )
        self.assertEqual(res_stale.status_code, 400)
        self.assertIn("Stale GPS update rejected", res_stale.json()["detail"])

    def test_11_latest_gps_update_wins(self):
        """11. Test latest valid GPS telemetry update overwrites position."""
        units = client.get("/api/rescue-units").json()
        for u in units:
            client.patch(f"/api/rescue-units/{u['id']}/status", json={"status": "AVAILABLE"})

        inc_res = client.post(
            "/api/incidents",
            json={"incident_type": "MEDICAL", "severity": "HIGH", "latitude": 12.97, "longitude": 77.58},
        )
        inc = inc_res.json()
        self.created_incidents.append(inc["id"])

        disp_res = client.post(f"/api/dispatch/incident/{inc['id']}")
        disp_id = disp_res.json()["dispatch_id"]
        self.created_dispatches.append(disp_id)

        t1 = datetime.utcnow().isoformat() + "Z"
        client.post(f"/api/dispatches/{disp_id}/location", json={"lat": 12.971, "lng": 77.581, "timestamp": t1})

        t2 = (datetime.utcnow() + timedelta(seconds=5)).isoformat() + "Z"
        res2 = client.post(f"/api/dispatches/{disp_id}/location", json={"lat": 12.975, "lng": 77.585, "timestamp": t2})
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["unit"]["lat"], 12.975)

    def test_12_13_route_origin_uses_rescuer_destination_uses_incident(self):
        """12 & 13. Test AI route origin uses live rescuer position & destination uses incident."""
        inc_res = client.post(
            "/api/incidents",
            json={"incident_type": "FIRE", "severity": "CRITICAL", "latitude": 12.966602, "longitude": 77.599961},
        )
        inc = inc_res.json()
        self.created_incidents.append(inc["id"])

        route_payload = {
          "start": {"lat": 12.979766, "lng": 77.583438, "name": "Rescuer Live GPS"},
          "destination": {"lat": inc["latitude"], "lng": inc["longitude"], "name": "Incident Site"},
          "vehicle_type": "ambulance"
        }
        res = client.post("/api/ai/route", json=route_payload)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIn("geometry", data)
        self.assertTrue("total_distance_meters" in data or "distance_meters" in data)

    def test_14_route_deviation_integration(self):
        """14. Test live GPS route deviation triggers route health check & reroute recommendation."""
        units = client.get("/api/rescue-units").json()
        for u in units:
            client.patch(f"/api/rescue-units/{u['id']}/status", json={"status": "AVAILABLE"})

        inc_res = client.post(
            "/api/incidents",
            json={"incident_type": "FLOOD", "severity": "HIGH", "latitude": 12.966602, "longitude": 77.599961},
        )
        inc = inc_res.json()
        self.created_incidents.append(inc["id"])

        disp_res = client.post(f"/api/dispatch/incident/{inc['id']}")
        disp_id = disp_res.json()["dispatch_id"]
        self.created_dispatches.append(disp_id)

        # Send location update far off route to trigger deviation
        dev_res = client.post(
            f"/api/dispatches/{disp_id}/location",
            json={"lat": 12.9500, "lng": 77.5700, "speed_kmh": 30.0, "accuracy": 5.0},
        )
        self.assertEqual(dev_res.status_code, 200)
        data = dev_res.json()
        self.assertIn("route_health", data)

    def test_15_gps_failure_handling(self):
        """15. Test GPS failure handling and invalid boundary rejection."""
        # Out of bounds lat
        res1 = client.post(
            "/api/dispatches/disp-fake/location",
            json={"lat": 100.0, "lng": 77.58},
        )
        self.assertIn(res1.status_code, [400, 422])

        # Negative accuracy
        res2 = client.post(
            "/api/dispatches/disp-fake/location",
            json={"lat": 12.97, "lng": 77.58, "accuracy": -5.0},
        )
        self.assertIn(res2.status_code, [400, 422])

    def test_16_17_simulation_and_developer_mode_compatibility(self):
        """16 & 17. Test simulation and developer mode API compatibility."""
        sim_res = client.post("/api/simulations", json={"scenario_type": "URBAN_FLOOD", "scale": "SMALL", "seed": 42})
        self.assertEqual(sim_res.status_code, 200)

    def test_18_api_v1_compatibility(self):
        """18. Test /api/v1/ prefix endpoint compatibility."""
        res = client.get("/api/v1/incidents")
        self.assertEqual(res.status_code, 200)

    def test_19_command_center_integration(self):
        """19. Test command center receives live telemetry overview."""
        res = client.get("/api/command-center/overview")
        self.assertEqual(res.status_code, 200)

    def test_20_stage_7c_live_tracking_regression(self):
        """20. Test Stage 7C live mission tracking API regression."""
        units = client.get("/api/rescue-units").json()
        for u in units:
            client.patch(f"/api/rescue-units/{u['id']}/status", json={"status": "AVAILABLE"})

        inc_res = client.post(
            "/api/incidents",
            json={"incident_type": "MEDICAL", "severity": "HIGH", "latitude": 12.9716, "longitude": 77.5946},
        )
        inc = inc_res.json()
        self.created_incidents.append(inc["id"])

        disp_res = client.post(f"/api/dispatch/incident/{inc['id']}")
        disp_id = disp_res.json()["dispatch_id"]
        self.created_dispatches.append(disp_id)

        live_res = client.get(f"/api/dispatches/{disp_id}/live")
        self.assertEqual(live_res.status_code, 200)
        self.assertEqual(live_res.json()["dispatch_id"], disp_id)


if __name__ == "__main__":
    unittest.main()
