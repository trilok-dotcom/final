import os
import sys
import json
import random
import argparse
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn

from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm


# ============================================================
# PATH SETUP
# ============================================================

AI_DIR = Path(__file__).resolve().parent
BACKEND_DIR = AI_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ============================================================
# PROJECT IMPORTS
# ============================================================

from ai import config
from ai.dataset import SatelliteRoadDataset, get_dataloaders
from ai.model import RoadSegmentationModel, get_default_device
from ai.losses import CombinedLoss
from ai.metrics import calculate_all_metrics


# ============================================================
# REPRODUCIBILITY
# ============================================================

def set_seed(seed: int = 42) -> None:
    """
    Set random seeds for reproducibility.
    """

    random.seed(seed)
    np.random.seed(seed)

    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)

        # Reproducibility
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


# ============================================================
# EARLY STOPPING
# ============================================================

class EarlyStopping:
    """
    Stop training when validation IoU stops improving.
    """

    def __init__(
        self,
        patience: int = 7,
        min_delta: float = 1e-4
    ) -> None:

        self.patience = patience
        self.min_delta = min_delta

        self.counter = 0
        self.best_score: Optional[float] = None
        self.early_stop = False

    def __call__(self, val_iou: float) -> bool:

        if self.best_score is None:

            self.best_score = val_iou

        elif val_iou < self.best_score + self.min_delta:

            self.counter += 1

            if self.counter >= self.patience:
                self.early_stop = True

        else:

            self.best_score = val_iou
            self.counter = 0

        return self.early_stop


# ============================================================
# TRAINING GRAPHS
# ============================================================

def save_training_graphs(
    history: Dict[str, List[float]],
    output_dir: Path
) -> None:

    output_dir.mkdir(parents=True, exist_ok=True)

    epochs = range(1, len(history["train_loss"]) + 1)

    # --------------------------------------------------------
    # LOSS CURVE
    # --------------------------------------------------------

    plt.figure(figsize=(8, 6))

    plt.plot(
        epochs,
        history["train_loss"],
        "b-o",
        label="Training Loss"
    )

    plt.plot(
        epochs,
        history["val_loss"],
        "r-s",
        label="Validation Loss"
    )

    plt.title(
        "Training & Validation Loss Curve",
        fontsize=14,
        fontweight="bold"
    )

    plt.xlabel("Epoch")
    plt.ylabel("Combined Loss")

    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()

    plt.savefig(
        output_dir / "loss_curve.png",
        dpi=300
    )

    plt.close()

    # --------------------------------------------------------
    # IOU CURVE
    # --------------------------------------------------------

    plt.figure(figsize=(8, 6))

    plt.plot(
        epochs,
        history["val_iou"],
        "g-^",
        label="Validation IoU"
    )

    plt.title(
        "Validation IoU Curve",
        fontsize=14,
        fontweight="bold"
    )

    plt.xlabel("Epoch")
    plt.ylabel("Intersection over Union")

    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()

    plt.savefig(
        output_dir / "iou_curve.png",
        dpi=300
    )

    plt.close()

    # --------------------------------------------------------
    # DICE CURVE
    # --------------------------------------------------------

    plt.figure(figsize=(8, 6))

    plt.plot(
        epochs,
        history["val_dice"],
        "m-d",
        label="Validation Dice"
    )

    plt.title(
        "Validation Dice Score Curve",
        fontsize=14,
        fontweight="bold"
    )

    plt.xlabel("Epoch")
    plt.ylabel("Dice Score")

    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()

    plt.savefig(
        output_dir / "dice_curve.png",
        dpi=300
    )

    plt.close()

    # --------------------------------------------------------
    # COMBINED GRAPH
    # --------------------------------------------------------

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(18, 5)
    )

    axes[0].plot(
        epochs,
        history["train_loss"],
        label="Train Loss"
    )

    axes[0].plot(
        epochs,
        history["val_loss"],
        label="Validation Loss"
    )

    axes[0].set_title("Loss Curves")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].legend()
    axes[0].grid(True)

    axes[1].plot(
        epochs,
        history["val_iou"],
        label="Validation IoU"
    )

    axes[1].set_title("IoU Curve")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("IoU")
    axes[1].legend()
    axes[1].grid(True)

    axes[2].plot(
        epochs,
        history["val_dice"],
        label="Validation Dice"
    )

    axes[2].set_title("Dice Curve")
    axes[2].set_xlabel("Epoch")
    axes[2].set_ylabel("Dice")
    axes[2].legend()
    axes[2].grid(True)

    plt.suptitle(
        "RESQROUTE AI - Road Segmentation Training",
        fontsize=16,
        fontweight="bold"
    )

    plt.tight_layout()

    plt.savefig(
        output_dir / "all_curves.png",
        dpi=300
    )

    plt.close()

    print(
        f"[SUCCESS] Saved training graphs to '{output_dir}'"
    )


# ============================================================
# DATA CHECK
# ============================================================

def ensure_dummy_data_if_empty() -> None:
    """
    Only creates dummy data if train/valid directories are empty.

    Your real dataset is already populated, so this function
    should not create anything during your actual training.
    """

    import cv2

    for split_dir in [
        config.TRAIN_DIR,
        config.VALID_DIR
    ]:

        split_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        if not list(split_dir.glob("*")):

            print(
                f"[SETUP] Directory empty: {split_dir}"
            )

            print(
                "[SETUP] Creating temporary dummy samples..."
            )

            for i in range(1, 5):

                dummy_sat = np.full(
                    (512, 512, 3),
                    (34, 139, 34),
                    dtype=np.uint8
                )

                cv2.line(
                    dummy_sat,
                    (0, 128 * i),
                    (512, 128 * i),
                    (180, 180, 180),
                    20
                )

                dummy_mask = np.zeros(
                    (512, 512),
                    dtype=np.uint8
                )

                cv2.line(
                    dummy_mask,
                    (0, 128 * i),
                    (512, 128 * i),
                    255,
                    20
                )

                cv2.imwrite(
                    str(
                        split_dir /
                        f"sample_{i}_sat.jpg"
                    ),
                    cv2.cvtColor(
                        dummy_sat,
                        cv2.COLOR_RGB2BGR
                    )
                )

                cv2.imwrite(
                    str(
                        split_dir /
                        f"sample_{i}_mask.png"
                    ),
                    dummy_mask
                )


# ============================================================
# MAIN TRAINING FUNCTION
# ============================================================

def train_model(
    epochs: int = 20,
    batch_size: int = 2,
    learning_rate: float = 1e-4,
    seed: int = 42,
    patience: int = 7,
    grad_clip_norm: float = 1.0,
    dice_weight: float = 1.0,
    bce_weight: float = 1.0,
    weights_dir: Optional[Path] = None,
    logs_dir: Optional[Path] = None,
    tensorboard_dir: Optional[Path] = None,
    outputs_dir: Optional[Path] = None,
) -> Dict[str, List[float]]:

    # ========================================================
    # 1. SEED
    # ========================================================

    set_seed(seed)

    # ========================================================
    # 2. DIRECTORIES
    # ========================================================

    weights_path = (
        weights_dir
        if weights_dir is not None
        else AI_DIR / "weights"
    )

    logs_path = (
        logs_dir
        if logs_dir is not None
        else AI_DIR / "logs"
    )

    tb_path = (
        tensorboard_dir
        if tensorboard_dir is not None
        else AI_DIR / "tensorboard"
    )

    output_path = (
        outputs_dir
        if outputs_dir is not None
        else AI_DIR / "outputs"
    )

    for path in [
        weights_path,
        logs_path,
        tb_path,
        output_path
    ]:

        path.mkdir(
            parents=True,
            exist_ok=True
        )

    best_model_file = (
        weights_path /
        "best_model.pth"
    )

    last_model_file = (
        weights_path /
        "last_model.pth"
    )

    log_json_file = (
        logs_path /
        "training_log.json"
    )

    # ========================================================
    # 3. DEVICE
    # ========================================================

    device = get_default_device()

    print("=" * 50)
    print(
        "     RESQROUTE AI - U-NET MODEL TRAINING PIPELINE"
    )
    print("=" * 50)

    print(
        f"PyTorch Version  : {torch.__version__}"
    )

    print(
        f"CUDA Available   : {torch.cuda.is_available()}"
    )

    print(
        f"Selected Device  : {device}"
    )

    if device.type == "cuda":

        print(
            f"GPU              : {torch.cuda.get_device_name(0)}"
        )

        print(
            f"CUDA Version     : {torch.version.cuda}"
        )

    print(
        f"Hyperparameters  : "
        f"Epochs={epochs}, "
        f"BatchSize={batch_size}, "
        f"LR={learning_rate}, "
        f"Seed={seed}"
    )

    print(
        f"Image Resolution : "
        f"{config.IMAGE_HEIGHT}x{config.IMAGE_WIDTH}"
    )

    print("Save Paths:")

    print(
        f"  - Checkpoints  : {weights_path}"
    )

    print(
        f"  - Logs         : {logs_path}"
    )

    print(
        f"  - TensorBoard  : {tb_path}"
    )

    print(
        f"  - Output Graphs: {output_path}"
    )

    print()

    # ========================================================
    # 4. DATASET
    # ========================================================

    ensure_dummy_data_if_empty()

    print("[INFO] Loading datasets...")

    dataloaders = get_dataloaders(
        batch_size=batch_size,
        num_workers=config.NUM_WORKERS
    )

    train_loader = dataloaders["train"]

    val_loader = dataloaders["valid"]

    print(
        f"[INFO] Training samples  : "
        f"{len(train_loader.dataset)}"
    )

    print(
        f"[INFO] Validation samples: "
        f"{len(val_loader.dataset)}"
    )

    print(
        f"[INFO] Training batches  : "
        f"{len(train_loader)}"
    )

    print(
        f"[INFO] Validation batches: "
        f"{len(val_loader)}"
    )

    # ========================================================
    # 5. MODEL
    # ========================================================

    print("\n[INFO] Creating U-Net model...")

    model = RoadSegmentationModel(
        encoder_name="resnet34",
        encoder_weights="imagenet",
        in_channels=3,
        classes=1,
        device=device
    )

    print(
        f"[INFO] Model parameters: "
        f"{model.count_parameters():,}"
    )

    # ========================================================
    # 6. LOSS
    # ========================================================

    criterion = CombinedLoss(
        dice_weight=dice_weight,
        bce_weight=bce_weight
    )

    # ========================================================
    # 7. OPTIMIZER
    # ========================================================

    optimizer = AdamW(
        model.parameters(),
        lr=learning_rate,
        weight_decay=1e-4
    )

    # ========================================================
    # 8. LEARNING RATE SCHEDULER
    # ========================================================

    scheduler = CosineAnnealingLR(
        optimizer,
        T_max=max(epochs, 2),
        eta_min=1e-6
    )

    # ========================================================
    # 9. AUTOMATIC MIXED PRECISION
    # ========================================================

    use_amp = device.type == "cuda"

    scaler = torch.amp.GradScaler(
        "cuda",
        enabled=use_amp
    )

    print(
        f"[INFO] Automatic Mixed Precision: "
        f"{'ENABLED' if use_amp else 'DISABLED'}"
    )

    # ========================================================
    # 10. TENSORBOARD
    # ========================================================

    writer = SummaryWriter(
        log_dir=str(tb_path)
    )

    # ========================================================
    # 11. EARLY STOPPING
    # ========================================================

    early_stopper = EarlyStopping(
        patience=patience
    )

    best_val_iou = -1.0

    # ========================================================
    # 12. HISTORY
    # ========================================================

    history: Dict[str, List[float]] = {

        "train_loss": [],
        "val_loss": [],

        "val_iou": [],
        "val_dice": [],

        "val_precision": [],
        "val_recall": [],
        "val_f1": [],

        "val_pixel_accuracy": [],

        "learning_rate": []
    }

    # ========================================================
    # 13. TRAINING START
    # ========================================================

    print(
        "\n[INFO] Starting training loop...\n"
    )

    for epoch in range(
        1,
        epochs + 1
    ):

        # ====================================================
        # CURRENT LR
        # ====================================================

        current_lr = optimizer.param_groups[0]["lr"]

        # ====================================================
        # TRAINING
        # ====================================================

        model.train()

        running_train_loss = 0.0

        train_bar = tqdm(
            train_loader,
            desc=(
                f"Epoch {epoch:02d}/{epochs:02d} [Train]"
            ),
            leave=False,
            bar_format=(
                "{l_bar}{bar:25}{r_bar}"
            )
        )

        for images, masks in train_bar:

            images = images.to(
                device,
                non_blocking=True
            )

            masks = masks.to(
                device,
                non_blocking=True
            )

            optimizer.zero_grad(
                set_to_none=True
            )

            # ------------------------------------------------
            # FORWARD PASS
            # ------------------------------------------------

            with torch.amp.autocast(
                device_type=device.type,
                enabled=use_amp
            ):

                logits = model(images)

                loss = criterion(
                    logits,
                    masks
                )

            # ------------------------------------------------
            # BACKWARD PASS
            # ------------------------------------------------

            if use_amp:

                scaler.scale(loss).backward()

                scaler.unscale_(optimizer)

                torch.nn.utils.clip_grad_norm_(
                    model.parameters(),
                    max_norm=grad_clip_norm
                )

                scaler.step(optimizer)

                scaler.update()

            else:

                loss.backward()

                torch.nn.utils.clip_grad_norm_(
                    model.parameters(),
                    max_norm=grad_clip_norm
                )

                optimizer.step()

            # ------------------------------------------------
            # LOSS
            # ------------------------------------------------

            running_train_loss += (
                loss.item() *
                images.size(0)
            )

            train_bar.set_postfix(
                loss=f"{loss.item():.4f}"
            )

        epoch_train_loss = (
            running_train_loss /
            len(train_loader.dataset)
        )

        # ====================================================
        # VALIDATION
        # ====================================================

        model.eval()

        running_val_loss = 0.0

        val_preds_list = []
        val_targets_list = []

        val_bar = tqdm(
            val_loader,
            desc=(
                f"Epoch {epoch:02d}/{epochs:02d} [Valid]"
            ),
            leave=False,
            bar_format=(
                "{l_bar}{bar:25}{r_bar}"
            )
        )

        with torch.no_grad():

            for images, masks in val_bar:

                images = images.to(
                    device,
                    non_blocking=True
                )

                masks = masks.to(
                    device,
                    non_blocking=True
                )

                with torch.amp.autocast(
                    device_type=device.type,
                    enabled=use_amp
                ):

                    logits = model(images)

                    loss = criterion(
                        logits,
                        masks
                    )

                running_val_loss += (
                    loss.item() *
                    images.size(0)
                )

                val_preds_list.append(
                    logits.float().cpu()
                )

                val_targets_list.append(
                    masks.float().cpu()
                )

        epoch_val_loss = (
            running_val_loss /
            len(val_loader.dataset)
        )

        # ====================================================
        # METRICS
        # ====================================================

        all_preds = torch.cat(
            val_preds_list,
            dim=0
        )

        all_targets = torch.cat(
            val_targets_list,
            dim=0
        )

        val_metrics = calculate_all_metrics(
            all_preds,
            all_targets
        )

        # ====================================================
        # PRINT CURRENT EPOCH
        # ====================================================

        print()

        print(
            f"Epoch [{epoch:02d}/{epochs:02d}] "
            f"LR: {current_lr:.8f}"
        )

        print(
            f"  Training Loss   : "
            f"{epoch_train_loss:.4f}"
        )

        print(
            f"  Validation Loss : "
            f"{epoch_val_loss:.4f}"
        )

        print(
            f"  IoU             : "
            f"{val_metrics['iou']:.4f}"
        )

        print(
            f"  Dice            : "
            f"{val_metrics['dice']:.4f}"
        )

        print(
            f"  Precision       : "
            f"{val_metrics['precision']:.4f}"
        )

        print(
            f"  Recall          : "
            f"{val_metrics['recall']:.4f}"
        )

        print(
            f"  F1              : "
            f"{val_metrics['f1']:.4f}"
        )

        print(
            f"  Pixel Accuracy  : "
            f"{val_metrics['pixel_accuracy']:.4f}"
        )

        # ====================================================
        # SAVE HISTORY
        # ====================================================

        history["train_loss"].append(
            epoch_train_loss
        )

        history["val_loss"].append(
            epoch_val_loss
        )

        history["val_iou"].append(
            val_metrics["iou"]
        )

        history["val_dice"].append(
            val_metrics["dice"]
        )

        history["val_precision"].append(
            val_metrics["precision"]
        )

        history["val_recall"].append(
            val_metrics["recall"]
        )

        history["val_f1"].append(
            val_metrics["f1"]
        )

        history["val_pixel_accuracy"].append(
            val_metrics["pixel_accuracy"]
        )

        history["learning_rate"].append(
            current_lr
        )

        # ====================================================
        # TENSORBOARD
        # ====================================================

        writer.add_scalar(
            "Loss/Train",
            epoch_train_loss,
            epoch
        )

        writer.add_scalar(
            "Loss/Validation",
            epoch_val_loss,
            epoch
        )

        writer.add_scalar(
            "Metrics/IoU",
            val_metrics["iou"],
            epoch
        )

        writer.add_scalar(
            "Metrics/Dice",
            val_metrics["dice"],
            epoch
        )

        writer.add_scalar(
            "Metrics/Precision",
            val_metrics["precision"],
            epoch
        )

        writer.add_scalar(
            "Metrics/Recall",
            val_metrics["recall"],
            epoch
        )

        writer.add_scalar(
            "Metrics/F1",
            val_metrics["f1"],
            epoch
        )

        writer.add_scalar(
            "Metrics/PixelAccuracy",
            val_metrics["pixel_accuracy"],
            epoch
        )

        writer.add_scalar(
            "LearningRate",
            current_lr,
            epoch
        )

        # ====================================================
        # BEST MODEL
        # ====================================================

        if val_metrics["iou"] > best_val_iou:

            best_val_iou = val_metrics["iou"]

            model.save_model(
                best_model_file
            )

            print(
                f"  [CHECKPOINT] New best "
                f"validation IoU "
                f"({best_val_iou:.4f})"
            )

            print(
                f"  Saved: "
                f"{best_model_file}"
            )

        # ====================================================
        # LAST MODEL
        # ====================================================

        model.save_model(
            last_model_file
        )

        print(
            f"  [CHECKPOINT] Last model saved"
        )

        # ====================================================
        # STEP SCHEDULER
        # ====================================================

        scheduler.step()

        next_lr = optimizer.param_groups[0]["lr"]

        print(
            f"  Next Epoch LR   : "
            f"{next_lr:.8f}"
        )

        print("-" * 50)

        # ====================================================
        # EARLY STOPPING
        # ====================================================

        if early_stopper(
            val_metrics["iou"]
        ):

            print(
                "\n[EARLY STOPPING]"
            )

            print(
                f"Validation IoU did not improve "
                f"for {patience} epochs."
            )

            break

        # ====================================================
        # CUDA MEMORY CLEANUP
        # ====================================================

        if device.type == "cuda":

            torch.cuda.empty_cache()

    # ========================================================
    # CLOSE TENSORBOARD
    # ========================================================

    writer.close()

    # ========================================================
    # SAVE JSON
    # ========================================================

    with open(
        log_json_file,
        "w"
    ) as f:

        json.dump(
            history,
            f,
            indent=4
        )

    print(
        f"\n[SUCCESS] Saved training log to:"
    )

    print(
        f"{log_json_file}"
    )

    # ========================================================
    # SAVE GRAPHS
    # ========================================================

    save_training_graphs(
        history,
        output_path
    )

    # ========================================================
    # FINAL OUTPUT
    # ========================================================

    print("\n")
    print("=" * 50)
    print(
        "      TRAINING PIPELINE COMPLETED SUCCESSFULLY!"
    )
    print("=" * 50)

    print(
        f"Best Validation IoU: "
        f"{best_val_iou:.4f}"
    )

    print(
        f"Best Model Weights : "
        f"{best_model_file}"
    )

    print(
        f"Last Model Weights : "
        f"{last_model_file}"
    )

    return history


# ============================================================
# COMMAND LINE
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Train U-Net Model for "
            "Disaster Road Mapping"
        )
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=20,
        help="Number of training epochs"
    )

    parser.add_argument(
        "--batch_size",
        type=int,
        default=2,
        help="Batch size per training step"
    )

    parser.add_argument(
        "--lr",
        type=float,
        default=1e-4,
        help="AdamW learning rate"
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed"
    )

    parser.add_argument(
        "--patience",
        type=int,
        default=7,
        help="Early stopping patience"
    )

    args = parser.parse_args()

    train_model(
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        seed=args.seed,
        patience=args.patience
    )