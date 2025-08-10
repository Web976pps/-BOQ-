from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError

def pdf_to_pngs(pdf_path, raster_dir, dpi, engine):
    raster_dir.mkdir(parents=True, exist_ok=True)
    try:
        images = convert_from_path(pdf_path, dpi=dpi)
    except PDFInfoNotInstalledError:
        import fitz
        doc = fitz.open(pdf_path)
        images = []
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            images.append(pix.tobytes('png'))
    png_paths = []
    for i, img in enumerate(images):
        png_path = raster_dir / f'page_{i+1}.png'
        with open(png_path, 'wb') as f:
            f.write(img)
        png_paths.append((i+1, png_path))
    return png_paths
