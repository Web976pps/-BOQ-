"""PDF → PNG rasterisation helpers."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple

import fitz  # PyMuPDF
from loguru import logger


__all__ = ["pdf_to_pngs"]


# ---------------------------------------------------------------------------
# Engine-specific renderers
# ---------------------------------------------------------------------------

def _render_with_pymupdf(pdf_path: Path, out_dir: Path, dpi: int) -> list[Tuple[int, Path]]:
    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0  # 72 DPI is PDF user-space
    matrix = fitz.Matrix(zoom, zoom)
    results: list[Tuple[int, Path]] = []

    for page_index, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=matrix)
        out_path = out_dir / f"page_{page_index:04d}.png"
        pix.save(out_path)
        results.append((page_index, out_path))

    return results


def _render_with_pdftoppm(pdf_path: Path, out_dir: Path, dpi: int) -> list[Tuple[int, Path]]:
    prefix = out_dir / "page"
    cmd = [
        "pdftoppm",
        "-png",
        "-r",
        str(dpi),
        str(pdf_path),
        str(prefix),
    ]
    subprocess.run(cmd, check=True)

    results: list[Tuple[int, Path]] = []
    for png_path in sorted(out_dir.glob("page-*.png")):
        page_num = int("".join(filter(str.isdigit, png_path.stem)))
        results.append((page_num, png_path))
    return results


def _render_with_ghostscript(pdf_path: Path, out_dir: Path, dpi: int) -> list[Tuple[int, Path]]:
    cmd = [
        "gs",
        "-dNOPAUSE",
        "-sDEVICE=pnggray",
        f"-r{dpi}",
        "-sOutputFile=" + str(out_dir / "page_%04d.png"),
        str(pdf_path),
        "-dBATCH",
    ]
    subprocess.run(cmd, check=True)

    results: list[Tuple[int, Path]] = []
    for png_path in sorted(out_dir.glob("page_*.png")):
        page_num = int(png_path.stem.split("_")[1])
        results.append((page_num, png_path))
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def pdf_to_pngs(pdf_path: str | Path, out_dir: str | Path, *, dpi: int = 300, engine: str = "auto") -> List[Tuple[int, Path]]:  # noqa: D401
    """Rasterise **pdf_path** into PNGs using the selected *engine*.

    Returns a list of *(page_number, png_path)* tuples.
    """

    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if engine == "auto":
        engine = "pdftoppm" if shutil.which("pdftoppm") else "ghostscript" if shutil.which("gs") else "pymupdf"

    logger.info(f"Rasterising {pdf_path.name} with {engine} @ {dpi} DPI → {out_dir}")

    if engine == "pdftoppm":
        return _render_with_pdftoppm(pdf_path, out_dir, dpi)
    if engine == "ghostscript":
        return _render_with_ghostscript(pdf_path, out_dir, dpi)
    if engine == "pymupdf":
        return _render_with_pymupdf(pdf_path, out_dir, dpi)

    raise ValueError(f"Unknown raster engine: {engine}") 