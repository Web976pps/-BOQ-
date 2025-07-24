"""Configuration loader using Pydantic models."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class RasterConfig(BaseModel):
    """Settings controlling PDF rasterisation."""

    dpi: int = Field(300, gt=0)
    engine: Literal["pdftoppm", "ghostscript", "pymupdf", "auto"] = "auto"


class PreprocessConfig(BaseModel):
    """Settings controlling image preprocessing parameters."""

    clahe_clip: float = Field(2.0, ge=0)
    clahe_grid: int = Field(8, gt=0)
    adaptive_block_size: int = Field(51, gt=1)
    adaptive_C: int = 2
    deskew: bool = True


class DBSCANConfig(BaseModel):
    eps_mm: float = 2.0
    min_samples: int = 1


class SpatialConfig(BaseModel):
    strategy: Literal["dbscan", "voronoi"] = "dbscan"
    dbscan: DBSCANConfig = DBSCANConfig()
    max_assign_dist_mm: float = 20.0
    zone_buffer_mm: float = 0.0


class AppConfig(BaseModel):
    """Top-level application config schema."""

    raster: RasterConfig = RasterConfig()
    preprocess: PreprocessConfig = PreprocessConfig()
    spatial: SpatialConfig = SpatialConfig()


DEFAULT_CONFIG = AppConfig()


def load_config(yml_path: str | Path | None = None) -> AppConfig:  # noqa: D401
    """Load configuration file.

    If *yml_path* is *None*, a default config is returned. Otherwise, the YAML
    file is read and validated against the :class:`AppConfig` schema.
    """

    if yml_path is None:
        return DEFAULT_CONFIG

    path = Path(yml_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {yml_path}")

    with path.open("r", encoding="utf-8") as fh:
        payload = yaml.safe_load(fh) or {}

    return AppConfig(**payload) 