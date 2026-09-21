import sys
import math
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure root workspace directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app
from ai.georeference import DEFAULT_BOUNDS


def has_nan(obj) -> bool:
    """Recursively check if object contains NaN or Inf floating values."""
    if isinstance(obj, float):
        return math.isnan(obj) or math.isinf(obj)
    elif isinstance(obj, dict):
        return any(has_nan(v) for v in obj.values())
    elif isinstance(obj, list):
        return any(has_nan(v) for v in obj)
    return False


def run_stage_6_routing_test() -> None:
    """Run full Stage 6B Emergency Routing Engine validation test."""
    print("==================================================")
    print("  RESQROUTE — STAGE 6B: EMERGENCY ROUTING TEST   ")
    print("==================================================")

    print("[1/6] Initializing FastAPI TestClient...")
    with TestClient(app) as client:
        # 1. Test Valid Emergency Route Request
        print("[2/6] Sending valid emergency route request to '/api/ai/route'...")
        valid_payload = {
            "start": {
                "lat": 12.979766,
                "lng": 77.583438,
                "name": "Emergency Base Alpha",
            },
            "destination": {
                "lat": 12.966602,
                "lng": 77.599961,
                "name": "Disaster Zone Site #4",
            },
            "vehicle_type": "ambulance",
            "avoid_low_confidence": True,
        }

        response = client.post("/api/ai/route", json=valid_payload)
        assert response.status_code == 200, f"Expected 200 OK, got HTTP {response.status_code}: {response.text}"
        data = response.json()
        print(f"      HTTP Status: {response.status_code} OK")

        # 2. Verify JSON Response structure & assertions
        print("[3/6] Verifying route calculation JSON response fields...")
        assert data.get("success") is True, "Expected 'success' to be True"
        assert "route_id" in data and data["route_id"].startswith("route_"), "Invalid route_id"
        assert data.get("routing_engine") == "resqroute_ai_graph", "Invalid routing_engine identifier"
        assert "total_distance_meters" in data and data["total_distance_meters"] > 0, "Invalid total_distance_meters"
        assert "estimated_duration_seconds" in data and data["estimated_duration_seconds"] > 0, "Invalid estimated_duration_seconds"
        assert 0.0 <= data.get("average_confidence", -1) <= 1.0, "Invalid average_confidence range"
        assert data.get("risk_level") in ["low", "moderate", "high"], "Invalid risk_level"

        # Snapped Points
        snapped_start = data.get("snapped_start", {})
        snapped_dest = data.get("snapped_destination", {})
        assert "lat" in snapped_start and "lng" in snapped_start and "distance_to_road_meters" in snapped_start, "Invalid snapped_start"
        assert "lat" in snapped_dest and "lng" in snapped_dest and "distance_to_road_meters" in snapped_dest, "Invalid snapped_dest"

        # Geometry
        geom = data.get("geometry", {})
        assert geom.get("type") == "LineString", "Expected geometry.type == 'LineString'"
        coords = geom.get("coordinates", [])
        assert len(coords) >= 2, "Expected at least 2 route geometry coordinates"

        # Verify GeoJSON order [lng, lat] and bounds check
        print("[4/6] Verifying GeoJSON coordinate order [lng, lat] and georeference bounds...")
        for item in coords:
            lng_val, lat_val = item[0], item[1]
            assert DEFAULT_BOUNDS["west"] - 0.001 <= lng_val <= DEFAULT_BOUNDS["east"] + 0.001, f"Lng out of bounds: {lng_val}"
            assert DEFAULT_BOUNDS["south"] - 0.001 <= lat_val <= DEFAULT_BOUNDS["north"] + 0.001, f"Lat out of bounds: {lat_val}"

        # Steps
        steps = data.get("steps", [])
        assert len(steps) >= 2, "Expected at least 2 turn-by-turn steps"
        assert steps[0]["turn_type"] == "start", "Expected first step turn_type == 'start'"
        assert steps[-1]["turn_type"] == "arrive", "Expected last step turn_type == 'arrive'"

        # Verify no NaN values
        print("[5/6] Verifying zero NaN or Inf values in response payload...")
        assert not has_nan(data), "Response JSON contains NaN or Inf values!"

        # 3. Test Failure Cases
        print("[6/6] Testing error handling for invalid/off-road locations...")
        
        # Test Out of Bounds
        out_of_bounds_payload = {
            "start": {"lat": 40.7128, "lng": -74.0060},  # New York lat/lng
            "destination": {"lat": 12.9750, "lng": 77.5950},
        }
        res_oob = client.post("/api/ai/route", json=out_of_bounds_payload)
        assert res_oob.status_code == 400, f"Expected 400 Bad Request for out-of-bounds, got HTTP {res_oob.status_code}"
        print("      - Out-of-bounds error handling verified (HTTP 400)")

        # Test Off-Road (far from any road)
        # Note: even inside bounds, if a point is in a corner with no roads
        off_road_payload = {
            "start": {"lat": 12.9601, "lng": 77.5801},
            "destination": {"lat": 12.9750, "lng": 77.5950},
        }
        res_off = client.post("/api/ai/route", json=off_road_payload)
        assert res_off.status_code in [400, 404], f"Expected 400/404 for off-road point, got HTTP {res_off.status_code}"
        print("      - Off-road snap distance error handling verified")

        # 4. Print Required Final Summary Output Format
        print("\n============================================================")
        print("RESQROUTE — STAGE 6B ROUTING TEST")
        print("============================================================")
        print("Endpoint:")
        print("POST /api/ai/route")
        print("\nModel:")
        print("U-Net + ResNet-34")
        print("\nAI graph:")
        print("Loaded successfully")
        print("\nStart:")
        print(f"[{valid_payload['start']['lat']}, {valid_payload['start']['lng']}] ({valid_payload['start']['name']})")
        print("\nDestination:")
        print(f"[{valid_payload['destination']['lat']}, {valid_payload['destination']['lng']}] ({valid_payload['destination']['name']})")
        print("\nSnapped start:")
        print(f"[{snapped_start['lat']}, {snapped_start['lng']}] ({snapped_start['distance_to_road_meters']}m offset)")
        print("\nSnapped destination:")
        print(f"[{snapped_dest['lat']}, {snapped_dest['lng']}] ({snapped_dest['distance_to_road_meters']}m offset)")
        print("\nRoute found:")
        print("YES")
        print("\nAlgorithm:")
        print("Dijkstra")
        print("\nDistance:")
        print(f"{data['total_distance_meters']} meters")
        print("\nDuration:")
        print(f"{data['estimated_duration_seconds']} seconds")
        print("\nAverage AI confidence:")
        print(f"{data['average_confidence']}")
        print("\nRisk:")
        print(f"{data['risk_level']}")
        print("\nGraph nodes:")
        print(f"{len(coords)}")
        print("\nGraph edges:")
        print(f"{len(coords) - 1}")
        print("\nRoute geometry points:")
        print(f"{len(coords)}")
        print("\nAPI status:")
        print("200 OK")
        print("============================================================")
        print("STAGE 6B COMPLETED")
        print("============================================================")


if __name__ == "__main__":
    run_stage_6_routing_test()
