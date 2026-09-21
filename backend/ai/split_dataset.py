import os
import shutil
import random

# ==========================
# CONFIGURATION
# ==========================
DATASET_DIR = "datasets"

TRAIN_DIR = os.path.join(DATASET_DIR, "train")
VALID_DIR = os.path.join(DATASET_DIR, "valid")
TEST_DIR = os.path.join(DATASET_DIR, "test")

VALID_RATIO = 0.10
TEST_RATIO = 0.10

random.seed(42)

# ==========================
# Create folders
# ==========================

os.makedirs(VALID_DIR, exist_ok=True)
os.makedirs(TEST_DIR, exist_ok=True)

# ==========================
# Find all image-mask pairs
# ==========================

sat_images = [f for f in os.listdir(TRAIN_DIR) if f.endswith("_sat.jpg")]

pairs = []

for sat in sat_images:

    mask = sat.replace("_sat.jpg", "_mask.png")

    if os.path.exists(os.path.join(TRAIN_DIR, mask)):
        pairs.append((sat, mask))

print(f"Total paired samples found : {len(pairs)}")

# Shuffle

random.shuffle(pairs)

# Split

num_total = len(pairs)

num_valid = int(num_total * VALID_RATIO)
num_test = int(num_total * TEST_RATIO)

valid_pairs = pairs[:num_valid]
test_pairs = pairs[num_valid:num_valid+num_test]

print("Validation:", len(valid_pairs))
print("Test:", len(test_pairs))
print("Remaining Train:", num_total - len(valid_pairs) - len(test_pairs))

# ==========================
# Move files
# ==========================

def move_pairs(pair_list, destination):

    for sat, mask in pair_list:

        shutil.move(
            os.path.join(TRAIN_DIR, sat),
            os.path.join(destination, sat)
        )

        shutil.move(
            os.path.join(TRAIN_DIR, mask),
            os.path.join(destination, mask)
        )

move_pairs(valid_pairs, VALID_DIR)
move_pairs(test_pairs, TEST_DIR)

print("\nDataset successfully split!")