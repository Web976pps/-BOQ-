"""Spatial association of codes to zones.

This module assigns every *code* token to exactly one *zone* token on the same
page using either DBSCAN clustering or Voronoi partitioning.

The output preserves the original `code` dict structure and enriches it with:
    - zone (str | "__UNASSIGNED__")
    - distance_px (float | None)
    - strategy_used (str)

It also returns a *SpatialReport* summarising assignment quality.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from loguru import logger
from scipy.spatial import Voronoi
from shapely.geometry import Point, Polygon, box
from sklearn.cluster import DBSCAN

__all__ = [
    "to_mm",
    "to_px",
    "assign",
    "CodeToken",
    "ZoneToken",
    "SpatialCfg",
    "DBSCANCfg",
    "SpatialReport",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def to_mm(px: float, dpi: int) -> float:  # noqa: D401
    """Convert pixels to millimetres."""
    return px * 25.4 / dpi


def to_px(mm: float, dpi: int) -> float:  # noqa: D401
    """Convert millimetres to pixels."""
    return mm * dpi / 25.4


# ---------------------------------------------------------------------------
# Token data structures
# ---------------------------------------------------------------------------


def _centroid(bbox: tuple[int, int, int, int]) -> tuple[float, float]:
    x, y, w, h = bbox
    return (x + w / 2.0, y + h / 2.0)


def _area(bbox: tuple[int, int, int, int]) -> int:
    _, _, w, h = bbox
    return w * h


@dataclass(slots=True)
class ZoneToken:
    page: int
    bbox: tuple[int, int, int, int]
    conf: float
    zone: str

    centroid: tuple[float, float] = field(init=False)
    area: int = field(init=False)

    def __post_init__(self) -> None:
        self.centroid = _centroid(self.bbox)
        self.area = _area(self.bbox)


@dataclass(slots=True)
class CodeToken:
    page: int
    bbox: tuple[int, int, int, int]
    conf: float
    code: str
    prefix: str

    centroid: tuple[float, float] = field(init=False)

    # Enriched later
    zone: str | None = None
    distance_px: float | None = None
    strategy_used: str | None = None
    cluster_id: int | None = None

    def __post_init__(self) -> None:
        self.centroid = _centroid(self.bbox)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class DBSCANCfg:
    eps_mm: float = 2.0
    min_samples: int = 1


@dataclass(slots=True)
class SpatialCfg:
    dpi: int = 300
    strategy: str = "dbscan"  # dbscan | voronoi
    dbscan: DBSCANCfg = field(default_factory=DBSCANCfg)

    max_assign_dist_mm: float = 20.0  # fallback for voronoi
    zone_buffer_mm: float = 0.0  # expand zone polygons

    prefer_smaller_zone_area: bool = True  # tie-break rule 2


@dataclass(slots=True)
class SpatialReport:
    strategy: str
    assigned: int
    unassigned: int
    clusters: int
    mean_distance_px: float | None
    median_distance_px: float | None

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


# ---------------------------------------------------------------------------
# Tie-breaker util
# ---------------------------------------------------------------------------


def _select_zone(candidates: list[ZoneToken], distance_fn) -> ZoneToken:
    """Apply deterministic tie-breakers to choose one zone among *candidates*.

    *distance_fn* returns the distance from zone centroid to the code (or cluster cent.)
    """

    # 1) Minimum distance already ensured by caller providing candidate list with minimal dist
    best = candidates[0]
    best_dist = distance_fn(best)

    # filter same distance within 1e-6
    same_dist = [z for z in candidates if abs(distance_fn(z) - best_dist) < 1e-6]
    if len(same_dist) == 1:
        return best

    # 1) Highest zone OCR confidence
    max_conf = max(z.conf for z in same_dist)
    conf_filtered = [z for z in same_dist if z.conf == max_conf]
    if len(conf_filtered) == 1:
        return conf_filtered[0]

    # 2) Smallest / largest area based on cfg? Not available here; we'll default smaller.
    min_area = min(z.area for z in conf_filtered)
    area_filtered = [z for z in conf_filtered if z.area == min_area]
    if len(area_filtered) == 1:
        return area_filtered[0]

    # 3) Lexicographically smallest zone name
    return sorted(area_filtered, key=lambda z: z.zone)[0]


# ---------------------------------------------------------------------------
# Core assignment
# ---------------------------------------------------------------------------


def assign(
    zones: list[dict[str, Any]],
    codes: list[dict[str, Any]],
    cfg: SpatialCfg | dict[str, Any] | None = None,
) -> tuple[list[CodeToken], SpatialReport]:  # noqa: D401
    """Assign *codes* to *zones* following *cfg* strategy.

    Returns (*enriched_codes*, *report*)
    """

    if cfg is None:
        cfg = SpatialCfg()
    elif isinstance(cfg, dict):
        # naive parse; only top-level necessary keys
        cfg = SpatialCfg(
            dpi=cfg.get("dpi", 300),
            strategy=cfg.get("strategy", "dbscan"),
            dbscan=DBSCANCfg(**cfg.get("dbscan", {})),
            max_assign_dist_mm=cfg.get("max_assign_dist_mm", 20.0),
            zone_buffer_mm=cfg.get("zone_buffer_mm", 0.0),
            prefer_smaller_zone_area=cfg.get("prefer_smaller_zone_area", True),
        )

    dpi = cfg.dpi

    # Convert to token objects
    zone_tokens = [ZoneToken(**z) for z in zones]
    code_tokens = [CodeToken(**c) for c in codes]

    # Index by page
    pages = sorted({t.page for t in code_tokens})

    for page in pages:
        page_zones = [z for z in zone_tokens if z.page == page]
        page_codes = [c for c in code_tokens if c.page == page]

        if not page_zones:
            for c in page_codes:
                c.zone = "__UNASSIGNED__"
                c.strategy_used = cfg.strategy
                c.distance_px = None
            continue

        if cfg.strategy == "dbscan":
            _assign_dbscan(page_zones, page_codes, cfg)
        elif cfg.strategy == "voronoi":
            _assign_voronoi(page_zones, page_codes, cfg)
        else:
            raise ValueError(f"Unknown spatial strategy: {cfg.strategy}")

    # Build report
    assigned = sum(c.zone != "__UNASSIGNED__" for c in code_tokens)
    unassigned = len(code_tokens) - assigned
    distances = [c.distance_px for c in code_tokens if c.distance_px is not None]
    mean_dist = float(np.mean(distances)) if distances else None
    median_dist = float(np.median(distances)) if distances else None

    # clusters count only for dbscan else len(zones)
    clusters = (
        len(set(c.cluster_id for c in code_tokens if c.cluster_id is not None))
        if cfg.strategy == "dbscan"
        else len(zone_tokens)
    )

    report = SpatialReport(
        strategy=cfg.strategy,
        assigned=assigned,
        unassigned=unassigned,
        clusters=clusters,
        mean_distance_px=mean_dist,
        median_distance_px=median_dist,
    )

    logger.info(
        f"Spatial assign » strategy={cfg.strategy} assigned={assigned}/{len(code_tokens)} mean_dist_px={mean_dist}"
    )

    # Return list in original order to maintain determinism
    return code_tokens, report


# ---------------------------------------------------------------------------
# Strategy implementations
# ---------------------------------------------------------------------------


def _assign_dbscan(
    page_zones: list[ZoneToken], page_codes: list[CodeToken], cfg: SpatialCfg
) -> None:
    eps_px = to_px(cfg.dbscan.eps_mm, cfg.dpi)

    coords = np.array([c.centroid for c in page_codes])
    clustering = DBSCAN(eps=eps_px, min_samples=cfg.dbscan.min_samples).fit(coords)
    labels = clustering.labels_

    # Assign cluster_id for all codes first
    for c, lbl in zip(page_codes, labels, strict=False):
        c.cluster_id = int(lbl)

    # Assign zones per-code based on individual distance to nearest zone.
    for c in page_codes:
        c.strategy_used = "dbscan"

        # Compute nearest zone(s) for this code
        dists = [math.dist(c.centroid, z.centroid) for z in page_zones]
        min_dist = min(dists)
        nearest_zones = [
            z for z, d in zip(page_zones, dists, strict=False) if abs(d - min_dist) < 1e-6
        ]

        if min_dist > eps_px:
            # Too far from any zone → unassigned
            c.zone = "__UNASSIGNED__"
            c.distance_px = None
        else:
            chosen_zone = _select_zone(nearest_zones, lambda z: math.dist(c.centroid, z.centroid))
            c.zone = chosen_zone.zone
            c.distance_px = min_dist


# ---------------------------------------------------------------------------


def _assign_voronoi(
    page_zones: list[ZoneToken], page_codes: list[CodeToken], cfg: SpatialCfg
) -> None:
    """Assign via Voronoi cells; fallback to nearest zone within `max_assign_dist_mm`."""

    # Construct Voronoi diagram from zone centroids
    points = np.array([z.centroid for z in page_zones])
    if len(points) < 2:
        # Voronoi undefined; fallback to nearest-zone assignment
        _assign_nearest(page_zones, page_codes, cfg)
        return

    vor = Voronoi(points)

    # Build page bounding box (large area), using max coordinates from codes and zones
    xs = [p[0] for p in points] + [c.centroid[0] for c in page_codes]
    ys = [p[1] for p in points] + [c.centroid[1] for c in page_codes]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    bounds = box(min_x, min_y, max_x, max_y)

    # Map region index to polygon
    region_polys: dict[int, Polygon] = {}
    for point_idx, region_idx in enumerate(vor.point_region):
        verts_idx = vor.regions[region_idx]
        if -1 in verts_idx or len(verts_idx) == 0:
            # Open region; skip -> fallback nearest later
            continue
        polygon = Polygon(vor.vertices[verts_idx])
        if cfg.zone_buffer_mm:
            buffer_px = to_px(cfg.zone_buffer_mm, cfg.dpi)
            polygon = polygon.buffer(buffer_px)
        polygon = polygon.intersection(bounds)
        region_polys[point_idx] = polygon

    max_assign_dist_px = to_px(cfg.max_assign_dist_mm, cfg.dpi)

    for c in page_codes:
        point = Point(c.centroid)
        assigned_zone: ZoneToken | None = None
        assigned_dist = None

        # Check polygons
        for idx, poly in region_polys.items():
            if poly.contains(point):
                z = page_zones[idx]
                assigned_zone = z
                assigned_dist = math.dist(c.centroid, z.centroid)
                break

        # Fallback to nearest zone within threshold
        if assigned_zone is None:
            dists = [math.dist(c.centroid, z.centroid) for z in page_zones]
            min_dist = min(dists)
            if min_dist <= max_assign_dist_px:
                nearest_zones = [
                    z for z, d in zip(page_zones, dists, strict=False) if abs(d - min_dist) < 1e-6
                ]
                assigned_zone = _select_zone(
                    nearest_zones, lambda z: math.dist(c.centroid, z.centroid)
                )
                assigned_dist = min_dist

        c.strategy_used = "voronoi"
        if assigned_zone is None:
            c.zone = "__UNASSIGNED__"
            c.distance_px = None
        else:
            c.zone = assigned_zone.zone
            c.distance_px = assigned_dist


# ---------------------------------------------------------------------------
# Nearest fallback
# ---------------------------------------------------------------------------


def _assign_nearest(
    page_zones: list[ZoneToken], page_codes: list[CodeToken], cfg: SpatialCfg
) -> None:
    """Simple nearest-zone assignment used when Voronoi cannot be constructed."""
    max_assign_px = to_px(cfg.max_assign_dist_mm, cfg.dpi)
    for c in page_codes:
        dists = [math.dist(c.centroid, z.centroid) for z in page_zones]
        min_dist = min(dists)
        if min_dist > max_assign_px:
            c.zone = "__UNASSIGNED__"
            c.distance_px = None
        else:
            nearest_zones = [
                z for z, d in zip(page_zones, dists, strict=False) if abs(d - min_dist) < 1e-6
            ]
            z = _select_zone(nearest_zones, lambda z: math.dist(c.centroid, z.centroid))
            c.zone = z.zone
            c.distance_px = min_dist
        c.strategy_used = "nearest"
