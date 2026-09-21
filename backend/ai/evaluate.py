import sys
import json
from pathlib import Path

import numpy as np
import torch
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader

# --------------------------------------------------
# PATH SETUP
# --------------------------------------------------

AI_DIR = Path(__file__).resolve().parent
BACKEND_DIR = AI_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# --------------------------------------------------
# IMPORT PROJECT MODULES
# --------------------------------------------------

from model import RoadSegmentationModel
from dataset import SatelliteRoadDataset
from metrics import calculate_all_metrics


# ==================================================
# CONFIGURATION
# ==================================================

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

WEIGHTS = AI_DIR / "weights" / "best_model.pth"

TEST_DIR = AI_DIR / "datasets" / "test"

OUTPUT_DIR = AI_DIR / "outputs" / "test_evaluation"
SAMPLES_DIR = OUTPUT_DIR / "samples"
PREDICTIONS_DIR = OUTPUT_DIR / "predictions"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)

BATCH_SIZE = 2
NUM_WORKERS = 0
THRESHOLD = 0.5

# Number of visual examples to save
NUM_VISUAL_SAMPLES = 12


# ==================================================
# HEADER
# ==================================================

print("=" * 60)
print("       RESQROUTE AI - TEST SET EVALUATION")
print("=" * 60)

print(f"Device       : {DEVICE}")

if torch.cuda.is_available():
    print(f"GPU          : {torch.cuda.get_device_name(0)}")
    print(f"CUDA Version : {torch.version.cuda}")

print(f"Test Dataset : {TEST_DIR}")
print(f"Model        : {WEIGHTS}")
print(f"Batch Size   : {BATCH_SIZE}")
print(f"Threshold    : {THRESHOLD}")

print("=" * 60)


# ==================================================
# CHECK FILES
# ==================================================

if not WEIGHTS.exists():
    raise FileNotFoundError(
        f"Best model weights not found:\n{WEIGHTS}"
    )

if not TEST_DIR.exists():
    raise FileNotFoundError(
        f"Test dataset directory not found:\n{TEST_DIR}"
    )


# ==================================================
# LOAD TEST DATASET
# ==================================================

print("\n[INFO] Loading test dataset...")

test_dataset = SatelliteRoadDataset(
    split="test"
)

print(f"[INFO] Test samples: {len(test_dataset)}")

if len(test_dataset) == 0:
    raise RuntimeError(
        "No test samples were found."
    )


test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=NUM_WORKERS,
    pin_memory=torch.cuda.is_available()
)


# ==================================================
# LOAD MODEL
# ==================================================

print("\n[INFO] Loading trained U-Net...")

model = RoadSegmentationModel(
    encoder_name="resnet34",
    encoder_weights=None,
    in_channels=3,
    classes=1,
    device=DEVICE,
)

model.load_model(
    WEIGHTS,
    device=DEVICE
)

model.eval()

print("[SUCCESS] Best model loaded.")
print(f"[INFO] Parameters: {model.count_parameters():,}")


# ==================================================
# GLOBAL METRIC ACCUMULATORS
# ==================================================

total_tp = 0.0
total_fp = 0.0
total_fn = 0.0
total_tn = 0.0

total_pixels = 0

# Used for average batch metrics
metric_sums = {
    "iou": 0.0,
    "dice": 0.0,
    "pixel_accuracy": 0.0,
    "precision": 0.0,
    "recall": 0.0,
    "f1": 0.0,
}

num_batches = 0


# ==================================================
# VISUALIZATION FUNCTION
# ==================================================

def save_comparison(
    image_tensor,
    target_tensor,
    prediction_tensor,
    probability_tensor,
    sample_number,
):
    """
    Save:
        Satellite Image
        Ground Truth
        Prediction
        Overlay
        Probability Map
    """

    # ----------------------------------------------
    # Convert image tensor back to display format
    # ----------------------------------------------

    image = image_tensor.detach().cpu().numpy()

    # CHW -> HWC
    image = np.transpose(image, (1, 2, 0))

    # Undo ImageNet normalization
    mean = np.array(
        [0.485, 0.456, 0.406]
    )

    std = np.array(
        [0.229, 0.224, 0.225]
    )

    image = image * std + mean

    image = np.clip(image, 0, 1)

    # ----------------------------------------------
    # Ground truth
    # ----------------------------------------------

    target = target_tensor.detach().cpu().numpy()

    if target.ndim == 3:
        target = target[0]

    target = (target > 0.5).astype(np.uint8)

    # ----------------------------------------------
    # Prediction
    # ----------------------------------------------

    prediction = prediction_tensor.detach().cpu().numpy()

    if prediction.ndim == 3:
        prediction = prediction[0]

    prediction = (prediction > 0.5).astype(np.uint8)

    # ----------------------------------------------
    # Probability
    # ----------------------------------------------

    probability = probability_tensor.detach().cpu().numpy()

    if probability.ndim == 3:
        probability = probability[0]

    # ----------------------------------------------
    # Overlay
    # ----------------------------------------------

    overlay = (
        image * 255
    ).astype(np.uint8).copy()

    road_pixels = prediction == 1

    # Red highlight for detected roads
    overlay[road_pixels] = (
        0.5 * overlay[road_pixels]
        + 0.5 * np.array([255, 0, 0])
    ).astype(np.uint8)

    overlay = overlay.astype(np.float32) / 255.0

    # ----------------------------------------------
    # Plot
    # ----------------------------------------------

    fig, axes = plt.subplots(
        1,
        5,
        figsize=(20, 4)
    )

    axes[0].imshow(image)
    axes[0].set_title("Satellite Image")

    axes[1].imshow(
        target,
        cmap="gray"
    )
    axes[1].set_title("Ground Truth")

    axes[2].imshow(
        prediction,
        cmap="gray"
    )
    axes[2].set_title("Prediction")

    axes[3].imshow(overlay)
    axes[3].set_title("Road Overlay")

    axes[4].imshow(
        probability,
        cmap="hot",
        vmin=0,
        vmax=1
    )
    axes[4].set_title("Probability")

    for ax in axes:
        ax.axis("off")

    plt.tight_layout()

    output_path = (
        SAMPLES_DIR
        / f"sample_{sample_number:04d}.png"
    )

    plt.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight"
    )

    plt.close(fig)


# ==================================================
# TEST EVALUATION
# ==================================================

print("\n[INFO] Starting test evaluation...")
print(
    f"[INFO] Evaluating {len(test_dataset)} test images..."
)

sample_counter = 0

with torch.inference_mode():

    for batch_index, batch in enumerate(test_loader):

        images, masks = batch

        images = images.to(
            DEVICE,
            non_blocking=True
        )

        masks = masks.to(
            DEVICE,
            non_blocking=True
        )

        # ------------------------------------------
        # MODEL PREDICTION
        # ------------------------------------------

        logits = model(images)

        probabilities = torch.sigmoid(logits)

        predictions = (
            probabilities >= THRESHOLD
        ).float()

        # ------------------------------------------
        # GLOBAL CONFUSION MATRIX
        # ------------------------------------------

        pred_flat = predictions.view(-1)
        target_flat = masks.view(-1)

        tp = (
            (pred_flat == 1)
            & (target_flat == 1)
        ).sum().item()

        fp = (
            (pred_flat == 1)
            & (target_flat == 0)
        ).sum().item()

        fn = (
            (pred_flat == 0)
            & (target_flat == 1)
        ).sum().item()

        tn = (
            (pred_flat == 0)
            & (target_flat == 0)
        ).sum().item()

        total_tp += tp
        total_fp += fp
        total_fn += fn
        total_tn += tn

        total_pixels += target_flat.numel()

        # ------------------------------------------
        # EXISTING PROJECT METRICS
        # ------------------------------------------

        batch_metrics = calculate_all_metrics(
            logits,
            masks,
            threshold=THRESHOLD,
            from_logits=True
        )

        for key in metric_sums:
            metric_sums[key] += batch_metrics[key]

        num_batches += 1

        # ------------------------------------------
        # SAVE VISUAL SAMPLES
        # ------------------------------------------

        if sample_counter < NUM_VISUAL_SAMPLES:

            batch_size_actual = images.shape[0]

            for i in range(batch_size_actual):

                if sample_counter >= NUM_VISUAL_SAMPLES:
                    break

                save_comparison(
                    images[i],
                    masks[i],
                    predictions[i],
                    probabilities[i],
                    sample_counter + 1
                )

                sample_counter += 1

        # ------------------------------------------
        # PROGRESS
        # ------------------------------------------

        if (
            (batch_index + 1) % 50 == 0
            or batch_index == len(test_loader) - 1
        ):

            processed = min(
                (batch_index + 1) * BATCH_SIZE,
                len(test_dataset)
            )

            print(
                f"[PROGRESS] "
                f"{processed}/{len(test_dataset)} "
                f"images evaluated"
            )


# ==================================================
# CALCULATE FINAL GLOBAL METRICS
# ==================================================

eps = 1e-7

iou = (
    total_tp + eps
) / (
    total_tp
    + total_fp
    + total_fn
    + eps
)

dice = (
    2 * total_tp + eps
) / (
    2 * total_tp
    + total_fp
    + total_fn
    + eps
)

precision = (
    total_tp + eps
) / (
    total_tp
    + total_fp
    + eps
)

recall = (
    total_tp + eps
) / (
    total_tp
    + total_fn
    + eps
)

f1 = (
    2 * precision * recall + eps
) / (
    precision + recall + eps
)

pixel_accuracy = (
    total_tp + total_tn
) / total_pixels


# ==================================================
# AVERAGE BATCH METRICS
# ==================================================

average_batch_metrics = {
    key: value / num_batches
    for key, value in metric_sums.items()
}


# ==================================================
# PRINT RESULTS
# ==================================================

print("\n")
print("=" * 60)
print("                 FINAL TEST RESULTS")
print("=" * 60)

print(f"Test Samples       : {len(test_dataset)}")
print(f"Total Pixels       : {total_pixels:,}")

print("\n--- GLOBAL METRICS ---")

print(f"IoU                : {iou:.4f}")
print(f"Dice               : {dice:.4f}")
print(f"Precision          : {precision:.4f}")
print(f"Recall             : {recall:.4f}")
print(f"F1 Score           : {f1:.4f}")
print(f"Pixel Accuracy     : {pixel_accuracy:.4f}")

print("\n--- CONFUSION COUNTS ---")

print(f"True Positives     : {int(total_tp):,}")
print(f"False Positives    : {int(total_fp):,}")
print(f"False Negatives    : {int(total_fn):,}")
print(f"True Negatives     : {int(total_tn):,}")

print("\n--- AVERAGE BATCH METRICS ---")

for key, value in average_batch_metrics.items():
    print(
        f"{key.replace('_', ' ').title():<19}: "
        f"{value:.4f}"
    )


# ==================================================
# SAVE JSON RESULTS
# ==================================================

results = {
    "model": "U-Net ResNet34",
    "weights": str(WEIGHTS),
    "device": str(DEVICE),
    "gpu": (
        torch.cuda.get_device_name(0)
        if torch.cuda.is_available()
        else "CPU"
    ),
    "test_samples": len(test_dataset),
    "image_resolution": "512x512",
    "threshold": THRESHOLD,

    "global_metrics": {
        "iou": iou,
        "dice": dice,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "pixel_accuracy": pixel_accuracy,
    },

    "confusion_counts": {
        "true_positive": int(total_tp),
        "false_positive": int(total_fp),
        "false_negative": int(total_fn),
        "true_negative": int(total_tn),
    },

    "average_batch_metrics": average_batch_metrics,
}


json_path = OUTPUT_DIR / "test_metrics.json"

with open(
    json_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        results,
        f,
        indent=4
    )


# ==================================================
# SAVE TEXT SUMMARY
# ==================================================

summary_path = OUTPUT_DIR / "test_summary.txt"

with open(
    summary_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "RESQROUTE AI - TEST SET EVALUATION\n"
    )

    f.write("=" * 50 + "\n\n")

    f.write(
        f"Model: U-Net ResNet34\n"
    )

    f.write(
        f"Test Samples: {len(test_dataset)}\n"
    )

    f.write(
        f"Device: {DEVICE}\n"
    )

    if torch.cuda.is_available():
        f.write(
            f"GPU: {torch.cuda.get_device_name(0)}\n"
        )

    f.write("\nGLOBAL METRICS\n")
    f.write("-" * 30 + "\n")

    f.write(
        f"IoU: {iou:.4f}\n"
    )

    f.write(
        f"Dice: {dice:.4f}\n"
    )

    f.write(
        f"Precision: {precision:.4f}\n"
    )

    f.write(
        f"Recall: {recall:.4f}\n"
    )

    f.write(
        f"F1: {f1:.4f}\n"
    )

    f.write(
        f"Pixel Accuracy: {pixel_accuracy:.4f}\n"
    )


# ==================================================
# FINAL OUTPUT
# ==================================================

print("\n")
print("[SUCCESS] Test evaluation completed.")

print(
    f"[SUCCESS] Metrics saved to:\n"
    f"         {json_path}"
)

print(
    f"[SUCCESS] Summary saved to:\n"
    f"         {summary_path}"
)

print(
    f"[SUCCESS] Visual samples saved to:\n"
    f"         {SAMPLES_DIR}"
)

print("\n" + "=" * 60)
print("          TEST EVALUATION COMPLETED")
print("=" * 60)