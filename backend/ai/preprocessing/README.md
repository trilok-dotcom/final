# RESQROUTE — Stage 3C: SpaceNet 5 Mumbai Dataset Preprocessing

This directory contains the robust, standalone dataset preprocessing pipeline for pairing SpaceNet 5 Mumbai satellite imagery (`PS-RGB`) with GeoJSON road speed annotations (`geojson_roads_speed`) and rasterizing the road vector annotations into binary segmentation masks for U-Net model training.

---

## 🚀 Execution Commands

Execute all commands from the **project root directory** (`majorproject/`):

### 1. Run Preprocessing Pipeline
```bash
python -m backend.ai.preprocessing.preprocess_spacenet
```

This will:
1. Scan and pair all 1,016 `PS-RGB` satellite images and GeoJSON labels.
2. Perform rigorous data validation (checking file integrity, dimensions, CRS, and malformed geometries).
3. Convert vector road LineStrings into 1300x1300 binary raster masks aligned with native GeoTIFF affine transforms.
4. Perform a 100% reproducible **80% Train / 20% Validation** split.
5. Export processed images, masks, split manifests (`train.txt`, `val.txt`), and summary report (`dataset_summary.json`).

### 2. Generate Visual Quality Check Samples
```bash
python -m backend.ai.preprocessing.visualize_samples
```

This will:
- Generate 10+ side-by-side comparison images (Original Satellite Image vs. Road Mask Overlay).
- Create a multi-tile contact sheet grid (`contact_sheet.png`) for rapid inspection.

---

## 📁 Output Directory Structure

Processed output files are stored cleanly in `backend/ai/datasets/processed/`:

```
backend/ai/datasets/processed/
├── images/                  # 1300x1300 PS-RGB Satellite Images (.png)
├── masks/                   # 1300x1300 Single-Channel Binary Masks (0=background, 255=road) (.png)
├── visualizations/          # Side-by-side sample panels & contact sheet (.png)
├── train.txt                # Deterministic training split manifest (812 chip IDs)
├── val.txt                  # Deterministic validation split manifest (204 chip IDs)
└── dataset_summary.json     # Complete dataset statistics and error log
```

---

## ⚙️ Configuration (`config.py`)

Key parameters can be adjusted in `backend/ai/preprocessing/config.py`:

| Parameter | Default | Description |
|---|---|---|
| `ROAD_BUFFER_PIXELS` | `4.0` | Radius buffer in pixels for centerline road buffering (~2.5m road width) |
| `BACKGROUND_VAL` | `0` | Pixel value for non-road background |
| `ROAD_VAL` | `255` | Pixel value for road mask pixels |
| `TRAIN_SPLIT_RATIO` | `0.8` | Ratio of dataset allocated to training set (80%) |
| `VAL_SPLIT_RATIO` | `0.2` | Ratio of dataset allocated to validation set (20%) |
| `RANDOM_SEED` | `42` | Fixed seed for reproducible train/val splits |

---

## 🐍 PyTorch Dataset Usage (`dataset.py`)

The `SpaceNetRoadDataset` PyTorch `Dataset` class is ready for training pipelines:

```python
from backend.ai.preprocessing.dataset import SpaceNetRoadDataset

# Instantiate training dataset
train_dataset = SpaceNetRoadDataset(split="train", normalize=True)
print("Training samples:", len(train_dataset))

image_tensor, mask_tensor = train_dataset[0]
print("Image shape:", image_tensor.shape)  # torch.Size([3, 1300, 1300])
print("Mask shape:", mask_tensor.shape)   # torch.Size([1, 1300, 1300])
```

---

## 🏛️ Architecture Rules

- **Independent Module**: This preprocessing package operates completely independently from FastAPI, React, OSRM, and NetworkX routing components.
- **Geospatial Integrity**: Vector road geometries are rasterized using the exact GeoTIFF affine transform (`ModelPixelScaleTag` and `ModelTiepointTag`) without hardcoded or assumed coordinates.
