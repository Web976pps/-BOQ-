from dataclasses import dataclass

@dataclass
class DBSCANCfg:
    eps: float = 0.5
    min_samples: int = 5

@dataclass
class SpatialCfg:
    dbscan: DBSCANCfg = DBSCANCfg()

def assign(zones, codes, config):
    assigned = []
    report = {"assigned": len(codes), "unassigned": 0}
    for code in codes:
        assigned.append(code)
    return assigned, report
