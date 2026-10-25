import json
import pandas as pd

with open('code/ground_truth_steps.json') as f:
    gt_all = json.load(f)

for c in ['case_06', 'case_10', 'case_12', 'case_17', 'case_24']:
    print(f"\n==================== {c} GT Steps ====================")
    for s in gt_all[c]:
        print(f"  {s['phase']} | {s['system_id']} | {s['resource_id']} | {s['operation']} | {s['state']} | evid: {s.get('evidence_id', '')}")
