import json
import pandas as pd

with open('code/ground_truth_steps.json') as f:
    ground_truth = json.load(f)

with open('code/evidence_cache.json') as f:
    cache = json.load(f)

df_act = pd.read_csv('dataset/system_activity.csv')
df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')

for idx, r in df_samples.iterrows():
    c = r['case_id']
    steps = ground_truth[c]
    print(f"\n==================== {c} ({r['email']}) ====================")
    for s in steps:
        res = s['resource_id']
        sys_id = s['system_id']
        phase = s['phase']
        op = s['operation']
        st = s['state']
        evid = s.get('evidence_id', '')
        
        # Check where res appears in evidence
        ev_matches = []
        for fid, finfo in cache.items():
            for rec in finfo['records']:
                if rec.get('resource_id') == res:
                    ev_matches.append((fid, finfo['captured_at'], rec))
                    break
                    
        # Check where res appears in activity
        acts = df_act[df_act['resource_id'] == res]
        act_summary = [(a['activity_id'], a['event_time'], a['event_type'], a['reported_result']) for _, a in acts.iterrows()]
        
        print(f"Step: {phase} | {sys_id} | {res} | {op} | {st} | evid: '{evid}'")
        if ev_matches:
            for em in ev_matches:
                print(f"   In evid {em[0]} ({em[1]}): {em[2]}")
        if act_summary:
            print(f"   In act: {act_summary}")
