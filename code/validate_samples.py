import json
import pandas as pd
from agent import DeletionAuditAgent

agent = DeletionAuditAgent()
df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
df_out = pd.read_csv('dataset/sample_output.csv')

total = len(df_samples)
status_matches = 0
exact_step_matches = 0

print(f"Validating on {total} sample cases:")
for idx, r in df_samples.iterrows():
    c = r['case_id']
    pred = agent.audit_case(r)
    gt_row = df_out[df_out['case_id'] == c].iloc[0]
    
    gt_status = gt_row['deletion_status']
    pred_status = pred['deletion_status']
    
    gt_steps = json.loads(gt_row['steps_json'])
    pred_steps = json.loads(pred['steps_json'])
    
    s_match = (gt_status == pred_status)
    if s_match:
        status_matches += 1
        
    step_match = (gt_steps == pred_steps)
    if step_match:
        exact_step_matches += 1
    else:
        print(f"\n--- {c} Diff ---")
        print(f"Status: pred={pred_status} vs gt={gt_status}")
        print(f"Pred steps ({len(pred_steps)}):")
        for s in pred_steps:
            print(f"   {s['phase']} | {s['system_id']} | {s['resource_id']} | {s['operation']} | {s['state']} | evid: '{s['evidence_id']}'")
        print(f"GT steps ({len(gt_steps)}):")
        for s in gt_steps:
            print(f"   {s['phase']} | {s['system_id']} | {s['resource_id']} | {s['operation']} | {s['state']} | evid: '{s.get('evidence_id', '')}'")

print("\n" + "="*40)
print(f"Status Accuracy: {status_matches}/{total} ({status_matches/total*100:.1f}%)")
print(f"Exact Step Match: {exact_step_matches}/{total} ({exact_step_matches/total*100:.1f}%)")
print("="*40)
