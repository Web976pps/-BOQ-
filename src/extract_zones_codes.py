"""CLI entry point for A1 PDF zones & codes extraction."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from loguru import logger
from pdf_code_extractor.export import write_csvs, write_overlays
from pdf_code_extractor.normalize import apply as normalize_apply
from pdf_code_extractor.ocr_codes import detect as detect_codes
from pdf_code_extractor.ocr_zones import detect as detect_zones
from pdf_code_extractor.preprocess import load_and_enhance
from pdf_code_extractor.raster import pdf_to_pngs
from pdf_code_extractor.spatial import assign
from pdf_code_extractor.validate import run as validate_run

from utils.config import load_config
from utils.logging import setup_logging

# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------


def process_pdfs(
    pdf_paths: list[Path], output_dir: Path, cfg_path: str | None = None
) -> dict[str, Any]:  # noqa: D401
    config = load_config(cfg_path)
    setup_logging(json_logging=False, level="INFO")

    out_dir = output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    temp_dir = Path(tempfile.mkdtemp(prefix="extract_")).resolve()

    zones: list[dict[str, Any]] = []
    codes: list[dict[str, Any]] = []
    page_images: dict[int, Path] = {}

    page_counter = 1
    for pdf_path in pdf_paths:
        logger.info(f"Processing PDF: {pdf_path}")
        raster_dir = temp_dir / pdf_path.stem
        page_pngs = pdf_to_pngs(
            pdf_path, raster_dir, dpi=config.raster.dpi, engine=config.raster.engine
        )

        for local_page_num, png_path in page_pngs:
            global_page_num = page_counter
            page_counter += 1
            page_images[global_page_num] = png_path

            # Preprocess
            img = load_and_enhance(png_path)

            # OCR detections
            zones.extend(detect_zones(img, global_page_num))
            codes.extend(detect_codes(img, global_page_num))

    # Spatial assignment
    assigned_codes, spatial_report = assign(zones, codes, config.spatial.dict())

    # Convert dataclasses to dicts
    assigned_dicts = [c.__dict__.copy() for c in assigned_codes]

    # Normalisation
    norm_rows = normalize_apply(assigned_dicts)

    # Validation
    validation_report = validate_run(norm_rows, zones, None)

    # Exports
    write_csvs(norm_rows, out_dir)
    write_overlays(norm_rows, zones, page_images, out_dir / "overlays")

    # Persist report
    with (out_dir / "qa_report.json").open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "spatial": spatial_report,
                "validation": validation_report,
            },
            fh,
            indent=2,
        )

    logger.info("Extraction completed")
    shutil.rmtree(temp_dir, ignore_errors=True)

    return {
        "spatial": spatial_report,
        "validation": validation_report,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def make_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract A1 drawing zones & codes from PDFs.")
    parser.add_argument("pdf", nargs="+", help="Input PDF file(s)")
    parser.add_argument(
        "--out", "-o", default="output", help="Output directory for CSVs & overlays"
    )
    parser.add_argument("--config", "-c", help="Path to YAML config file")
    return parser


def main() -> None:  # noqa: D401
    parser = make_arg_parser()
    args = parser.parse_args()

    pdf_paths = [Path(p).expanduser().resolve() for p in args.pdf]
    output_dir = Path(args.out).expanduser().resolve()

    process_pdfs(pdf_paths, output_dir, args.config)


if __name__ == "__main__":
    main()
