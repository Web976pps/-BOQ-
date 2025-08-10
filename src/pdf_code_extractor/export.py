import pandas as pd
from pathlib import Path
import cv2

def write_csvs(norm_rows, out_dir):
    df = pd.DataFrame(norm_rows)
    df.to_csv(out_dir / 'row_level_instances.csv', index=False)

def write_overlays(norm_rows, zones, page_images, overlay_dir):
    overlay_dir.mkdir(exist_ok=True)
    for page, path in page_images.items():
        img = cv2.imread(str(path))
        cv2.imwrite(str(overlay_dir / f'page_{page}_overlay.png'), img)
