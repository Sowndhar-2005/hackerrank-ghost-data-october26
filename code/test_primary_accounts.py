import pandas as pd
import json

df_act = pd.read_csv('dataset/system_activity.csv')
p_acts = df_act[df_act['details'].str.contains('Deletion worker submitted primary profile', na=False)].copy()
p_acts['dt'] = pd.to_datetime(p_acts['event_time'])

with open('code/ground_truth_steps.json') as f:
    gt_all = json.load(f)

df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
correct = 0
for idx, r in df_samples.iterrows():
    c = r['case_id']
    gt_steps = gt_all[c]
    gt_acc = None
    for s in gt_steps:
        if s['system_id'] == 'account_service' and 'account_' in s['resource_id']:
            gt_acc = s['resource_id']
            break
            
    rep_dt = pd.to_datetime(r['reported_at'])
    cands = p_acts[(p_acts['dt'] <= rep_dt + pd.Timedelta(minutes=5)) & (p_acts['dt'] >= rep_dt - pd.Timedelta(hours=3))].copy()
    if not cands.empty:
        cands['dist'] = (rep_dt - cands['dt']).abs()
        closest = cands.sort_values('dist').iloc[0]['resource_id']
        match = (closest == gt_acc)
        if match:
            correct += 1
        print(f"{c}: GT={gt_acc} Predicted={closest} Match={match}")
    else:
        print(f"{c}: GT={gt_acc} NO CANDIDATES")

print(f"Total account matches: {correct}/{len(df_samples)}")
