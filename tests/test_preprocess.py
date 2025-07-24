import cv2
import numpy as np

from pdf_code_extractor.preprocess import _deskew


def test_deskew_preserves_shape() -> None:
    """Deskew should not change image dimensions."""

    img = np.zeros((100, 100), dtype=np.uint8)
    cv2.putText(img, "TEST", (5, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2, cv2.LINE_AA)
    rotated = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

    deskewed = _deskew(rotated)

    assert deskewed.shape == rotated.shape
