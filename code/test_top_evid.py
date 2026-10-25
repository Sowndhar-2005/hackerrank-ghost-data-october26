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

with open('code/ground_truth_steps.json') as f:
    ground_truth = json.load(f)

def get_identifiers(email, audit_at):
    email_clean = email.strip().lower()
    u_row = df_users[df_users['email'].str.lower() == email_clean]
    user_id = None
    if not u_row.empty:
        user_id = u_row.iloc[0]['user_id']
    else:
        a_row = df_audit[
            (df_audit['field_name'] == 'email') & 
            ((df_audit['old_value'].str.lower() == email_clean) | 
             (df_audit['new_value'].str.lower() == email_clean)) &
            (df_audit['event_time'] <= audit_at)
        ]
        if not a_row.empty:
            user_id = a_row.iloc[0]['user_id']
            u_row = df_users[df_users['user_id'] == user_id]

    if not user_id:
        return {'user_id': None, 'emails': {email_clean}, 'names': set(), 'phones': set(), 'email_hashes': set()}

    emails = {u_row.iloc[0]['email'].lower(), email_clean}
    names = {str(u_row.iloc[0]['name']).strip()}
    phones = {str(u_row.iloc[0]['phone']).strip()}
    hashes = {str(u_row.iloc[0]['email_hash']).strip()}

    user_audits = df_audit[
        (df_audit['user_id'] == user_id) & 
        (df_audit['event_time'] <= audit_at)
    ]
    for _, a in user_audits.iterrows():
        f = a['field_name']
        if f == 'email':
            if pd.notna(a['old_value']): emails.add(a['old_value'].strip().lower())
            if pd.notna(a['new_value']): emails.add(a['new_value'].strip().lower())
        elif f == 'name':
            if pd.notna(a['old_value']): names.add(a['old_value'].strip())
            if pd.notna(a['new_value']): names.add(a['new_value'].strip())
        elif f == 'phone':
            if pd.notna(a['old_value']): phones.add(a['old_value'].strip())
            if pd.notna(a['new_value']): phones.add(a['new_value'].strip())
        elif f == 'email_hash':
            if pd.notna(a['old_value']): hashes.add(a['old_value'].strip())
            if pd.notna(a['new_value']): hashes.add(a['new_value'].strip())

    return {
        'user_id': user_id,
        'emails': emails,
        'names': names,
        'phones': phones,
        'email_hashes': hashes
    }

# Check for each sample case:
for idx, r in df_samples.iterrows():
    c = r['case_id']
    audit_at = r['audit_at']
    ids = get_identifiers(r['email'], audit_at)
    gt_steps = ground_truth[c]
    gt_evids = sorted(list(set(s['evidence_id'] for s in gt_steps if s['evidence_id'])))
    
    # Find all evidence files matching this user with captured_at <= audit_at
    matching = []
    for fid, finfo in cache.items():
        if finfo['captured_at'] <= audit_at:
            # Check records
            cnt = 0
            for rec in finfo['records']:
                r_str = json.dumps(rec).lower()
                if any(em in r_str for em in ids['emails']) or (ids['user_id'] and ids['user_id'].lower() in r_str):
                    cnt += 1
            if cnt > 0:
                matching.append((finfo['captured_at'], fid, finfo['origin'], cnt))
                
    matching.sort(key=lambda x: x[0], reverse=True)
    top_evids = [m[1] for m in matching[:len(gt_evids)]] if matching else []
    print(f"{c}: GT={gt_evids} | Top matching={top_evids} | all matching={[(m[1], m[0]) for m in matching]}")
