import re
from pdf_code_extractor.ocr_codes import _CODE_PATTERN


def test_regex_matches_valid_codes():
    samples = [
        "CH21A",
        "TB-12",
        "C 9",
        "su 7b",
    ]
    for s in samples:
        assert _CODE_PATTERN.search(s)


def test_regex_rejects_invalid():
    invalid = [
        "XY123",
        "CH",
        "123CH",
        "TB--",
    ]
    for s in invalid:
        assert not _CODE_PATTERN.search(s) 