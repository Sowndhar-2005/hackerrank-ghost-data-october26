import json
import pandas as pd
from agent import DeletionAuditAgent

agent = DeletionAuditAgent()
df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
df_out = pd.read_csv('dataset/sample_output.csv')

with open('code/ground_truth_steps.json') as f:
    gt_all = json.load(f)

for idx, r in df_samples.iterrows():
    c = r['case_id']
    pred = agent.audit_case(r)
    gt_steps = gt_all[c]
    pred_steps = json.loads(pred['steps_json'])
    gt_status = df_out[df_out['case_id'] == c].iloc[0]['deletion_status']
    pred_status = pred['deletion_status']

    diff = (gt_status != pred_status) or (gt_steps != pred_steps)
    if diff:
        print(f"=== {c} status: pred={pred_status} gt={gt_status} ===")
        print(f"Pred ({len(pred_steps)}):")
        for s in pred_steps:
            print(f"   {s['phase']} | {s['system_id']} | {s['resource_id']} | {s['operation']} | {s['state']} | evid: {s['evidence_id']}")
        print(f"GT ({len(gt_steps)}):")
        for s in gt_steps:
            print(f"   {s['phase']} | {s['system_id']} | {s['resource_id']} | {s['operation']} | {s['state']} | evid: {s.get('evidence_id', '')}")
        print()
