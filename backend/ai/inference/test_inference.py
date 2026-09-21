import sys
from pathlib import Path
import cv2
import numpy as np

# Ensure backend directory is in sys.path
AI_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = AI_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai.inference.predictor import RoadPredictor

# Evaluation output directory
EVAL_DIR = AI_DIR / "evaluation"
EVAL_DIR.mkdir(parents=True, exist_ok=True)

# Sample satellite image for testing
SAMPLE_IMAGE_PATH = AI_DIR / "datasets" / "processed" / "images" / "chip0.png"
MODEL_CHECKPOINT_PATH = AI_DIR / "models" / "resqroute_unet_resnet34_v2_best.pth"


def run_inference_test() -> None:
    """Run full inference validation test on RESQROUTE trained model."""
    print("==================================================")
    print("   RESQROUTE — STAGE 4: AI INFERENCE PIPELINE TEST  ")
    print("==================================================")

    # 1. Load the trained model using RoadPredictor
    if not MODEL_CHECKPOINT_PATH.exists():
        raise FileNotFoundError(f"Trained model file missing at '{MODEL_CHECKPOINT_PATH}'")

    if not SAMPLE_IMAGE_PATH.exists():
        raise FileNotFoundError(f"Sample satellite image missing at '{SAMPLE_IMAGE_PATH}'")

    print(f"[1/4] Loading trained model from: {MODEL_CHECKPOINT_PATH.name}...")
    predictor = RoadPredictor(model_path=MODEL_CHECKPOINT_PATH, default_threshold=0.25)
    print(f"      Model loaded successfully.")

    # 2. Run inference on sample image
    print(f"[2/4] Running inference on sample image: {SAMPLE_IMAGE_PATH.name}...")
    result = predictor.predict(SAMPLE_IMAGE_PATH, threshold=0.25)

    prob_map = result["probability_map"]
    mask = result["mask"]
    overlay = result["overlay"]
    road_network = result["road_network"]
    meta = result["metadata"]

    # 3. Save outputs to backend/ai/evaluation/
    print(f"[3/4] Saving results to: {EVAL_DIR}...")
    
    # Save probability map as 8-bit grayscale image (0-255)
    prob_map_uint8 = (prob_map * 255.0).clip(0, 255).astype(np.uint8)
    prob_path = EVAL_DIR / "prediction.png"
    cv2.imwrite(str(prob_path), prob_map_uint8)

    # Save binary mask
    mask_path = EVAL_DIR / "mask.png"
    cv2.imwrite(str(mask_path), mask)

    # Save overlay image (Convert RGB to BGR for OpenCV cv2.imwrite)
    overlay_bgr = cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR)
    overlay_path = EVAL_DIR / "overlay.png"
    cv2.imwrite(str(overlay_path), overlay_bgr)

    print(f"      - Prediction map saved: {prob_path.name}")
    print(f"      - Binary mask saved:    {mask_path.name}")
    print(f"      - Overlay saved:        {overlay_path.name}")

    # 4. Print required evaluation summary
    print("\n==================================================")
    print("               TEST RESULTS SUMMARY               ")
    print("==================================================")
    print(f"Model loaded successfully : Yes ({MODEL_CHECKPOINT_PATH.name})")
    print(f"Device                    : {meta['device']}")
    print(f"Input shape               : {meta['input_shape']}")
    print(f"Output shape              : {meta['output_shape']}")
    print(f"Threshold                 : {meta['threshold_used']}")
    print(f"Inference time            : {meta['inference_time_ms']} ms")
    print(f"Detected road pixel %     : {meta['road_pixel_percentage']} %")
    print(f"Extracted graph nodes     : {len(road_network['nodes'])}")
    print(f"Extracted graph edges     : {len(road_network['edges'])}")
    print("==================================================")


if __name__ == "__main__":
    run_inference_test()
