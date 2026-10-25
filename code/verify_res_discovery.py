import os
import re
import json
import pandas as pd
from datetime import datetime, timedelta

df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
df_out = pd.read_csv('dataset/sample_output.csv')
df_act = pd.read_csv('dataset/system_activity.csv')
df_evid = pd.read_csv('dataset/evidence_files.csv').set_index('file_id').to_dict('index')

with open('code/ground_truth_steps.json') as f:
    ground_truth = json.load(f)

with open('code/evidence_cache.json') as f:
    evidence_cache = json.load(f)

# Inspect deletion batches in system_activity
# Every time deletion_worker runs, it processes resources.
# Let's map each sample case to its exact resources from ground truth and check their activities
print("Verifying resource origins across all 32 cases:")
matched_res_count = 0
total_gt_res = 0

for idx, r in df_samples.iterrows():
    c = r['case_id']
    gt_steps = ground_truth[c]
    res_set = set(s['resource_id'] for s in gt_steps)
    total_gt_res += len(res_set)
    
    # Check if these resources appear in activity or in evidence
    found_in_act = set(df_act[df_act['resource_id'].isin(res_set)]['resource_id'])
    
    # Check evidence
    found_in_evid = set()
    for eid, finfo in evidence_cache.items():
        if finfo['captured_at'] <= r['audit_at']:
            for rec in finfo['records']:
                r_str = json.dumps(rec)
                for res_id in res_set:
                    if res_id in r_str:
                        found_in_evid.add(res_id)
                        
    all_found = found_in_act.union(found_in_evid)
    diff = res_set - all_found
    if not diff:
        matched_res_count += len(res_set)
    else:
        print(f"{c}: missed {diff}")

print(f"Total GT resources: {total_gt_res}, Discovered: {matched_res_count}")
