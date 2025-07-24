"""Image preprocessing utilities (grayscale, CLAHE, threshold, deskew)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from loguru import logger


@dataclass
class PreprocessCfg:
    clahe_clip: float = 2.0
    clahe_grid: int = 8
    adaptive_block_size: int = 51  # must be odd
    adaptive_C: int = 2
    deskew: bool = True


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _deskew(image: np.ndarray) -> np.ndarray:
    coords = np.column_stack(np.where(image < 255))
    if coords.size == 0:
        return image  # blank page

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )

    logger.debug(f"Deskewed by {angle:.2f}°")
    return rotated


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_and_enhance(
    img_path: str | Path, cfg: PreprocessCfg | dict[str, Any] | None = None
) -> np.ndarray:  # noqa: D401
    """Load image at *img_path* and apply preprocessing pipeline."""

    if cfg is None:
        cfg = PreprocessCfg()
    elif isinstance(cfg, dict):
        cfg = PreprocessCfg(**cfg)

    img_path = Path(img_path)
    gray = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise FileNotFoundError(f"Could not load image: {img_path}")

    logger.debug(f"Processing {img_path.name} – shape={gray.shape}")

    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=cfg.clahe_clip, tileGridSize=(cfg.clahe_grid, cfg.clahe_grid))
    enhanced = clahe.apply(gray)

    # Adaptive threshold
    block_size = cfg.adaptive_block_size | 1  # ensure odd
    binary = cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        cfg.adaptive_C,
    )

    if cfg.deskew:
        binary = _deskew(binary)

    return binary
