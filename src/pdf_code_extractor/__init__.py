"""Top-level package for A1 PDF zones/codes extractor."""

__version__ = "0.1.0"
from .preprocess import PreprocessCfg  # noqa: F401 
from .ocr_zones import ZonesCfg  # noqa: F401
from .ocr_codes import CodesCfg, normalise_code  # noqa: F401 
from .spatial import SpatialCfg, DBSCANCfg, to_px, to_mm  # noqa: F401 
from .normalize import apply as normalize_apply  # noqa: F401
from .validate import run as validate_run  # noqa: F401
from .export import write_csvs, write_overlays  # noqa: F401 