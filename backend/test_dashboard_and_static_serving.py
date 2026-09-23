import sys
import time
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app
from ai.config import AI_DIR

SAMPLE_IMAGE_PATH = AI_DIR / "datasets" / "processed" / "images" / "chip0.png"


def run_dashboard_static_serving_test():
    print("==================================================")
    print("  VERIFYING AI ANALYSIS DASHBOARD & STATIC SERVING ")
    print("==================================================")

    if not SAMPLE_IMAGE_PATH.exists():
        from PIL import Image
        temp_img_path = ROOT_DIR / "temp_sat_test.png"
        Image.new("RGB", (512, 512), color=(40, 140, 60)).save(temp_img_path)
        img_to_upload = temp_img_path
    else:
        img_to_upload = SAMPLE_IMAGE_PATH

    print(f"[1/4] Starting FastAPI TestClient...")
    with TestClient(app) as client:
        # 1. Test POST /api/v1/analyze-satellite (AI Analysis Dashboard)
        print("[2/4] Testing POST /api/v1/analyze-satellite...")
        with open(img_to_upload, "rb") as f:
            resp = client.post("/api/v1/analyze-satellite", files={"file": ("sat_test.png", f, "image/png")})

        assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"
        data = resp.json()
        print("      POST /api/v1/analyze-satellite -> 200 OK")

        # Verify response structure
        assert data.get("success") is True, "Response success must be True"
        assert "prediction" in data, "Missing 'prediction' object"
        assert "road_network" in data, "Missing 'road_network' object"

        mask_url = data["prediction"]["mask_url"]
        overlay_url = data["prediction"]["overlay_url"]
        heatmap_url = data["prediction"]["heatmap_url"]

        skeleton_url = data["road_network"]["skeleton_url"]
        net_overlay_url = data["road_network"]["overlay_url"]
        comparison_url = data["road_network"]["comparison_url"]

        print(f"      - mask_url       : {mask_url}")
        print(f"      - skeleton_url   : {skeleton_url}")
        print(f"      - net_overlay_url: {net_overlay_url}")
        print(f"      - heatmap_url    : {heatmap_url}")
        print(f"      - comparison_url : {comparison_url}")

        # 2. Test HTTP GET on each generated static URL (Requirement #11)
        print("[3/4] Testing HTTP GET requests on all 5 generated visualization URLs...")
        urls_to_test = [
            ("AI Road Segmentation Mask", mask_url),
            ("Extracted Road Skeleton", skeleton_url),
            ("Road Network Overlay", net_overlay_url),
            ("Prediction Heatmap", heatmap_url),
            ("4-Panel Quadrant Grid", comparison_url),
        ]

        for name, url_path in urls_to_test:
            get_resp = client.get(url_path)
            print(f"      HTTP GET {url_path} ({name}) -> Status: {get_resp.status_code}, Size: {len(get_resp.content)} bytes")
            assert get_resp.status_code == 200, f"Failed to fetch {name} at '{url_path}'. Status: {get_resp.status_code}"
            assert len(get_resp.content) > 100, f"Empty content received for {name} at '{url_path}'"

        # 3. Test Stage 7E Post-Disaster Road Condition Assessment co-existence
        print("[4/4] Testing Stage 7E Post-Disaster endpoint co-existence...")
        with open(img_to_upload, "rb") as f_pre, open(img_to_upload, "rb") as f_post:
            resp_7e = client.post(
                "/api/road-condition/analyze",
                files={
                    "before_image": ("pre.png", f_pre, "image/png"),
                    "after_image": ("post.png", f_post, "image/png"),
                },
            )

        assert resp_7e.status_code == 200, f"Stage 7E assess failed: {resp_7e.status_code}: {resp_7e.text}"
        data_7e = resp_7e.json()
        annotated_after_url = data_7e["annotated_after_image"]
        get_7e_resp = client.get(annotated_after_url)
        print(f"      Stage 7E annotated_after_image GET {annotated_after_url} -> Status: {get_7e_resp.status_code}, Size: {len(get_7e_resp.content)} bytes")
        assert get_7e_resp.status_code == 200, f"Failed to fetch Stage 7E overlay at '{annotated_after_url}'"

        print("\n==================================================")
        print("  ALL DASHBOARD & STATIC SERVING TESTS PASSED!   ")
        print("==================================================")


if __name__ == "__main__":
    run_dashboard_static_serving_test()
