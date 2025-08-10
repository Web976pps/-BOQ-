from pdf2image import convert_from_path

def pdf_to_pngs(pdf_path, raster_dir, dpi, engine):
    raster_dir.mkdir(parents=True, exist_ok=True)
    images = convert_from_path(pdf_path, dpi=dpi)
    png_paths = []
    for i, img in enumerate(images):
        png_path = raster_dir / f'page_{i+1}.png'
        img.save(png_path, 'PNG')
        png_paths.append((i+1, png_path))
    return png_paths
