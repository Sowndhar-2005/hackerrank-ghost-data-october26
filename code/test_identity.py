import pandas as pd

df_users = pd.read_csv('dataset/user_identities.csv')
df_audit = pd.read_csv('dataset/user_audit_log.csv')
df_sample = pd.read_csv('dataset/sample_deletion_requests.csv')

def resolve_user(email):
    # check user_identities
    match = df_users[df_users['email'].str.lower() == email.lower()]
    if not match.empty:
        return match.iloc[0]['user_id']
    
    # check audit log
    match_audit = df_audit[(df_audit['field_name'] == 'email') & 
                           ((df_audit['old_value'].str.lower() == email.lower()) | 
                            (df_audit['new_value'].str.lower() == email.lower()))]
    if not match_audit.empty:
        return match_audit.iloc[0]['user_id']
    return None

found = 0
for idx, row in df_sample.iterrows():
    uid = resolve_user(row['email'])
    if uid:
        found += 1
    else:
        print(f"Could not resolve user for {row['case_id']} ({row['email']})")

print(f"Resolved {found} / {len(df_sample)} sample cases.")
