import os
import re
import json
import pandas as pd
from rag_indexer import EvidenceIndexer

indexer = EvidenceIndexer()
cache = indexer.parse_all()

df_users = pd.read_csv('dataset/user_identities.csv')
df_audit = pd.read_csv('dataset/user_audit_log.csv')
df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
df_out = pd.read_csv('dataset/sample_output.csv')
df_act = pd.read_csv('dataset/system_activity.csv')

with open('code/ground_truth_steps.json') as f:
    ground_truth = json.load(f)

from test_top_evid import get_identifiers

def discover_case_resources(case_row):
    email = case_row['email']
    audit_at = case_row['audit_at']
    reported_at = case_row['reported_at']
    requested_at = case_row['requested_at']
    
    ids = get_identifiers(email, audit_at)
    user_id = ids['user_id']
    emails = ids['emails']
    phones = ids['phones']
    hashes = ids['email_hashes']
    
    discovered_resources = set()
    resource_details = {} # res_id -> {system_id, state, evidence_id, etc.}
    
    # 1. Search Evidence Files <= audit_at
    for fid, finfo in cache.items():
        if finfo['captured_at'] <= audit_at:
            for rec in finfo['records']:
                # Check match
                matched = False
                for ref in ['user_id', 'customer_reference', 'subject_reference', 'lookup_key', 
                            'correlation_key', 'subject_ref', 'subject_key']:
                    v = rec.get(ref)
                    if v and isinstance(v, str):
                        if (user_id and v == user_id) or (v.lower() in emails):
                            matched = True; break
                if not matched:
                    for em in ['email', 'requester_email', 'owner_email', 'customer_email', 'lookup_key']:
                        v = rec.get(em)
                        if v and isinstance(v, str) and v.lower() in emails:
                            matched = True; break
                if not matched and 'content' in rec:
                    c = rec['content']
                    if any(e in c.lower() for e in emails) or (user_id and user_id in c):
                        matched = True
                        
                if matched:
                    r_id = rec.get('resource_id')
                    if r_id:
                        discovered_resources.add(r_id)
                        if r_id not in resource_details:
                            resource_details[r_id] = []
                        resource_details[r_id].append((fid, rec))

    # 2. Search Activity <= audit_at
    # Check deletion_worker window
    rep_dt = pd.to_datetime(reported_at)
    w_start = (rep_dt - pd.Timedelta(hours=3)).isoformat()
    w_end = (rep_dt + pd.Timedelta(minutes=30)).isoformat()
    
    window_acts = df_act[
        (df_act['source_system'] == 'deletion_worker') &
        (df_act['event_time'] >= w_start) &
        (df_act['event_time'] <= w_end) &
        (df_act['event_time'] <= audit_at)
    ]
    
    # If any resource already discovered is in window_acts, pull all co-occurring resources from that batch!
    batch_res = set()
    for idx, a in window_acts.iterrows():
        r_id = a['resource_id']
        if r_id in discovered_resources:
            # Found connection! Look around this activity timestamp
            act_time = a['event_time']
            # activities within 10 minutes
            close_acts = window_acts[
                (window_acts['event_time'] >= (pd.to_datetime(act_time) - pd.Timedelta(minutes=45)).isoformat()) &
                (window_acts['event_time'] <= (pd.to_datetime(act_time) + pd.Timedelta(minutes=45)).isoformat())
            ]
            for _, ca in close_acts.iterrows():
                batch_res.add(ca['resource_id'])
                
    return ids, discovered_resources, batch_res

for idx, r in df_samples.iterrows():
    c = r['case_id']
    gt_res = set(s['resource_id'] for s in ground_truth[c])
    ids, disc, batch = discover_case_resources(r)
    combined = disc.union(batch)
    missing = gt_res - combined
    extra = combined - gt_res
    print(f"{c}: GT={len(gt_res)}, Found={len(combined)} | Missing: {missing} | Extra: {extra}")
