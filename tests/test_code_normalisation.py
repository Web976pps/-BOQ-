from pdf_code_extractor.ocr_codes import normalise_code


def test_normalise_code_variants() -> None:
    cases = {
        "CH 21 a": "CH21A",
        "tb-99": "TB99",
        "c 123": "C123",
        "SU-7b": "SU7B",
    }
    for raw, expected in cases.items():
        norm, _ = normalise_code(raw)
        assert norm == expected
