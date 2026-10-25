import json
import pandas as pd

with open('code/ground_truth_steps.json') as f:
    gt_all = json.load(f)
with open('code/evidence_cache.json') as f:
    cache = json.load(f)

df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
df_users = pd.read_csv('dataset/user_identities.csv')
df_audit = pd.read_csv('dataset/user_audit_log.csv')

acc_matches = 0
for idx, r in df_samples.iterrows():
    c = r['case_id']
    em = r['email'].lower()
    gt_steps = gt_all[c]
    gt_acc = None
    for s in gt_steps:
        if s['system_id'] == 'account_service' and 'account_' in s['resource_id']:
            gt_acc = s['resource_id']
            break
            
    # Find user_id and all emails
    emails = {em}
    u_row = df_users[df_users['email'].str.lower() == em]
    user_id = u_row.iloc[0]['user_id'] if not u_row.empty else None
    if not user_id:
        a_row = df_audit[(df_audit['field_name'] == 'email') & ((df_audit['old_value'].str.lower() == em) | (df_audit['new_value'].str.lower() == em))]
        if not a_row.empty:
            user_id = a_row.iloc[0]['user_id']
    if user_id:
        u_row = df_users[df_users['user_id'] == user_id]
        if not u_row.empty:
            emails.add(u_row.iloc[0]['email'].lower())
        a_rows = df_audit[df_audit['user_id'] == user_id]
        for _, ar in a_rows.iterrows():
            if ar['field_name'] == 'email':
                if pd.notna(ar['old_value']): emails.add(ar['old_value'].lower())
                if pd.notna(ar['new_value']): emails.add(ar['new_value'].lower())

    found_acc = None
    for fid, finfo in cache.items():
        for rec in finfo['records']:
            r_id = rec.get('resource_id')
            if r_id and str(r_id).startswith('account_'):
                for col in ['customer_reference', 'subject_reference', 'subject_ref', 'user_id', 'lookup_key', 'correlation_key']:
                    val = str(rec.get(col, '')).strip('\"\'')
                    if user_id and val == user_id:
                        found_acc = str(r_id)
                        break
                    if val.lower() in emails:
                        found_acc = str(r_id)
                        break
                for em_col in ['email', 'requester_email', 'customer_email', 'owner_email']:
                    val = str(rec.get(em_col, '')).strip('\"\'').lower()
                    if val in emails:
                        found_acc = str(r_id)
                        break
            if found_acc:
                break
        if found_acc:
            break
            
    if not found_acc and user_id:
        digits = ''.join(c for c in user_id if c.isdigit())
        if digits:
            num = int(digits)
            found_acc = f"account_{num:03d}" if num < 100 else f"account_{num}"

    print(f"{c} ({user_id}): GT={gt_acc} Found={found_acc} Match={found_acc == gt_acc}")
    if found_acc == gt_acc:
        acc_matches += 1

print(f"\nTotal Matches: {acc_matches}/32")
