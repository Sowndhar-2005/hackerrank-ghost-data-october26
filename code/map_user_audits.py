import json
from rag_indexer import EvidenceIndexer

indexer = EvidenceIndexer()
cache = indexer.parse_all()

audit_user_map = {}
for fid, finfo in cache.items():
    for rec in finfo['records']:
        r_id = rec.get('resource_id')
        if r_id and 'audit_record_' in str(r_id):
            u_refs = []
            for k in ['subject_reference', 'customer_reference', 'lookup_key', 'correlation_key', 'subject_key', 'user_id']:
                v = rec.get(k)
                if v and isinstance(v, str):
                    u_refs.append(v.strip('"\''))
            # Check raw_line if present
            raw = rec.get('raw_line', '')
            if 'correlation_key=' in raw:
                import re
                m = re.search(r'correlation_key="?([^"\s]+)"?', raw)
                if m:
                    u_refs.append(m.group(1))
            for u in u_refs:
                audit_user_map[u] = r_id
                audit_user_map[(u, fid)] = r_id

print(f"Total mapped user -> audit_record entries: {len(audit_user_map)}")
