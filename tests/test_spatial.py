from pdf_code_extractor.spatial import assign, SpatialCfg, DBSCANCfg, to_px


# Synthetic zone and code fixtures
ZONE_1 = {"page": 1, "bbox": (100, 100, 50, 20), "conf": 80.0, "zone": "A"}
ZONE_2 = {"page": 1, "bbox": (300, 100, 60, 25), "conf": 70.0, "zone": "B"}

CODE_NEAR_1 = {"page": 1, "bbox": (110, 120, 30, 15), "conf": 90.0, "code": "CH1", "prefix": "CH"}
CODE_NEAR_1_B = {"page": 1, "bbox": (120, 140, 30, 15), "conf": 85.0, "code": "CH2", "prefix": "CH"}
CODE_NEAR_2 = {"page": 1, "bbox": (310, 120, 30, 15), "conf": 88.0, "code": "CH3", "prefix": "CH"}
CODE_MID = {"page": 1, "bbox": (200, 100, 30, 15), "conf": 92.0, "code": "CH4", "prefix": "CH"}


def _extract_zones_and_codes():
    zones = [ZONE_1, ZONE_2]
    codes = [CODE_NEAR_1, CODE_NEAR_1_B, CODE_NEAR_2, CODE_MID]
    return zones, codes


def test_dbscan_assignment():
    zones, codes = _extract_zones_and_codes()
    cfg = SpatialCfg(strategy="dbscan", dbscan=DBSCANCfg(eps_mm=10))  # large eps
    assigned, report = assign(zones, codes, cfg)

    zones_map = {c.code: c.zone for c in assigned}
    assert zones_map["CH1"] == "A"
    assert zones_map["CH2"] == "A"
    assert zones_map["CH3"] == "B"
    # mid code should tie-break (higher zone conf) -> zone A
    assert zones_map["CH4"] == "A"
    assert report.unassigned == 0


def test_no_zones_unassigned():
    zones = []
    _, codes = _extract_zones_and_codes()
    cfg = SpatialCfg(strategy="dbscan")
    assigned, report = assign(zones, codes, cfg)

    assert all(c.zone == "__UNASSIGNED__" for c in assigned)
    assert report.unassigned == len(codes)


def test_determinism():
    zones, codes = _extract_zones_and_codes()
    cfg = SpatialCfg(strategy="dbscan", dbscan=DBSCANCfg(eps_mm=10))
    a1, _ = assign(zones, codes, cfg)
    a2, _ = assign(zones, codes, cfg)
    assert [c.zone for c in a1] == [c.zone for c in a2] 