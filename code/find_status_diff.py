import json
import pandas as pd
from agent import DeletionAuditAgent

agent = DeletionAuditAgent()
df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
df_out = pd.read_csv('dataset/sample_output.csv')

print("Status Mismatches:")
for idx, r in df_samples.iterrows():
    c = r['case_id']
    pred = agent.audit_case(r)
    gt_status = df_out[df_out['case_id'] == c].iloc[0]['deletion_status']
    pred_status = pred['deletion_status']
    if gt_status != pred_status:
        print(f"Case {c}: pred={pred_status} vs gt={gt_status} | email={r['email']} | reported={r['reported_status']}")
