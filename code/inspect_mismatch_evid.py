import json

with open('code/evidence_cache.json') as f:
    cache = json.load(f)

# Inspect evidence_57
print("=== evidence_57 (case_06) ===")
print(cache.get('evidence_57', {}).get('file_path'))
for r in cache.get('evidence_57', {}).get('records', []):
    if 'search' in str(r) or 'jonas' in str(r):
        print(r)

# Inspect evidence_61
print("\n=== evidence_61 (case_10) ===")
print(cache.get('evidence_61', {}).get('file_path'))
for r in cache.get('evidence_61', {}).get('records', []):
    if 'support' in str(r) or 'nadia' in str(r):
        print(r)

# Inspect evidence_01 for case_12 and case_17
print("\n=== evidence_01 (case_12: analytics_9914, case_17: backup_3245) ===")
for r in cache.get('evidence_01', {}).get('records', []):
    r_id = r.get('resource_id')
    if r_id in ['analytics_9914', 'backup_3245']:
        print(r)
