import os
import json
import pandas as pd
from rag_indexer import EvidenceIndexer

indexer = EvidenceIndexer()
cache = indexer.parse_all()

df_users = pd.read_csv('dataset/user_identities.csv')
df_audit = pd.read_csv('dataset/user_audit_log.csv')
df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
df_evid = pd.read_csv('dataset/evidence_files.csv').set_index('file_id').to_dict('index')

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

print("Testing evidence matching against ground truth:")
for idx, r in df_samples.iterrows():
    c = r['case_id']
    audit_at = r['audit_at']
    ids = get_identifiers(r['email'], audit_at)
    gt_steps = ground_truth[c]
    gt_findings = [s for s in gt_steps if s['phase'] == 'FINDING']
    gt_status = "COMPLETE" if not gt_findings else "INCOMPLETE"
    
    # Check which evidence files before audit_at contain records for this user
    matching_evids = []
    for fid, finfo in cache.items():
        if finfo['captured_at'] <= audit_at:
            for rec in finfo['records']:
                # check match
                r_str = json.dumps(rec).lower()
                matched = False
                for em in ids['emails']:
                    if em in r_str: matched = True; break
                if not matched and ids['user_id'] and ids['user_id'].lower() in r_str:
                    matched = True
                if matched:
                    matching_evids.append((fid, finfo['origin'], finfo['captured_at']))
                    break
    
    gt_evids = list(set(s['evidence_id'] for s in gt_steps if s['evidence_id']))
    print(f"{c} ({gt_status}) | GT evids: {gt_evids} | Found matching evids: {[e[0] for e in matching_evids]}")
