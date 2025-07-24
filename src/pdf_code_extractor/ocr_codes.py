"""Code detection via Tesseract OCR and regex filtering."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pytesseract
from loguru import logger

__all__ = ["CodesCfg", "normalise_code", "detect"]


_CODE_PATTERN = re.compile(r"\b(?:CH|TB|C|SU|KT)\s*-?\s*\d+(?:\s*[A-Za-z])?\b", re.IGNORECASE)


@dataclass(slots=True)
class CodesCfg:
    psm: int = 6  # assume uniform block
    pattern: re.Pattern[str] = field(default=_CODE_PATTERN, repr=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def normalise_code(raw: str) -> tuple[str, str]:
    """Return (*code*, *prefix*) in normalised form."""
    clean = re.sub(r"[\s-]+", "", raw).upper()
    # prefix is consecutive letters at start
    m = re.match(r"[A-Z]+", clean)
    prefix = m.group(0) if m else ""
    return clean, prefix


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect(
    img: np.ndarray, page_num: int, cfg: CodesCfg | None = None
) -> list[dict[str, Any]]:  # noqa: D401
    """Detect drawing codes matching regex pattern.

    Returns list of dicts with: page, bbox, conf, code, prefix
    """

    if cfg is None:
        cfg = CodesCfg()

    tess_config = f"--psm {cfg.psm}"

    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config=tess_config)
    n = len(data["text"])

    results: list[dict[str, Any]] = []
    for i in range(n):
        text = data["text"][i].strip()
        if not text:
            continue
        if not cfg.pattern.search(text):
            continue
        code, prefix = normalise_code(text)
        conf = float(data["conf"][i]) if data["conf"][i] != "-1" else 0.0
        bbox = (data["left"][i], data["top"][i], data["width"][i], data["height"][i])
        results.append(
            {
                "page": page_num,
                "bbox": bbox,
                "conf": conf,
                "code": code,
                "prefix": prefix,
            }
        )

    logger.debug(f"Detected {len(results)} codes on page {page_num}")
    return results
