import pandas as pd
import json

df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
df_out = pd.read_csv('dataset/sample_output.csv')
df_evid = pd.read_csv('dataset/evidence_files.csv')
merged = pd.merge(df_samples, df_out, on='case_id')

evid_map = dict(zip(df_evid['file_id'], df_evid['origin']))

for idx, r in merged.iterrows():
    steps = json.loads(r['steps_json'])
    evids = list(set(s['evidence_id'] for s in steps if s.get('evidence_id')))
    evid_origins = [f"{e} ({evid_map.get(e)})" for e in evids]
    findings = [f"{s['system_id']}:{s['resource_id']}:{s['operation']}:{s.get('evidence_id')}" for s in steps if s['phase'] == 'FINDING']
    verifs = [f"{s['system_id']}:{s['resource_id']}:{s['operation']}:{s.get('evidence_id')}" for s in steps if s['phase'] == 'VERIFICATION']
    print(f"{r['case_id']} ({r['email']}) -> {r['deletion_status']} | audit: {r['audit_at']}")
    print(f"   Evids: {evid_origins}")
    if findings:
        print(f"   Findings: {findings}")
    if r['deletion_status'] == 'COMPLETE':
        print(f"   Verifs: {verifs}")
