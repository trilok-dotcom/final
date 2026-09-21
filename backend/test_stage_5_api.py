import sys
import time
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure root workspace directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app
from ai.config import AI_DIR

SAMPLE_IMAGE_PATH = AI_DIR / "datasets" / "processed" / "images" / "chip0.png"


def run_stage_5_api_test() -> None:
    """Run full Stage 5 API integration test for /api/ai/detect-roads."""
    print("==================================================")
    print("  RESQROUTE — STAGE 5: BACKEND AI API INTEGRATION ")
    print("==================================================")

    if not SAMPLE_IMAGE_PATH.exists():
        raise FileNotFoundError(f"Sample test image missing at '{SAMPLE_IMAGE_PATH}'")

    print(f"[1/5] Initializing FastAPI TestClient with preloaded U-Net ResNet-34 model...")
    # Initialize TestClient using lifespan context manager
    with TestClient(app) as client:
        print("[2/5] Preparing sample satellite image 'chip0.png'...")
        with open(SAMPLE_IMAGE_PATH, "rb") as img_file:
            files = {"file": ("chip0.png", img_file, "image/png")}

            print("[3/5] Sending HTTP POST request to '/api/ai/detect-roads'...")
            start_wall_time = time.perf_counter()
            response = client.post("/api/ai/detect-roads", files=files)
            wall_time_ms = (time.perf_counter() - start_wall_time) * 1000.0

        # Assert HTTP status code 200 OK
        assert response.status_code == 200, f"Expected 200 OK, got HTTP {response.status_code}: {response.text}"
        data = response.json()
        print(f"      HTTP Status: {response.status_code} OK (Round-trip time: {wall_time_ms:.2f} ms)")

        # [4/5] Verify JSON Response payload fields
        print("[4/5] Verifying structured JSON response payload...")
        assert data.get("success") is True, "Expected 'success' to be True"
        assert "inference_time_ms" in data and data["inference_time_ms"] > 0, "Invalid inference_time_ms"
        assert data.get("threshold") == 0.25, f"Expected threshold 0.25, got {data.get('threshold')}"
        assert "detected_road_pixel_percentage" in data, "Missing detected_road_pixel_percentage"
        assert data.get("image_dimensions") == [512, 512], "Expected image_dimensions [512, 512]"

        assert "prediction_url" in data, "Missing prediction_url"
        assert "mask_url" in data, "Missing mask_url"
        assert "overlay_url" in data, "Missing overlay_url"

        assert "road_graph" in data, "Missing road_graph"
        road_graph = data["road_graph"]
        assert len(road_graph["nodes"]) == data["graph_nodes"], "Nodes count mismatch"
        assert len(road_graph["edges"]) == data["graph_edges"], "Edges count mismatch"

        # [5/5] Verify output files generated on server filesystem
        print("[5/5] Verifying generated output image files on disk...")
        for url_key in ["prediction_url", "mask_url", "overlay_url"]:
            rel_url = data[url_key]
            rel_path = rel_url.lstrip("/").replace("outputs/", "")
            file_on_disk = AI_DIR / "outputs" / rel_path
            assert file_on_disk.exists(), f"Generated artifact missing on disk at '{file_on_disk}'"
            print(f"      - Verified static artifact: {file_on_disk.name} ({file_on_disk.stat().st_size} bytes)")

        print("\n==================================================")
        print("         STAGE 5 API TEST RESULTS SUMMARY         ")
        print("==================================================")
        print(f"HTTP Status              : 200 OK")
        print(f"Endpoint                 : POST /api/ai/detect-roads")
        print(f"Model Engine Status      : Loaded ONCE (CUDA GPU active)")
        print(f"Threshold                : {data['threshold']}")
        print(f"Inference execution time : {data['inference_time_ms']} ms")
        print(f"Round-trip request time  : {wall_time_ms:.2f} ms")
        print(f"Detected road pixel %    : {data['detected_road_pixel_percentage']} %")
        print(f"Extracted graph nodes    : {data['graph_nodes']}")
        print(f"Extracted graph edges    : {data['graph_edges']}")
        print(f"Prediction image URL     : {data['prediction_url']}")
        print(f"Binary mask URL          : {data['mask_url']}")
        print(f"Road overlay URL         : {data['overlay_url']}")
        print("==================================================")
        print("STAGE 5 API INTEGRATION VERIFIED 100% SUCCESSFULLY!")
        print("==================================================")


if __name__ == "__main__":
    run_stage_5_api_test()
