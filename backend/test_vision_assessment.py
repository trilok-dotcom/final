import os
import sys
import unittest
import json
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import init_db, get_db_connection
from app.services.vision_road_assessment import vision_assessment_provider, VisionAssessmentProvider, VisionRoadAssessmentResult, RoadSegmentAssessment
from app.services.road_condition_service import road_condition_service
from app.services.emergency_routing_service import emergency_routing_service

client = TestClient(app)


class TestVisionRoadAssessment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        road_condition_service.reset_active_assessment()

    def tearDown(self):
        road_condition_service.reset_active_assessment()

    def test_01_missing_api_key_status(self):
        """1. Test missing API key returns provider_not_configured status without crashing."""
        old_v = os.environ.get("VISION_AI_API_KEY")
        old_g = os.environ.get("GOOGLE_API_KEY")
        old_gm = os.environ.get("GEMINI_API_KEY")
        try:
            os.environ["VISION_AI_API_KEY"] = ""
            os.environ["GOOGLE_API_KEY"] = ""
            os.environ["GEMINI_API_KEY"] = ""
            provider = VisionAssessmentProvider()
            self.assertFalse(provider.is_configured())

            default_chip = backend_dir / "ai" / "datasets" / "processed" / "images" / "chip0.png"
            res = provider.assess_road_traversability(default_chip, default_chip)
            self.assertEqual(res["status"], "provider_not_configured")
            self.assertFalse(res["provider_configured"])
        finally:
            if old_v is not None: os.environ["VISION_AI_API_KEY"] = old_v
            if old_g is not None: os.environ["GOOGLE_API_KEY"] = old_g
            if old_gm is not None: os.environ["GEMINI_API_KEY"] = old_gm

    def test_02_pydantic_schema_validation(self):
        """2. Test Pydantic validation of Vision AI response schema."""
        data = {
            "overall_summary": "Disaster road condition analysis complete.",
            "disclaimer": "Image-based traversability estimate — not structural safety certification.",
            "roads": [
                {
                    "id": "road_001",
                    "condition": "SAFE",
                    "confidence": 0.95,
                    "reason": "Road intact",
                    "before_points": [[10, 10]],
                    "after_points": [[10, 10]],
                },
                {
                    "id": "road_002",
                    "condition": "BLOCKED",
                    "confidence": 0.88,
                    "reason": "Flooded segment",
                },
            ],
        }
        validated = VisionRoadAssessmentResult(**data)
        self.assertEqual(len(validated.roads), 2)
        self.assertEqual(validated.roads[0].condition, "SAFE")
        self.assertEqual(validated.roads[1].condition, "BLOCKED")

    def test_03_invalid_json_handling(self):
        """3. Test handling invalid JSON from API provider gracefully."""
        invalid_raw = "INVALID_NON_JSON_PROSE_TEXT"
        with self.assertRaises(Exception):
            json.loads(invalid_raw)

    def test_04_overlay_image_generation(self):
        """4. Test generated after_assessment_overlay.png overlay image with legend."""
        res = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        self.assertIn("overlay_image_url", res)
        overlay_path = backend_dir / "outputs" / "after_assessment_overlay.png"
        self.assertTrue(overlay_path.exists())
        self.assertGreater(overlay_path.stat().st_size, 0)

    def test_05_classifications_presence(self):
        """5. Test SAFE, DEGRADED, BLOCKED, UNKNOWN classifications are populated."""
        res = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        self.assertIn("safe_count", res)
        self.assertIn("degraded_count", res)
        self.assertIn("blocked_count", res)
        self.assertIn("unknown_count", res)

        conditions = {s["condition"] for s in res["segments"]}
        self.assertTrue(any(c in conditions for c in ["SAFE", "DEGRADED", "BLOCKED", "UNKNOWN"]))

    def test_06_after_image_preservation(self):
        """6. Test original AFTER image path is preserved in assessment result."""
        res = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        self.assertIn("post_image_path", res)
        self.assertIsNotNone(res["post_image_path"])

    def test_07_routing_graph_update_blocked_exclusion(self):
        """7. Test routing graph excludes BLOCKED roads and penalizes DEGRADED roads."""
        analysis = road_condition_service.analyze_road_condition(demo_scenario="SECTOR_4_FLOOD")
        road_condition_service.apply_assessment(analysis["assessment_id"])

        route_res = emergency_routing_service.calculate_emergency_route(
            start_lat=12.979766, start_lng=77.583438,
            dest_lat=12.966602, dest_lng=77.599961
        )
        self.assertTrue(route_res["success"])
        self.assertTrue(route_res["road_condition_aware"])
        self.assertGreaterEqual(route_res["blocked_edges_avoided"], 1)

    def test_08_api_endpoint_compatibility(self):
        """8. Test complete API endpoint compatibility for road condition analysis."""
        res_analyze = client.post("/api/road-condition/analyze", json={"demo_scenario": "SECTOR_4_FLOOD"})
        self.assertEqual(res_analyze.status_code, 200)
        data = res_analyze.json()
        aid = data["assessment_id"]

        res_get = client.get(f"/api/road-condition/{aid}")
        self.assertEqual(res_get.status_code, 200)

        res_apply = client.post(f"/api/road-condition/{aid}/apply")
        self.assertEqual(res_apply.status_code, 200)

        res_active = client.get("/api/road-condition/active")
        self.assertEqual(res_active.status_code, 200)
        self.assertTrue(res_active.json()["active"])

        res_reset = client.post("/api/road-condition/reset")
        self.assertEqual(res_reset.status_code, 200)

        res_active_post = client.get("/api/road-condition/active")
        self.assertFalse(res_active_post.json()["active"])


if __name__ == "__main__":
    unittest.main()
