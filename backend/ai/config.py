from pathlib import Path

# Base AI Directory (backend/ai/)
AI_DIR = Path(__file__).resolve().parent

# Datasets Root Directory
DATASETS_DIR = AI_DIR / "datasets"

# Sub-directory paths for train, validation, and test splits
TRAIN_DIR = DATASETS_DIR / "train"
VALID_DIR = DATASETS_DIR / "valid"
TEST_DIR = DATASETS_DIR / "test"

# Image Dimension Configuration
IMAGE_HEIGHT = 512
IMAGE_WIDTH = 512
CHANNELS = 3

# File Naming Conventions
SAT_SUFFIX = "_sat"
MASK_SUFFIX = "_mask"
SUPPORTED_IMG_EXTENSIONS = (".jpg", ".jpeg", ".png", ".tif", ".tiff")
SUPPORTED_MASK_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tif", ".tiff")

# DataLoader Configuration
BATCH_SIZE = 4
NUM_WORKERS = 0  # 0 recommended for cross-platform compatibility (Windows process spawn)
PIN_MEMORY = True

# ImageNet Normalization Parameters
NORM_MEAN = (0.485, 0.456, 0.406)
NORM_STD = (0.229, 0.224, 0.225)
