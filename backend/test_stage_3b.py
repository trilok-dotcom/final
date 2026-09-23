import json
import httpx
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
TEST_IMG_PATH = Path("ai/datasets/test/100703_sat.jpg")

def main():
    print("=" * 70)
    print("   RESQROUTE STAGE 3B ROAD NETWORK EXTRACTION VERIFICATION   ")
    print("=" * 70)

    # 1. GET /api/v1/health
    print("\n[TEST 1] GET /api/v1/health ...")
    r_health = httpx.get(f"{BASE_URL}/api/v1/health")
    print(f"Status: {r_health.status_code}, Body: {r_health.json()}")
    assert r_health.status_code == 200, "Health check failed!"
    print("=> TEST 1 PASSED!")

    # 2. POST /api/v1/road-network
    print("\n[TEST 2] POST /api/v1/road-network ...")
    net_payload = {"mask_path": "outputs/prediction_mask.png"}
    r_net = httpx.post(f"{BASE_URL}/api/v1/road-network", json=net_payload, timeout=20.0)
    print(f"Status: {r_net.status_code}")
    net_res = r_net.json()
    print(f"Road Network Response JSON:\n{json.dumps(net_res, indent=2)}")
    assert r_net.status_code == 200, f"Road network extraction failed: {net_res}"
    assert net_res.get("success") is True, "success is not True"
    assert net_res["graph_nodes"] > 0, "graph_nodes must be > 0"
    assert net_res["graph_edges"] > 0, "graph_edges must be > 0"
    print("=> TEST 2 PASSED!")

    # 3. POST /api/v1/analyze-satellite (End-to-End Combined Pipeline)
    print("\n[TEST 3] POST /api/v1/analyze-satellite (Combined AI Pipeline) ...")
    test_img = TEST_IMG_PATH
    if not test_img.exists():
        from PIL import Image
        test_img = Path("test_synthetic_sat.jpg")
        Image.new("RGB", (256, 256), color=(50, 120, 50)).save(test_img)

    with open(test_img, "rb") as f:
        files = {"file": ("sat_test.jpg", f, "image/jpeg")}
        r_comb = httpx.post(f"{BASE_URL}/api/v1/analyze-satellite", files=files, timeout=30.0)

    print(f"Status: {r_comb.status_code}")
    comb_res = r_comb.json()
    print(f"Combined Pipeline Response JSON:\n{json.dumps(comb_res, indent=2)}")
    assert r_comb.status_code == 200, f"Analyze satellite failed: {comb_res}"
    assert comb_res.get("success") is True
    assert "prediction" in comb_res
    assert "road_network" in comb_res
    print("=> TEST 3 PASSED!")

    # 4. Verify Static Assets & GeoJSON File Retrieval
    print("\n[TEST 4] Fetching generated output files & GeoJSON ...")
    urls_to_check = [
        ("skeleton_url", comb_res["road_network"]["skeleton_url"]),
        ("overlay_url", comb_res["road_network"]["overlay_url"]),
        ("comparison_url", comb_res["road_network"]["comparison_url"]),
        ("geojson_url", comb_res["road_network"]["geojson_url"]),
    ]

    for name, url_path in urls_to_check:
        full_url = f"{BASE_URL}{url_path}"
        asset_resp = httpx.get(full_url)
        print(f"Fetching {name} ({full_url}) -> Status: {asset_resp.status_code}, Size: {len(asset_resp.content)} bytes")
        assert asset_resp.status_code == 200, f"Failed to fetch {name} at {full_url}"

    # Inspect GeoJSON content
    geojson_resp = httpx.get(f"{BASE_URL}{comb_res['road_network']['geojson_url']}")
    geojson_dict = geojson_resp.json()
    features = geojson_dict.get("features", [])
    print(f"\nGeoJSON Inspection: Type={geojson_dict.get('type')}, Feature Count={len(features)}")
    if features:
        first_feat = features[0]
        print(f"Sample Feature 0: Properties={first_feat.get('properties')}, Coordinates Sample={first_feat['geometry']['coordinates'][:3]}")
        assert first_feat["geometry"]["type"] == "LineString"
        assert len(first_feat["geometry"]["coordinates"]) >= 2
    print("=> TEST 4 PASSED!")

    # 5. POST /api/v1/route Verification (Ensure OSRM is preserved)
    print("\n[TEST 5] POST /api/v1/route (OSRM preservation check) ...")
    r_route = httpx.post(
        f"{BASE_URL}/api/v1/route",
        json={"start": {"lat": 12.9716, "lng": 77.5946}, "destination": {"lat": 12.9780, "lng": 77.6010}},
        timeout=15.0
    )
    print(f"Status: {r_route.status_code}, Distance: {r_route.json().get('total_distance_meters')}m")
    assert r_route.status_code == 200, "OSRM routing check failed!"
    print("=> TEST 5 PASSED!")

    print("\n" + "=" * 70)
    print("   ALL STAGE 3B VERIFICATION TESTS PASSED SUCCESSFULLY 100%!   ")
    print("=" * 70)


if __name__ == "__main__":
    main()
