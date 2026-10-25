import pandas as pd
import json

df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
df_out = pd.read_csv('dataset/sample_output.csv')
df_act = pd.read_csv('dataset/system_activity.csv')

with open('code/ground_truth_steps.json') as f:
    ground_truth = json.load(f)

for idx, r in df_samples.iterrows():
    c = r['case_id']
    steps = ground_truth[c]
    acc_steps = [s for s in steps if s['system_id'] == 'account_service']
    acc_res = acc_steps[0]['resource_id'] if acc_steps else None
    
    # Check activity
    acts = df_act[(df_act['target_system'] == 'account_service') & (df_act['resource_id'] == acc_res)]
    act_ids = acts['activity_id'].tolist() if not acts.empty else []
    print(f"{c}: acc_res={acc_res} -> in activity: {act_ids}")
