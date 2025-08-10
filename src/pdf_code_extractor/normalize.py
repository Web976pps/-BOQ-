def apply(assigned_dicts):
    from collections import defaultdict
    dedup = defaultdict(int)
    for d in assigned_dicts:
        key = (d.get('zone'), d.get('code'))
        dedup[key] += 1
    return [{'zone': k[0], 'code': k[1], 'count': v} for k,v in dedup.items()]
