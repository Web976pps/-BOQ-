"""Validation utilities for spatial assignments and code extraction quality."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import List, Dict, Any

import numpy as np
from loguru import logger

__all__ = ["run"]


def run(rows: List[Dict[str, Any]], zones: List[Dict[str, Any]], cfg: Dict[str, Any] | None = None) -> Dict[str, Any]:  # noqa: D401
    """Produce validation summary.

    Parameters
    ----------
    rows
        Normalised rows with zone assignment.
    zones
        List of zone dicts.
    cfg
        Optional validation config (not yet used).
    """

    # Zones without codes
    zone_names_with_codes = {r["zone"] for r in rows if r.get("zone") and r["zone"] != "__UNASSIGNED__"}
    all_zone_names = {z["zone"] for z in zones}

    zones_without_codes = sorted(all_zone_names - zone_names_with_codes)

    # Unassigned codes
    unassigned_codes = [r for r in rows if r.get("zone") == "__UNASSIGNED__"]

    # Conflicts: code appears in >1 zone (pre-dedup we might not detect); compute clusters
    code_to_zones = defaultdict(set)
    for r in rows:
        code_to_zones[r["code"]].add(r["zone"])
    conflicts = {c: list(zs) for c, zs in code_to_zones.items() if len(zs) > 1}

    # Confidence statistics
    confs = [r["conf"] for r in rows if "conf" in r]
    conf_stats = {
        "mean": float(np.mean(confs)) if confs else None,
        "median": float(np.median(confs)) if confs else None,
        "min": float(min(confs)) if confs else None,
        "max": float(max(confs)) if confs else None,
    }

    report = {
        "zones_without_codes": zones_without_codes,
        "unassigned_codes": [c["code"] for c in unassigned_codes],
        "conflicts": conflicts,
        "conf_stats": conf_stats,
    }

    logger.info(
        f"Validation » zones_without_codes={len(zones_without_codes)} unassigned={len(unassigned_codes)} conflicts={len(conflicts)}"
    )

    return report 