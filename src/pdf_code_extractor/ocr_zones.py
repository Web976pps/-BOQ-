"""Zone detection via Tesseract OCR.

Detects ALL-CAPS text (e.g., drawing zones) and returns bounding-boxes with
confidence scores.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any

import cv2
import numpy as np
import pytesseract
from loguru import logger

__all__ = ["ZonesCfg", "detect"]


@dataclass(slots=True)
class ZonesCfg:
    """Configuration parameters controlling zone detection."""

    blacklist: set[str] = field(
        default_factory=lambda: {
            "NOTES",
            "SCALE",
            "REVISION",
            "TITLE",
            "DRAWING",
            "SHEET",
        }
    )
    min_height_percentile: float = 60.0  # discard words shorter than this percentile
    psm: int = 11  # sparse text


def _is_all_caps(token: str) -> bool:
    return token.isupper() and token.upper() == token and any(c.isalpha() for c in token)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect(img: np.ndarray, page_num: int, cfg: ZonesCfg | None = None) -> List[Dict[str, Any]]:  # noqa: D401
    """Detect ALL-CAPS zones in *img*.

    Returns list of dicts with: page, bbox(x,y,w,h), conf, zone
    """

    if cfg is None:
        cfg = ZonesCfg()

    tess_config = f"--psm {cfg.psm} -c tessedit_char_blacklist=0123456789"  # focus on text

    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config=tess_config)
    n = len(data["text"])

    heights = [data["height"][i] for i in range(n) if _is_all_caps(data["text"][i].strip())]
    if not heights:
        return []
    threshold = np.percentile(heights, cfg.min_height_percentile)

    results: List[Dict[str, Any]] = []
    for i in range(n):
        text = data["text"][i].strip()
        if not text:
            continue
        if not _is_all_caps(text):
            continue
        if text in cfg.blacklist:
            continue
        h = data["height"][i]
        if h < threshold:
            continue
        conf = float(data["conf"][i]) if data["conf"][i] != "-1" else 0.0
        bbox = (data["left"][i], data["top"][i], data["width"][i], data["height"][i])
        results.append({
            "page": page_num,
            "bbox": bbox,
            "conf": conf,
            "zone": text,
        })

    logger.debug(f"Detected {len(results)} zones on page {page_num}")
    return results 