import cv2

def load_and_enhance(png_path):
    img = cv2.imread(str(png_path))
    return _deskew(img)

def _deskew(img):
    # Basic deskew placeholder
    return img
