import pandas as pd
import json

df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
df_out = pd.read_csv('dataset/sample_output.csv')
df_act = pd.read_csv('dataset/system_activity.csv')

# For each sample case, let's see which activities match its resources
for idx, r in df_samples.iterrows():
    case_id = r['case_id']
    out_row = df_out[df_out['case_id'] == case_id].iloc[0]
    steps = json.loads(out_row['steps_json'])
    resources = [s['resource_id'] for s in steps]
    acts = df_act[df_act['resource_id'].isin(resources)]
    print(f"=== {case_id} ({r['email']}) req: {r['requested_at']} rep: {r['reported_at']} audit: {r['audit_at']} ===")
    print("Resources in output:", resources)
    for _, a in acts.iterrows():
        print(f"   act: {a['activity_id']} | {a['event_time']} | {a['event_type']} | {a['source_system']} -> {a['target_system']} | res: {a['resource_id']} | res_val: {a['reported_result']}")
        print(f"        details: {a['details']}")
