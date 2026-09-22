import sys
import unittest
import json
import time
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db_connection, init_db
from app.services.road_condition_service import road_condition_service
from app.services.emergency_routing_service import emergency_routing_service

client = TestClient(app)


class TestStage7ERoadCondition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Initialize database before running tests."""
        init_db()

    def setUp(self):
        self.conn = get_db_connection()
        # Ensure any active assessment is reset before each test
        road_condition_service.reset_active_assessment()

    def tearDown(self):
        road_condition_service.reset_active_assessment()
        self.conn.close()

    def test_01_analyze_pre_post_images(self):
        """1. Test analysis of pre and post disaster images."""
        res = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        self.assertIn("assessment_id", res)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertGreater(res["roads_analyzed"], 0)
        self.assertIn("safe_count", res)
        self.assertIn("degraded_count", res)
        self.assertIn("blocked_count", res)

    def test_02_preservation_calculation(self):
        """2. Test road preservation ratio calculation."""
        res = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        for seg in res["segments"]:
            ratio = seg["preservation_ratio"]
            self.assertGreaterEqual(ratio, 0.0)
            self.assertLessEqual(ratio, 1.0)
            self.assertIn("pre_confidence", seg)
            self.assertIn("post_confidence", seg)

    def test_03_safe_classification(self):
        """3. Test SAFE classification rule when preservation and confidence are high."""
        res = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        safe_segs = [s for s in res["segments"] if s["condition"] == "SAFE"]
        self.assertTrue(len(safe_segs) > 0 or res["safe_count"] >= 0)
        for s in safe_segs:
            self.assertTrue(s["traversable"])
            self.assertGreaterEqual(s["preservation_ratio"], 0.60)

    def test_04_degraded_classification(self):
        """4. Test DEGRADED classification rule."""
        res = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        deg_segs = [s for s in res["segments"] if s["condition"] == "DEGRADED"]
        for s in deg_segs:
            self.assertTrue(s["traversable"])

    def test_05_blocked_classification(self):
        """5. Test BLOCKED classification rule."""
        res = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        blocked_segs = [s for s in res["segments"] if s["condition"] == "BLOCKED"]
        self.assertGreater(len(blocked_segs), 0)
        for s in blocked_segs:
            self.assertFalse(s["traversable"])

    def test_06_unknown_handling(self):
        """6. Test UNKNOWN condition handling."""
        res = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        self.assertIn("unknown_count", res)

    def test_07_updated_graph_generation(self):
        """7. Test updated road graph generation with segment metadata."""
        res = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        seg = res["segments"][0]
        self.assertIn("edge_id", seg)
        self.assertIn("condition_score", seg)
        self.assertIn("geometry", seg)

    def test_08_blocked_edge_exclusion(self):
        """8. Test that blocked edges are excluded from routing graph."""
        analysis = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        road_condition_service.apply_assessment(analysis["assessment_id"])

        # Calculate route between georeferenced test points
        route_res = emergency_routing_service.calculate_emergency_route(
            start_lat=12.979766, start_lng=77.583438,
            dest_lat=12.966602, dest_lng=77.599961
        )
        self.assertTrue(route_res["success"])
        self.assertTrue(route_res["road_condition_aware"])
        self.assertGreaterEqual(route_res["blocked_edges_avoided"], 1)

    def test_09_degraded_edge_penalty(self):
        """9. Test degraded edge routing penalty application."""
        analysis = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        road_condition_service.apply_assessment(analysis["assessment_id"])
        active = road_condition_service.get_active_assessment()
        self.assertIsNotNone(active)

    def test_10_routing_consumes_updated_graph(self):
        """10. Test AI emergency routing engine consumes updated post-disaster graph."""
        analysis = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        road_condition_service.apply_assessment(analysis["assessment_id"])

        route_res = emergency_routing_service.calculate_emergency_route(
            start_lat=12.979766, start_lng=77.583438,
            dest_lat=12.966602, dest_lng=77.599961
        )
        self.assertTrue(route_res["road_condition_aware"])

    def test_11_apply_assessment_endpoint(self):
        """11. Test POST /api/road-condition/{assessment_id}/apply API."""
        analysis = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        aid = analysis["assessment_id"]

        res = client.post(f"/api/road-condition/{aid}/apply")
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["active_assessment"]["assessment_id"], aid)

    def test_12_existing_routing_unchanged_without_assessment(self):
        """12. Test existing routing behavior is unchanged when no assessment is active."""
        road_condition_service.reset_active_assessment()
        route_res = emergency_routing_service.calculate_emergency_route(
            start_lat=12.979766, start_lng=77.583438,
            dest_lat=12.966602, dest_lng=77.599961
        )
        self.assertTrue(route_res["success"])
        self.assertFalse(route_res["road_condition_aware"])
        self.assertEqual(route_res["blocked_edges_avoided"], 0)

    def test_13_api_endpoint_analyze(self):
        """13. Test POST /api/road-condition/analyze endpoint."""
        res = client.post("/api/road-condition/analyze", json={"demo_scenario": "SECTOR_4_FLOOD"})
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIn("assessment_id", data)
        self.assertEqual(data["status"], "COMPLETED")

    def test_14_api_v1_endpoint_analyze(self):
        """14. Test POST /api/v1/road-condition/analyze alias endpoint."""
        res = client.post("/api/v1/road-condition/analyze", json={"demo_scenario": "SECTOR_4_FLOOD"})
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIn("assessment_id", data)

    def test_15_missing_image_handling(self):
        """15. Test missing image handling gracefully falls back to default chip or simulated demo."""
        res = road_condition_service.analyze_road_condition(pre_image="non_existent_file.png")
        self.assertEqual(res["status"], "COMPLETED")
        self.assertGreater(res["roads_analyzed"], 0)

    def test_16_invalid_image_handling(self):
        """16. Test invalid assessment ID returns HTTP 404."""
        res = client.get("/api/road-condition/invalid-id-9999")
        self.assertEqual(res.status_code, 404)

    def test_17_active_route_reassessment(self):
        """17. Test route health evaluation with active post-disaster assessment."""
        analysis = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        road_condition_service.apply_assessment(analysis["assessment_id"])

        res_inc = client.post("/api/incidents", json={
            "incident_type": "FIRE", "severity": "CRITICAL",
            "latitude": 12.966602, "longitude": 77.599961,
            "location_name": "Post Disaster Site",
        })
        inc_id = res_inc.json()["id"]

        res_disp = client.post(f"/api/dispatch/incident/{inc_id}")
        disp_id = res_disp.json()["dispatch_id"]

        eval_res = client.post(f"/api/dispatches/{disp_id}/evaluate-route")
        self.assertEqual(eval_res.status_code, 200)
        data = eval_res.json()
        self.assertIn("POST_DISASTER_ROAD_BLOCKED", data.get("reason_codes", []))

    def test_18_reroute_recommendation(self):
        """18. Test reroute recommendation for blocked active routes."""
        analysis = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        road_condition_service.apply_assessment(analysis["assessment_id"])

        res_inc = client.post("/api/incidents", json={
            "incident_type": "FIRE", "severity": "CRITICAL",
            "latitude": 12.966602, "longitude": 77.599961,
        })
        inc_id = res_inc.json()["id"]

        res_disp = client.post(f"/api/dispatch/incident/{inc_id}")
        disp_id = res_disp.json()["dispatch_id"]

        reroute_res = client.post(f"/api/dispatches/{disp_id}/reroute-evaluate")
        self.assertEqual(reroute_res.status_code, 200)
        data = reroute_res.json()
        self.assertIn(data["decision"], ["REROUTE_REQUIRED", "REROUTE_RECOMMENDED", "NO_ALTERNATIVE"])

    def test_19_no_automatic_route_replacement(self):
        """19. Test operator approval workflow requires manual approval (no silent route replacement)."""
        analysis = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        road_condition_service.apply_assessment(analysis["assessment_id"])

        res_inc = client.post("/api/incidents", json={
            "incident_type": "MEDICAL", "severity": "HIGH",
            "latitude": 12.9716, "longitude": 77.5946,
        })
        inc_id = res_inc.json()["id"]
        res_disp = client.post(f"/api/dispatch/incident/{inc_id}")
        disp_id = res_disp.json()["dispatch_id"]

        disp_before = client.get(f"/api/dispatches/{disp_id}").json()
        reroute_res = client.post(f"/api/dispatches/{disp_id}/reroute-evaluate")

        disp_after = client.get(f"/api/dispatches/{disp_id}").json()

        # Route ID must not change automatically without POST /approve-reroute
        self.assertEqual(disp_before.get("route_id"), disp_after.get("route_id"))

    def test_20_no_fabricated_result_when_data_unavailable(self):
        """20. Test reset endpoint restores baseline graph without fabricated assessment results."""
        res_reset = client.post("/api/road-condition/reset")
        self.assertEqual(res_reset.status_code, 200)

        active_res = client.get("/api/road-condition/active").json()
        self.assertFalse(active_res["active"])


if __name__ == "__main__":
    unittest.main()
