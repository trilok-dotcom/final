import sys
from pathlib import Path
import torch
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import albumentations as A
from albumentations.pytorch import ToTensorV2

AI_DIR = Path(__file__).resolve().parent
BACKEND_DIR = AI_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai.model import RoadSegmentationModel




# --------------------------------------------------
# CONFIG
# --------------------------------------------------

AI_DIR = Path(__file__).resolve().parent

IMAGE_DIR = AI_DIR / "datasets" / "test"
WEIGHTS = AI_DIR / "weights" / "best_model.pth"
OUTPUT_DIR = AI_DIR / "outputs" / "prediction_test"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("=" * 60)
print("       RESQROUTE AI - REAL IMAGE PREDICTION TEST")
print("=" * 60)

print(f"Device : {DEVICE}")

if torch.cuda.is_available():
    print(f"GPU    : {torch.cuda.get_device_name(0)}")


# --------------------------------------------------
# FIND REAL SATELLITE IMAGE
# --------------------------------------------------

images = sorted(IMAGE_DIR.glob("*_sat.jpg"))

if not images:
    raise FileNotFoundError(
        f"No *_sat.jpg images found in {IMAGE_DIR}"
    )

image_path = images[0]

print(f"\n[INFO] Test image:")
print(f"       {image_path.name}")


# --------------------------------------------------
# LOAD MODEL
# --------------------------------------------------

print("\n[INFO] Loading trained model...")

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

print("[SUCCESS] Trained model loaded.")


# --------------------------------------------------
# PREPROCESS IMAGE
# --------------------------------------------------

transform = A.Compose([
    A.Resize(512, 512),
    A.Normalize(
        mean=(0.485, 0.456, 0.406),
        std=(0.229, 0.224, 0.225),
    ),
    ToTensorV2(),
])


# --------------------------------------------------
# LOAD IMAGE
# --------------------------------------------------

original = Image.open(image_path).convert("RGB")

original_np = np.array(original)

transformed = transform(image=original_np)

image_tensor = transformed["image"].unsqueeze(0).to(DEVICE)


print("\n--- IMAGE INFORMATION ---")

print(f"Original Size : {original.size}")
print(f"Tensor Shape  : {image_tensor.shape}")
print(f"Tensor Device : {image_tensor.device}")


# --------------------------------------------------
# PREDICTION
# --------------------------------------------------

print("\n[INFO] Running U-Net inference...")

with torch.no_grad():

    logits = model(image_tensor)

    probabilities = torch.sigmoid(logits)

    prediction = (probabilities > 0.5).float()


prediction = prediction.squeeze().cpu().numpy()

probabilities = probabilities.squeeze().cpu().numpy()


print("[SUCCESS] Prediction completed.")

print(f"Probability Min : {probabilities.min():.4f}")
print(f"Probability Max : {probabilities.max():.4f}")

road_pixels = np.sum(prediction == 1)
total_pixels = prediction.size

road_percentage = (road_pixels / total_pixels) * 100

print(f"Detected Road Pixels : {road_pixels:,}")
print(f"Total Pixels         : {total_pixels:,}")
print(f"Road Coverage        : {road_percentage:.2f}%")


# --------------------------------------------------
# SAVE MASK
# --------------------------------------------------

mask_path = OUTPUT_DIR / "predicted_mask.png"

mask_image = (prediction * 255).astype(np.uint8)

Image.fromarray(mask_image).save(mask_path)

print(f"\n[SUCCESS] Saved mask:")
print(f"         {mask_path}")


# --------------------------------------------------
# CREATE OVERLAY
# --------------------------------------------------

resized_original = original.resize((512, 512))

original_512 = np.array(resized_original)

overlay = original_512.copy()

road = prediction == 1

# Highlight detected roads
overlay[road] = (
    0.5 * overlay[road] +
    0.5 * np.array([255, 0, 0])
).astype(np.uint8)


overlay_path = OUTPUT_DIR / "road_overlay.png"

Image.fromarray(overlay).save(overlay_path)

print(f"[SUCCESS] Saved overlay:")
print(f"         {overlay_path}")


# --------------------------------------------------
# SAVE COMPARISON
# --------------------------------------------------

fig = plt.figure(figsize=(15, 5))

ax1 = fig.add_subplot(1, 3, 1)
ax1.imshow(original_512)
ax1.set_title("Satellite Image")
ax1.axis("off")

ax2 = fig.add_subplot(1, 3, 2)
ax2.imshow(prediction, cmap="gray")
ax2.set_title("Predicted Road Mask")
ax2.axis("off")

ax3 = fig.add_subplot(1, 3, 3)
ax3.imshow(overlay)
ax3.set_title("Detected Roads Overlay")
ax3.axis("off")

comparison_path = OUTPUT_DIR / "prediction_comparison.png"

plt.tight_layout()
plt.savefig(comparison_path, dpi=150)
plt.close()

print(f"[SUCCESS] Saved comparison:")
print(f"         {comparison_path}")


print("\n" + "=" * 60)
print("       REAL IMAGE PREDICTION COMPLETED")
print("=" * 60)