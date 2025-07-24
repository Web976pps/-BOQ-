from pdf_code_extractor.normalize import apply as norm_apply
from pdf_code_extractor.validate import run as validate_run

rows = [
    {"page": 1, "zone": "A", "code": "C1", "conf": 90.0},
    {"page": 1, "zone": "A", "code": "C1", "conf": 80.0},  # duplicate lower conf
    {"page": 1, "zone": "B", "code": "C2", "conf": 88.0},
    {"page": 1, "zone": "__UNASSIGNED__", "code": "C3", "conf": 70.0},
]

zones = [
    {"page": 1, "bbox": (0, 0, 50, 20), "conf": 80.0, "zone": "A"},
    {"page": 1, "bbox": (100, 0, 50, 20), "conf": 75.0, "zone": "B"},
]


def test_normalize_dedup():
    uniq = norm_apply(rows)
    assert len(uniq) == 3  # duplicate removed


def test_validate_summary():
    uniq = norm_apply(rows)
    report = validate_run(uniq, zones, None)
    assert "A" not in report["zones_without_codes"]
    assert "C3" in report["unassigned_codes"]
