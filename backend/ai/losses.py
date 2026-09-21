import sys
from pathlib import Path
from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F

# Ensure backend directory is in sys.path for standalone module execution
AI_DIR = Path(__file__).resolve().parent
BACKEND_DIR = AI_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class DiceLoss(nn.Module):
    """Dice Loss for binary image segmentation.

    Computes 1 - Dice Coefficient. Supports raw unnormalized logits or probabilities.

    Args:
        smooth (float): Smoothing factor to prevent division by zero. Default 1.0.
        from_logits (bool): If True, applies sigmoid function to input predictions. Default True.
    """

    def __init__(self, smooth: float = 1.0, from_logits: bool = True) -> None:
        super().__init__()
        self.smooth = smooth
        self.from_logits = from_logits

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        """Forward pass for Dice Loss.

        Args:
            pred (torch.Tensor): Predicted logits or probabilities of shape (B, 1, H, W) or (B, H, W).
            target (torch.Tensor): Ground truth binary mask tensor of shape (B, 1, H, W) or (B, H, W).

        Returns:
            torch.Tensor: Scalar Dice loss.
        """
        if self.from_logits:
            pred = torch.sigmoid(pred)

        # Flatten predictions and target masks
        pred_flat = pred.view(-1)
        target_flat = target.view(-1)

        intersection = (pred_flat * target_flat).sum()
        total = pred_flat.sum() + target_flat.sum()

        dice_score = (2.0 * intersection + self.smooth) / (total + self.smooth)
        return 1.0 - dice_score


class BCEWithLogitsLoss(nn.Module):
    """Binary Cross Entropy Loss with Logits wrapper for semantic segmentation.

    Args:
        pos_weight (Optional[torch.Tensor]): Weight for positive class to handle class imbalance.
    """

    def __init__(self, pos_weight: Optional[torch.Tensor] = None) -> None:
        super().__init__()
        self.loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        """Forward pass for BCEWithLogitsLoss.

        Args:
            pred (torch.Tensor): Raw model output logits.
            target (torch.Tensor): Ground truth binary mask tensor (float).

        Returns:
            torch.Tensor: Scalar BCE loss value.
        """
        # Ensure target matches pred dtype and dimensions
        if target.shape != pred.shape:
            target = target.view_as(pred)
        return self.loss_fn(pred, target.float())


class CombinedLoss(nn.Module):
    """Configurable Combined Loss (Dice Loss + BCEWithLogitsLoss) for Binary Road Segmentation.

    Combines smooth boundary optimization (Dice) with pixel-level classification (BCE).

    Args:
        dice_weight (float): Weight multiplier for Dice Loss. Default 1.0.
        bce_weight (float): Weight multiplier for BCE Loss. Default 1.0.
        smooth (float): Smoothing factor for Dice Loss calculation. Default 1.0.
        pos_weight (Optional[torch.Tensor]): Optional positive class weighting for BCE loss.
    """

    def __init__(
        self,
        dice_weight: float = 1.0,
        bce_weight: float = 1.0,
        smooth: float = 1.0,
        pos_weight: Optional[torch.Tensor] = None,
    ) -> None:
        super().__init__()
        self.dice_weight = dice_weight
        self.bce_weight = bce_weight
        self.dice_loss = DiceLoss(smooth=smooth, from_logits=True)
        self.bce_loss = BCEWithLogitsLoss(pos_weight=pos_weight)

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        """Calculate weighted sum of Dice and BCE loss components.

        Args:
            pred (torch.Tensor): Output logits from model.
            target (torch.Tensor): Target ground truth mask tensor.

        Returns:
            torch.Tensor: Combined scalar loss.
        """
        l_dice = self.dice_loss(pred, target)
        l_bce = self.bce_loss(pred, target)
        return (self.dice_weight * l_dice) + (self.bce_weight * l_bce)


if __name__ == "__main__":
    print("==================================================")
    print("      RESQROUTE AI - Loss Functions Test          ")
    print("==================================================")

    dummy_pred = torch.randn(2, 1, 512, 512)
    dummy_target = torch.randint(0, 2, (2, 1, 512, 512)).float()

    dice_fn = DiceLoss()
    bce_fn = BCEWithLogitsLoss()
    combined_fn = CombinedLoss(dice_weight=1.0, bce_weight=1.0)

    loss_d = dice_fn(dummy_pred, dummy_target)
    loss_b = bce_fn(dummy_pred, dummy_target)
    loss_c = combined_fn(dummy_pred, dummy_target)

    print(f"Dice Loss      : {loss_d.item():.4f}")
    print(f"BCE Loss       : {loss_b.item():.4f}")
    print(f"Combined Loss  : {loss_c.item():.4f}")
    print("[SUCCESS] All loss functions verified successfully!")
