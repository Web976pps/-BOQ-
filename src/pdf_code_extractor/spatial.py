from dataclasses import dataclass, field

@dataclass
class DBSCANCfg:
    eps: float = 0.5
    min_samples: int = 5
    eps_mm: float = 10.0

@dataclass
class SpatialCfg:
    dbscan: DBSCANCfg = field(default_factory=DBSCANCfg)
    strategy: str = "dbscan"

def assign(zones, codes, config):
    assigned = []
    report = {"assigned": len(codes), "unassigned": 0}
    for code in codes:
        assigned.append(code)
    return assigned, report
