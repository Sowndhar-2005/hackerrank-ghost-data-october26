import pandas as pd
import json

df_req = pd.read_csv('dataset/sample_deletion_requests.csv')
df_out = pd.read_csv('dataset/sample_output.csv')
merged = pd.merge(df_req, df_out, on='case_id')

for idx, row in merged.iterrows():
    steps = json.loads(row['steps_json'])
    print(f"--- Case: {row['case_id']} | Email: {row['email']} | Status: {row['deletion_status']} | AuditAt: {row['audit_at']} ---")
    print(f"Request: {row['request_text'][:80]}...")
    for s in steps:
        print(f"  Step {s['step_no']}: phase={s['phase']}, sys={s['system_id']}, res={s['resource_id']}, op={s['operation']}, st={s['state']}, evid={s.get('evidence_id')}")
