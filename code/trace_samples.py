import pandas as pd
import json

df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
df_out = pd.read_csv('dataset/sample_output.csv')
df_act = pd.read_csv('dataset/system_activity.csv')
df_users = pd.read_csv('dataset/user_identities.csv')
df_audit = pd.read_csv('dataset/user_audit_log.csv')
df_evid = pd.read_csv('dataset/evidence_files.csv')

def get_user_identifiers(email):
    # return set of all identifiers
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
    
    ids = {
        'user_id': user_id,
        'emails': {u_row.iloc[0]['email'].lower()},
        'names': {u_row.iloc[0]['name']},
        'phones': {u_row.iloc[0]['phone']},
        'email_hashes': {u_row.iloc[0]['email_hash']}
    }
    # audit logs
    user_audits = df_audit[df_audit['user_id'] == user_id]
    for _, a in user_audits.iterrows():
        f = a['field_name']
        if f == 'email':
            if pd.notna(a['old_value']): ids['emails'].add(a['old_value'].lower())
            if pd.notna(a['new_value']): ids['emails'].add(a['new_value'].lower())
        elif f == 'name':
            if pd.notna(a['old_value']): ids['names'].add(a['old_value'])
            if pd.notna(a['new_value']): ids['names'].add(a['new_value'])
        elif f == 'phone':
            if pd.notna(a['old_value']): ids['phones'].add(a['old_value'])
            if pd.notna(a['new_value']): ids['phones'].add(a['new_value'])
        elif f == 'email_hash':
            if pd.notna(a['old_value']): ids['email_hashes'].add(a['old_value'])
            if pd.notna(a['new_value']): ids['email_hashes'].add(a['new_value'])
    return ids

print("Sample analysis ready")
