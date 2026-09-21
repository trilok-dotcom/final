import sys
from pathlib import Path
from typing import Dict, Union, Tuple
import torch
import numpy as np

# Ensure backend directory is in sys.path for standalone module execution
AI_DIR = Path(__file__).resolve().parent
BACKEND_DIR = AI_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _prepare_binary_tensors(
    preds: Union[torch.Tensor, np.ndarray],
    targets: Union[torch.Tensor, np.ndarray],
    threshold: float = 0.5,
    from_logits: bool = True,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Helper utility to process and binarize input predictions and targets into 1D PyTorch float tensors.

    Args:
        preds (Tensor | ndarray): Predicted logits, probabilities, or binary masks.
        targets (Tensor | ndarray): Ground truth binary mask tensor or array.
        threshold (float): Decision threshold for binary classification. Default 0.5.
        from_logits (bool): If True, applies sigmoid to raw logits before thresholding. Default True.

    Returns:
        Tuple[torch.Tensor, torch.Tensor]: Flattened binary tensors (0.0 or 1.0) for predictions and targets.
    """
    if not isinstance(preds, torch.Tensor):
        preds = torch.from_numpy(np.asarray(preds))
    if not isinstance(targets, torch.Tensor):
        targets = torch.from_numpy(np.asarray(targets))

    # Detach and convert to float
    preds = preds.detach().cpu().float()
    targets = targets.detach().cpu().float()

    if from_logits:
        preds = torch.sigmoid(preds)

    preds_bin = (preds > threshold).float().view(-1)
    targets_bin = (targets > threshold).float().view(-1)

    return preds_bin, targets_bin


def calculate_iou(
    preds: Union[torch.Tensor, np.ndarray],
    targets: Union[torch.Tensor, np.ndarray],
    threshold: float = 0.5,
    eps: float = 1e-7,
    from_logits: bool = True,
) -> float:
    """Calculate Intersection over Union (IoU / Jaccard Index) for binary segmentation.

    Args:
        preds: Predicted model logits or probability map.
        targets: Ground truth binary mask tensor.
        threshold: Binarization decision threshold. Default 0.5.
        eps: Epsilon smoothing value for numerical stability. Default 1e-7.
        from_logits: Whether preds are raw unnormalized logits. Default True.

    Returns:
        float: IoU score between 0.0 and 1.0.
    """
    preds_bin, targets_bin = _prepare_binary_tensors(
        preds, targets, threshold=threshold, from_logits=from_logits
    )
    intersection = (preds_bin * targets_bin).sum().item()
    union = preds_bin.sum().item() + targets_bin.sum().item() - intersection
    return (intersection + eps) / (union + eps)


def calculate_dice(
    preds: Union[torch.Tensor, np.ndarray],
    targets: Union[torch.Tensor, np.ndarray],
    threshold: float = 0.5,
    eps: float = 1e-7,
    from_logits: bool = True,
) -> float:
    """Calculate Dice Coefficient (F1 Score equivalent for spatial overlap).

    Args:
        preds: Predicted model logits or probability map.
        targets: Ground truth binary mask tensor.
        threshold: Binarization decision threshold. Default 0.5.
        eps: Epsilon smoothing value for numerical stability. Default 1e-7.
        from_logits: Whether preds are raw unnormalized logits. Default True.

    Returns:
        float: Dice score between 0.0 and 1.0.
    """
    preds_bin, targets_bin = _prepare_binary_tensors(
        preds, targets, threshold=threshold, from_logits=from_logits
    )
    intersection = (preds_bin * targets_bin).sum().item()
    total = preds_bin.sum().item() + targets_bin.sum().item()
    return (2.0 * intersection + eps) / (total + eps)


def calculate_pixel_accuracy(
    preds: Union[torch.Tensor, np.ndarray],
    targets: Union[torch.Tensor, np.ndarray],
    threshold: float = 0.5,
    from_logits: bool = True,
) -> float:
    """Calculate overall pixel classification accuracy.

    Args:
        preds: Predicted model logits or probability map.
        targets: Ground truth binary mask tensor.
        threshold: Binarization decision threshold. Default 0.5.
        from_logits: Whether preds are raw unnormalized logits. Default True.

    Returns:
        float: Pixel accuracy ratio between 0.0 and 1.0.
    """
    preds_bin, targets_bin = _prepare_binary_tensors(
        preds, targets, threshold=threshold, from_logits=from_logits
    )
    correct = (preds_bin == targets_bin).float().sum().item()
    total_pixels = preds_bin.numel()
    return correct / total_pixels if total_pixels > 0 else 0.0


def calculate_precision(
    preds: Union[torch.Tensor, np.ndarray],
    targets: Union[torch.Tensor, np.ndarray],
    threshold: float = 0.5,
    eps: float = 1e-7,
    from_logits: bool = True,
) -> float:
    """Calculate Precision (True Positives / (True Positives + False Positives)).

    Args:
        preds: Predicted model logits or probability map.
        targets: Ground truth binary mask tensor.
        threshold: Binarization decision threshold. Default 0.5.
        eps: Epsilon smoothing value for numerical stability. Default 1e-7.
        from_logits: Whether preds are raw unnormalized logits. Default True.

    Returns:
        float: Precision score between 0.0 and 1.0.
    """
    preds_bin, targets_bin = _prepare_binary_tensors(
        preds, targets, threshold=threshold, from_logits=from_logits
    )
    tp = (preds_bin * targets_bin).sum().item()
    fp = (preds_bin * (1.0 - targets_bin)).sum().item()
    return (tp + eps) / (tp + fp + eps)


def calculate_recall(
    preds: Union[torch.Tensor, np.ndarray],
    targets: Union[torch.Tensor, np.ndarray],
    threshold: float = 0.5,
    eps: float = 1e-7,
    from_logits: bool = True,
) -> float:
    """Calculate Recall / Sensitivity (True Positives / (True Positives + False Negatives)).

    Args:
        preds: Predicted model logits or probability map.
        targets: Ground truth binary mask tensor.
        threshold: Binarization decision threshold. Default 0.5.
        eps: Epsilon smoothing value for numerical stability. Default 1e-7.
        from_logits: Whether preds are raw unnormalized logits. Default True.

    Returns:
        float: Recall score between 0.0 and 1.0.
    """
    preds_bin, targets_bin = _prepare_binary_tensors(
        preds, targets, threshold=threshold, from_logits=from_logits
    )
    tp = (preds_bin * targets_bin).sum().item()
    fn = ((1.0 - preds_bin) * targets_bin).sum().item()
    return (tp + eps) / (tp + fn + eps)


def calculate_f1(
    preds: Union[torch.Tensor, np.ndarray],
    targets: Union[torch.Tensor, np.ndarray],
    threshold: float = 0.5,
    eps: float = 1e-7,
    from_logits: bool = True,
) -> float:
    """Calculate F1 Score (Harmonic mean of Precision and Recall).

    Args:
        preds: Predicted model logits or probability map.
        targets: Ground truth binary mask tensor.
        threshold: Binarization decision threshold. Default 0.5.
        eps: Epsilon smoothing value for numerical stability. Default 1e-7.
        from_logits: Whether preds are raw unnormalized logits. Default True.

    Returns:
        float: F1 score between 0.0 and 1.0.
    """
    prec = calculate_precision(
        preds, targets, threshold=threshold, eps=eps, from_logits=from_logits
    )
    rec = calculate_recall(
        preds, targets, threshold=threshold, eps=eps, from_logits=from_logits
    )
    return (2.0 * prec * rec + eps) / (prec + rec + eps)


def calculate_all_metrics(
    preds: Union[torch.Tensor, np.ndarray],
    targets: Union[torch.Tensor, np.ndarray],
    threshold: float = 0.5,
    eps: float = 1e-7,
    from_logits: bool = True,
) -> Dict[str, float]:
    """Compute all 6 binary segmentation evaluation metrics in a single efficient pass.

    Returns dictionary containing keys:
    - 'iou'
    - 'dice'
    - 'pixel_accuracy'
    - 'precision'
    - 'recall'
    - 'f1'
    """
    preds_bin, targets_bin = _prepare_binary_tensors(
        preds, targets, threshold=threshold, from_logits=from_logits
    )

    tp = (preds_bin * targets_bin).sum().item()
    fp = (preds_bin * (1.0 - targets_bin)).sum().item()
    fn = ((1.0 - preds_bin) * targets_bin).sum().item()
    tn = ((1.0 - preds_bin) * (1.0 - targets_bin)).sum().item()

    total_pixels = preds_bin.numel()

    iou = (tp + eps) / (tp + fp + fn + eps)
    dice = (2.0 * tp + eps) / (2.0 * tp + fp + fn + eps)
    pixel_acc = (tp + tn) / total_pixels if total_pixels > 0 else 0.0
    prec = (tp + eps) / (tp + fp + eps)
    rec = (tp + eps) / (tp + fn + eps)
    f1 = (2.0 * prec * rec + eps) / (prec + rec + eps)

    return {
        "iou": iou,
        "dice": dice,
        "pixel_accuracy": pixel_acc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
    }


if __name__ == "__main__":
    print("==================================================")
    print("      RESQROUTE AI - Binary Segmentation Metrics  ")
    print("==================================================")

    dummy_pred = torch.randn(2, 1, 512, 512)
    dummy_target = torch.randint(0, 2, (2, 1, 512, 512)).float()

    metrics = calculate_all_metrics(dummy_pred, dummy_target)

    for metric_name, val in metrics.items():
        print(f" - {metric_name.replace('_', ' ').title():<18}: {val:.4f}")

    print("\n[SUCCESS] All binary segmentation metrics verified successfully!")
