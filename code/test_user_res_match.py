import pandas as pd
import json
import os
import re

df_users = pd.read_csv('dataset/user_identities.csv')
df_audit = pd.read_csv('dataset/user_audit_log.csv')
df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
df_out = pd.read_csv('dataset/sample_output.csv')

with open('code/ground_truth_steps.json') as f:
    ground_truth = json.load(f)

def get_identifiers(email):
    u_row = df_users[df_users['email'].str.lower() == email.lower()]
    user_id = None
    if not u_row.empty:
        user_id = u_row.iloc[0]['user_id']
    else:
        a_row = df_audit[(df_audit['field_name'] == 'email') & 
                         ((df_audit['old_value'].str.lower() == email.lower()) | 
                          (df_audit['new_value'].str.lower() == email.lower()))]
        if not a_row.empty:
            user_id = a_row.iloc[0]['user_id']
            u_row = df_users[df_users['user_id'] == user_id]
    
    if not user_id:
        return {}
    
    emails = {u_row.iloc[0]['email'].lower(), email.lower()}
    names = {str(u_row.iloc[0]['name'])}
    phones = {str(u_row.iloc[0]['phone'])}
    hashes = {str(u_row.iloc[0]['email_hash'])}
    
    user_audits = df_audit[df_audit['user_id'] == user_id]
    for _, a in user_audits.iterrows():
        f = a['field_name']
        if f == 'email':
            if pd.notna(a['old_value']): emails.add(a['old_value'].lower())
            if pd.notna(a['new_value']): emails.add(a['new_value'].lower())
        elif f == 'name':
            if pd.notna(a['old_value']): names.add(a['old_value'])
            if pd.notna(a['new_value']): names.add(a['new_value'])
        elif f == 'phone':
            if pd.notna(a['old_value']): phones.add(a['old_value'])
            if pd.notna(a['new_value']): phones.add(a['new_value'])
        elif f == 'email_hash':
            if pd.notna(a['old_value']): hashes.add(a['old_value'])
            if pd.notna(a['new_value']): hashes.add(a['new_value'])
            
    return {
        'user_id': user_id,
        'emails': emails,
        'names': names,
        'phones': phones,
        'email_hashes': hashes
    }

# Let's test matching across all 32 cases
print("Testing identifier resolution for 32 sample cases:")
for idx, r in df_samples.iterrows():
    c = r['case_id']
    ids = get_identifiers(r['email'])
    expected_resources = set(s['resource_id'] for s in ground_truth[c])
    print(f"{c}: user={ids['user_id']}, emails={ids['emails']}, expected_res={expected_resources}")
