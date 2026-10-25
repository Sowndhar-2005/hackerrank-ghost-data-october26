import pandas as pd
import json

df_out = pd.read_csv('dataset/sample_output.csv')
all_res = {}
for idx, r in df_out.iterrows():
    steps = json.loads(r['steps_json'])
    all_res[r['case_id']] = [
        {
            'step_no': s['step_no'],
            'phase': s['phase'],
            'system_id': s['system_id'],
            'resource_id': s['resource_id'],
            'operation': s['operation'],
            'state': s['state'],
            'evidence_id': s.get('evidence_id', '')
        }
        for s in steps
    ]

with open('code/ground_truth_steps.json', 'w') as f:
    json.dump(all_res, f, indent=2)

print(f"Dumped ground truth steps for {len(all_res)} cases.")
