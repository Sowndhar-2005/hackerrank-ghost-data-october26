import json
import pandas as pd
from rag_indexer import EvidenceIndexer

indexer = EvidenceIndexer()
cache = indexer.parse_all()

df_users = pd.read_csv('dataset/user_identities.csv')
df_audit = pd.read_csv('dataset/user_audit_log.csv')
df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
with open('code/ground_truth_steps.json') as f:
    ground_truth = json.load(f)

from test_top_evid import get_identifiers

for idx, r in df_samples.iterrows():
    c = r['case_id']
    audit_at = r['audit_at']
    ids = get_identifiers(r['email'], audit_at)
    gt_steps = ground_truth[c]
    gt_evids = sorted(list(set(s['evidence_id'] for s in gt_steps if s['evidence_id'])))
    if not gt_evids:
        continue
    eid = gt_evids[0]
    finfo = cache[eid]
    matching_recs = []
    for rec in finfo['records']:
        r_str = json.dumps(rec).lower()
        if any(em in r_str for em in ids['emails']) or (ids['user_id'] and ids['user_id'].lower() in r_str):
            matching_recs.append(rec)
    print(f"\n=== {c} ({r['email']}) -> {eid} ({len(matching_recs)} matching recs) ===")
    for m in matching_recs:
        print("  ", m)
