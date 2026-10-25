import pandas as pd
import json

df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
df_out = pd.read_csv('dataset/sample_output.csv')
df_evid = pd.read_csv('dataset/evidence_files.csv')
merged = pd.merge(df_samples, df_out, on='case_id')
ev_dict = df_evid.set_index('file_id').to_dict('index')

for idx, r in merged.iterrows():
    steps = json.loads(r['steps_json'])
    evids = list(set(s['evidence_id'] for s in steps if s.get('evidence_id')))
    print(f"=== {r['case_id']} | email: {r['email']} | audit_at: {r['audit_at']} | status: {r['deletion_status']} ===")
    for eid in evids:
        info = ev_dict.get(eid, {})
        print(f"   cited: {eid} | captured_at: {info.get('captured_at')} | origin: {info.get('origin')} | path: {info.get('file_path')}")
