import sys
import httpx
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
TEST_IMG_PATH = Path("ai/datasets/test/100703_sat.jpg")

print("=" * 60)
print("   RESQROUTE STAGE 3A INTEGRATION & ENDPOINT VERIFICATION   ")
print("=" * 60)

# 1. Health Check GET /api/v1/health
print("\n[TEST 1] GET /api/v1/health ...")
r = httpx.get(f"{BASE_URL}/api/v1/health")
print(f"Status Code : {r.status_code}")
print(f"Response    : {r.json()}")
assert r.status_code == 200, "Health check failed!"
print("=> TEST 1 PASSED!")

# 2. AI Inference POST /api/v1/predict
print("\n[TEST 2] POST /api/v1/predict with real satellite image ...")
if not TEST_IMG_PATH.exists():
    raise FileNotFoundError(f"Test image not found at {TEST_IMG_PATH}")

with open(TEST_IMG_PATH, "rb") as f:
    files = {"file": ("100703_sat.jpg", f, "image/jpeg")}
    r = httpx.post(f"{BASE_URL}/api/v1/predict", files=files, timeout=30.0)

print(f"Status Code : {r.status_code}")
res_json = r.json()
print(f"Response JSON:\n{res_json}")
assert r.status_code == 200, f"Predict failed: {res_json}"
assert res_json.get("success") is True, "success is not True"
assert "confidence" in res_json, "confidence missing"
assert "road_percentage" in res_json, "road_percentage missing"
assert "inference_time_ms" in res_json, "inference_time_ms missing"
assert "mask_url" in res_json, "mask_url missing"
assert "overlay_url" in res_json, "overlay_url missing"
assert "heatmap_url" in res_json, "heatmap_url missing"
print("=> TEST 2 PASSED!")

# 3. Static Assets Accessibility Test
print("\n[TEST 3] Verifying generated output URLs accessibility ...")
for url_key in ["mask_url", "overlay_url", "heatmap_url"]:
    url_path = res_json[url_key]
    full_url = f"{BASE_URL}{url_path}"
    img_resp = httpx.get(full_url)
    print(f"Checking {url_key} ({full_url}) -> Status: {img_resp.status_code}, Length: {len(img_resp.content)} bytes, Content-Type: {img_resp.headers.get('content-type')}")
    assert img_resp.status_code == 200, f"Failed to fetch image at {full_url}"
    assert len(img_resp.content) > 0, f"Empty image content at {full_url}"
print("=> TEST 3 PASSED!")

# 4. Existing Route Endpoint POST /api/v1/route Verification
print("\n[TEST 4] POST /api/v1/route (OSRM routing engine check) ...")
route_payload = {
    "start": {"lat": 12.9716, "lng": 77.5946},
    "destination": {"lat": 12.9780, "lng": 77.6010}
}
r_route = httpx.post(f"{BASE_URL}/api/v1/route", json=route_payload, timeout=20.0)
print(f"Status Code : {r_route.status_code}")
route_json = r_route.json()
print(f"Route Response Summary: ID={route_json.get('id')}, Distance={route_json.get('total_distance_meters')}m, Steps={len(route_json.get('steps', []))}")
assert r_route.status_code == 200, f"Route request failed: {route_json}"
print("=> TEST 4 PASSED!")

# 5. Invalid File Format Error Handling Check
print("\n[TEST 5] Error Handling: POST /api/v1/predict with invalid file extension ...")
invalid_files = {"file": ("test.txt", b"This is not an image", "text/plain")}
r_invalid = httpx.post(f"{BASE_URL}/api/v1/predict", files=invalid_files)
print(f"Status Code : {r_invalid.status_code}")
print(f"Response    : {r_invalid.json()}")
assert r_invalid.status_code == 400, "Invalid file format validation failed!"
print("=> TEST 5 PASSED!")

print("\n" + "=" * 60)
print("   ALL STAGE 3A VERIFICATION TESTS PASSED SUCCESSFULLY 100%!   ")
print("=" * 60)
