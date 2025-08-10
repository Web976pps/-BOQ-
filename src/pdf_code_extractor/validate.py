def run(norm_rows, zones, something):
    zones_without_codes = [z['text'] for z in zones if not any(r['zone'] == z['text'] for r in norm_rows)]
    return {"valid": True, "zones_without_codes": zones_without_codes}
