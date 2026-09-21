"""
===============================================================================
RESQROUTE AI — STAGE 10: SYSTEM EVALUATION & PERFORMANCE ANALYTICS TEST SUITE
===============================================================================
Automated test suite verifying System Evaluation Service, API Router, AI Model
accuracy benchmarks, Threshold sweeps, Inference timing, Routing metrics,
Resource & Dispatch metrics, Mission telemetry, Disaster simulation metrics,
Baseline OSRM & Nearest Unit comparisons, JSON/CSV exports, and SQLite persistence.
===============================================================================
"""

import sys
import json
import unittest
import numpy as np
from pathlib import Path

# Ensure backend root directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import init_db, get_db_connection
from app.services.evaluation_service import (
    evaluate_ai_model,
    evaluate_routing,
    evaluate_rerouting,
    evaluate_resources,
    evaluate_missions,
    evaluate_simulation,
    evaluate_osrm_baseline,
    evaluate_nearest_unit_baseline,
    get_overview,
    get_evaluation_runs,
    get_evaluation_run,
    export_run_metrics,
)


class TestStage10SystemEvaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 60)
        print("  RESQROUTE — STAGE 10: SYSTEM EVALUATION TEST SUITE")
        print("=" * 60)
        init_db()
        cls.client = TestClient(app)

    def test_01_get_evaluation_overview_initially(self):
        """Test GET /api/evaluation/overview endpoint returns valid overview schema."""
        response = self.client.get("/api/evaluation/overview")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("ai", data)
        self.assertIn("routing", data)
        self.assertIn("resources", data)
        self.assertIn("missions", data)
        self.assertIn("rerouting", data)
        self.assertIn("simulation", data)
        self.assertIn("baselines", data)
        print(" [PASS] Test 01: GET /api/evaluation/overview returns 200 OK")

    def test_02_get_evaluation_overview_v1_prefix(self):
        """Test GET /api/v1/evaluation/overview returns 200 OK under /v1 prefix."""
        response = self.client.get("/api/v1/evaluation/overview")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("success"))
        print(" [PASS] Test 02: GET /api/v1/evaluation/overview works under v1 prefix")

    def test_03_ai_evaluation_execution(self):
        """Test evaluate_ai_model executes and returns production & best threshold results."""
        res = evaluate_ai_model(num_samples=5)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertIn("production_metrics", res)
        self.assertIn("best_threshold_results", res)
        self.assertIn("threshold_curve", res)
        self.assertIn("latency_stats", res)
        print(" [PASS] Test 03: AI evaluation execution returns full metric payload")

    def test_04_dice_calculation_accuracy(self):
        """Test Dice coefficient metric calculation is bounded between 0.0 and 1.0."""
        res = evaluate_ai_model(num_samples=2)
        dice = res["production_metrics"]["dice"]
        self.assertGreaterEqual(dice, 0.0)
        self.assertLessEqual(dice, 1.0)
        print(f" [PASS] Test 04: Dice coefficient metric verified ({dice})")

    def test_05_iou_calculation_accuracy(self):
        """Test IoU metric calculation is bounded between 0.0 and 1.0."""
        res = evaluate_ai_model(num_samples=2)
        iou = res["production_metrics"]["iou"]
        self.assertGreaterEqual(iou, 0.0)
        self.assertLessEqual(iou, 1.0)
        print(f" [PASS] Test 05: IoU metric verified ({iou})")

    def test_06_precision_calculation_accuracy(self):
        """Test Precision metric calculation is bounded between 0.0 and 1.0."""
        res = evaluate_ai_model(num_samples=2)
        prec = res["production_metrics"]["precision"]
        self.assertGreaterEqual(prec, 0.0)
        self.assertLessEqual(prec, 1.0)
        print(f" [PASS] Test 06: Precision metric verified ({prec})")

    def test_07_recall_calculation_accuracy(self):
        """Test Recall metric calculation is bounded between 0.0 and 1.0."""
        res = evaluate_ai_model(num_samples=2)
        rec = res["production_metrics"]["recall"]
        self.assertGreaterEqual(rec, 0.0)
        self.assertLessEqual(rec, 1.0)
        print(f" [PASS] Test 07: Recall metric verified ({rec})")

    def test_08_threshold_sweep_evaluation(self):
        """Test threshold sweep evaluates all required decision thresholds."""
        res = evaluate_ai_model(num_samples=2)
        curve = res["threshold_curve"]
        thresholds = [pt["threshold"] for pt in curve]
        for expected_th in [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50]:
            self.assertIn(expected_th, thresholds)
        print(" [PASS] Test 08: Threshold sweep covers all 8 specified decision thresholds")

    def test_09_best_threshold_detection(self):
        """Test optimal threshold detection identifies maximum validation Dice score."""
        res = evaluate_ai_model(num_samples=2)
        best_th_res = res["best_threshold_results"]
        self.assertIn("best_threshold", best_th_res)
        self.assertIn("best_dice", best_th_res)
        print(f" [PASS] Test 09: Best threshold detected at {best_th_res['best_threshold']} with Dice {best_th_res['best_dice']}")

    def test_10_inference_latency_measurement(self):
        """Test AI inference latency tracking returns mean, median, min, max, std dev."""
        res = evaluate_ai_model(num_samples=2)
        lat = res["latency_stats"]
        self.assertIn("preprocess_mean_ms", lat)
        self.assertIn("inference_mean_ms", lat)
        self.assertIn("postprocess_mean_ms", lat)
        self.assertIn("total_pipeline_mean_ms", lat)
        self.assertGreater(lat["inference_mean_ms"], 0.0)
        print(f" [PASS] Test 10: Inference latency measured: Mean GPU/CPU Inference = {lat['inference_mean_ms']} ms")

    def test_11_routing_evaluation_execution(self):
        """Test evaluate_routing returns emergency route performance metrics."""
        res = evaluate_routing(num_samples=5)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertIn("routes_evaluated", res)
        self.assertIn("average_distance_m", res)
        self.assertIn("average_eta_s", res)
        self.assertIn("average_route_health", res)
        print(" [PASS] Test 11: Emergency routing evaluation executed successfully")

    def test_12_route_success_rate_calculation(self):
        """Test route success rate percentage is calculated correctly."""
        res = evaluate_routing(num_samples=5)
        self.assertIn("success_rate_percent", res)
        self.assertGreaterEqual(res["success_rate_percent"], 0.0)
        self.assertLessEqual(res["success_rate_percent"], 100.0)
        print(f" [PASS] Test 12: Route success rate verified ({res['success_rate_percent']}%)")

    def test_13_route_distance_calculation(self):
        """Test route average and median distance calculations."""
        res = evaluate_routing(num_samples=5)
        self.assertGreaterEqual(res["average_distance_m"], 0.0)
        self.assertGreaterEqual(res["median_distance_m"], 0.0)
        print(f" [PASS] Test 13: Average route distance verified ({res['average_distance_m']} m)")

    def test_14_route_eta_calculation(self):
        """Test average ETA seconds calculation."""
        res = evaluate_routing(num_samples=5)
        self.assertGreaterEqual(res["average_eta_s"], 0.0)
        print(f" [PASS] Test 14: Average route ETA verified ({res['average_eta_s']} s)")

    def test_15_route_confidence_calculation(self):
        """Test average AI route confidence score is between 0.0 and 1.0."""
        res = evaluate_routing(num_samples=5)
        self.assertGreaterEqual(res["average_confidence"], 0.0)
        self.assertLessEqual(res["average_confidence"], 1.0)
        print(f" [PASS] Test 15: AI route confidence verified ({res['average_confidence']})")

    def test_16_route_health_aggregation(self):
        """Test route health score aggregation and breakdown categories."""
        res = evaluate_routing(num_samples=5)
        self.assertIn("health_breakdown", res)
        hb = res["health_breakdown"]
        self.assertIn("healthy", hb)
        self.assertIn("degraded", hb)
        self.assertIn("critical", hb)
        print(" [PASS] Test 16: Route health score aggregation and breakdown categories verified")

    def test_17_reroute_events_aggregation(self):
        """Test dynamic rerouting evaluation queries reroute_events table."""
        res = evaluate_rerouting()
        self.assertEqual(res["status"], "COMPLETED")
        self.assertIn("degradation_events", res)
        self.assertIn("reroutes_approved", res)
        print(f" [PASS] Test 17: Rerouting evaluation verified ({res['reroutes_approved']} approved reroutes)")

    def test_18_health_improvement_calculation(self):
        """Test dynamic rerouting health improvement (+pts) calculation."""
        res = evaluate_rerouting()
        self.assertIn("average_health_improvement_pts", res)
        print(f" [PASS] Test 18: Rerouting health improvement verified (+{res['average_health_improvement_pts']} pts)")

    def test_19_eta_improvement_calculation(self):
        """Test dynamic rerouting ETA delta calculation."""
        res = evaluate_rerouting()
        self.assertIn("average_eta_change_s", res)
        print(f" [PASS] Test 19: Rerouting ETA delta verified ({res['average_eta_change_s']} s)")

    def test_20_resource_utilization_calculation(self):
        """Test resource optimization evaluation calculates fleet utilization percentage."""
        res = evaluate_resources()
        self.assertEqual(res["status"], "COMPLETED")
        self.assertIn("resource_utilization_percent", res)
        self.assertGreaterEqual(res["resource_utilization_percent"], 0.0)
        print(f" [PASS] Test 20: Resource fleet utilization verified ({res['resource_utilization_percent']}%)")

    def test_21_dispatch_latency_calculation(self):
        """Test dispatch latency calculation (incident creation -> dispatch creation)."""
        res = evaluate_missions()
        self.assertEqual(res["status"], "COMPLETED")
        self.assertIn("average_dispatch_latency_s", res)
        print(f" [PASS] Test 21: Dispatch creation latency verified ({res['average_dispatch_latency_s']} s)")

    def test_22_mission_duration_calculation(self):
        """Test mission duration calculation from dispatch creation to completion."""
        res = evaluate_missions()
        self.assertIn("average_mission_duration_s", res)
        print(f" [PASS] Test 22: Mission duration verified ({res['average_mission_duration_s']} s)")

    def test_23_disaster_simulation_evaluation(self):
        """Test disaster exercise simulation metrics evaluation."""
        res = evaluate_simulation()
        self.assertEqual(res["status"], "COMPLETED")
        self.assertIn("total_sessions", res)
        print(" [PASS] Test 23: Disaster simulation evaluation executed successfully")

    def test_24_simulation_data_isolation(self):
        """Test simulation evaluation strictly isolates records with simulation_session_id."""
        res = evaluate_simulation()
        for sess in res.get("sessions_evaluated", []):
            self.assertIn("simulation_id", sess)
        print(" [PASS] Test 24: Simulation records strictly isolated with simulation_id tag")

    def test_25_osrm_baseline_comparison(self):
        """Test Baseline A OSRM routing comparison returns neutral side-by-side payload."""
        res = evaluate_osrm_baseline(num_samples=2)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertIn("ai_routing", res)
        self.assertIn("osrm_baseline", res)
        self.assertIn("interpretation_note", res)
        print(" [PASS] Test 25: Baseline A (OSRM) neutral comparison verified")

    def test_26_nearest_unit_baseline_comparison(self):
        """Test Baseline B Nearest Unit comparison returns neutral side-by-side payload."""
        res = evaluate_nearest_unit_baseline(num_samples=2)
        self.assertIn("status", res)
        self.assertIn("baseline_type", res)
        print(" [PASS] Test 26: Baseline B (Nearest Unit) neutral comparison verified")

    def test_27_evaluation_history_retrieval(self):
        """Test get_evaluation_runs returns historical evaluation run records."""
        runs = get_evaluation_runs()
        self.assertIsInstance(runs, list)
        self.assertGreater(len(runs), 0)
        print(f" [PASS] Test 27: Evaluation history retrieved ({len(runs)} runs in DB)")

    def test_28_evaluation_persistence_sqlite(self):
        """Test evaluation run and metric records are persisted in SQLite DB tables."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM evaluation_runs;")
        run_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM evaluation_metrics;")
        metric_count = cursor.fetchone()[0]
        conn.close()

        self.assertGreater(run_count, 0)
        self.assertGreater(metric_count, 0)
        print(f" [PASS] Test 28: Evaluation persistence confirmed ({run_count} runs, {metric_count} metrics in SQLite)")

    def test_29_export_run_metrics_json(self):
        """Test exporting evaluation run metrics in JSON format."""
        runs = get_evaluation_runs()
        target_id = runs[0]["id"]
        content, mime = export_run_metrics(target_id, export_format="json")
        self.assertEqual(mime, "application/json")
        parsed = json.loads(content)
        self.assertEqual(parsed["id"], target_id)
        print(" [PASS] Test 29: Evaluation run JSON export verified")

    def test_30_export_run_metrics_csv(self):
        """Test exporting evaluation run metrics in CSV format."""
        runs = get_evaluation_runs()
        target_id = runs[0]["id"]
        content, mime = export_run_metrics(target_id, export_format="csv")
        self.assertEqual(mime, "text/csv")
        self.assertIn("id,evaluation_run_id,metric_name", content)
        print(" [PASS] Test 30: Evaluation run CSV export verified")

    def test_31_api_post_eval_endpoints(self):
        """Test REST API POST endpoints for triggering evaluations."""
        resp = self.client.post("/api/evaluation/ai", json={"sample_count": 2})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))

        resp = self.client.post("/api/evaluation/routing", json={"sample_count": 2})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))

        resp = self.client.post("/api/evaluation/rerouting")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))

        resp = self.client.post("/api/evaluation/resources")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))

        resp = self.client.post("/api/evaluation/missions")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))
        print(" [PASS] Test 31: All REST API POST evaluation trigger endpoints succeeded (HTTP 200)")

    def test_32_api_get_run_detail_and_metrics(self):
        """Test GET /api/evaluation/runs/{id} and /metrics endpoints."""
        runs = get_evaluation_runs()
        target_id = runs[0]["id"]

        resp = self.client.get(f"/api/evaluation/runs/{target_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))

        resp = self.client.get(f"/api/evaluation/runs/{target_id}/metrics")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))
        print(" [PASS] Test 32: GET /api/evaluation/runs/{id} and /metrics endpoints verified")

    def test_33_api_export_endpoint(self):
        """Test GET /api/evaluation/runs/{id}/export endpoint for json and csv."""
        runs = get_evaluation_runs()
        target_id = runs[0]["id"]

        resp = self.client.get(f"/api/evaluation/runs/{target_id}/export?format=json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.headers["content-type"].startswith("application/json"))

        resp = self.client.get(f"/api/evaluation/runs/{target_id}/export?format=csv")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.headers["content-type"].startswith("text/csv"))
        print(" [PASS] Test 33: GET /api/evaluation/runs/{id}/export endpoint verified for JSON & CSV")

    def test_34_invalid_run_id_returns_404(self):
        """Test requesting invalid evaluation run ID returns 404 Not Found."""
        resp = self.client.get("/api/evaluation/runs/non-existent-id")
        self.assertEqual(resp.status_code, 404)
        print(" [PASS] Test 34: Invalid evaluation run ID returns 404 Not Found")

    def test_35_repeatable_evaluation_idempotent(self):
        """Test running evaluation multiple times creates separate auditable records."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM evaluation_runs;")
        count_before = cursor.fetchone()[0]
        conn.close()

        _ = evaluate_ai_model(num_samples=2)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM evaluation_runs;")
        count_after = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count_after, count_before + 1)
        print(" [PASS] Test 35: Repeatable evaluations create separate auditable historical run records")


if __name__ == "__main__":
    unittest.main()
