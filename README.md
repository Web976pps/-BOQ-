# A1 PDF Zones/Codes Extractor

This repository contains a Python 3.11+ implementation of an A1 PDF zones/codes extractor.

## Quick Start

### Virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
make run-streamlit
```

### Docker

```bash
docker build -t pdf-extractor .
docker run -p 8501:8501 pdf-extractor
```

### Streamlit

```bash
make run-streamlit
```

## Configuration Reference

The pipeline is driven by a YAML config (see `config/default.yml`). All keys and defaults are documented below:

```yaml
raster:
  dpi: 300                # PNG resolution
  engine: auto            # pdftoppm | ghostscript | pymupdf | auto

preprocess:
  clahe_clip: 2.0         # CLAHE contrast limit
  clahe_grid: 8           # CLAHE grid size
  adaptive_block_size: 51 # Adaptive threshold block size (odd)
  adaptive_C: 2           # Adaptive threshold C
  deskew: true            # Deskew pages

spatial:
  strategy: dbscan        # dbscan | voronoi
  max_assign_dist_mm: 500 # Fallback nearest-zone distance (mm)
  zone_buffer_mm: 50      # Dilate zone polygons (mm)
  dbscan:
    eps_mm: 150           # Cluster radius (mm)
    min_samples: 1        # DBSCAN min samples
```

You can override any value by supplying `--config my.yml` to the CLI.

## Examples & Samples

A sample input PDF can be placed in `input/` (directory is git-tracked via `.gitkeep`). Example extractor outputs are stored in `outputs/example/` (headers only for brevity).

Run the full pipeline on the sample PDF:

```bash
make run PDF=input/sample.pdf OUT=outputs/example_run
```

The CSVs contain a metadata comment line with the extractor version (derived from the `VERSION` file) for reproducibility.
