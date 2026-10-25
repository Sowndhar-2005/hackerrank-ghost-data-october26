import pandas as pd
import json

df_act = pd.read_csv('dataset/system_activity.csv')
p_acts = df_act[df_act['details'].str.contains('Deletion worker submitted primary profile', na=False)].copy()
p_acts['dt'] = pd.to_datetime(p_acts['event_time'])

with open('code/ground_truth_steps.json') as f:
    gt_all = json.load(f)

df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
for idx in [27, 28, 29, 30, 31]:
    r = df_samples.iloc[idx]
    c = r['case_id']
    st = r['reported_status']
    gt_steps = gt_all[c]
    gt_acc = None
    for s in gt_steps:
        if s['system_id'] == 'account_service' and 'account_' in s['resource_id']:
            gt_acc = s['resource_id']
            break
            
    rep_dt = pd.to_datetime(r['reported_at'])
    cands = p_acts[(p_acts['dt'] <= rep_dt) & (p_acts['dt'] >= rep_dt - pd.Timedelta(hours=2))].copy()
    expected_res = 'SUCCESS' if st == 'COMPLETE' else ('PARTIAL' if st == 'PARTIALLY_COMPLETE' else 'FAILED')
    matched = cands[cands['reported_result'] == expected_res]
    res_list = matched['resource_id'].tolist()
    print(f"{c} (GT={gt_acc}, st={st}): Matched {res_list}")
