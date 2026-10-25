import pandas as pd
from datetime import datetime, timedelta

df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
df_act = pd.read_csv('dataset/system_activity.csv')

# Convert event_time and reported_at to datetime
df_act['dt'] = pd.to_datetime(df_act['event_time'])
df_samples['rep_dt'] = pd.to_datetime(df_samples['reported_at'])

# Check matching deletion_worker activities within 2 hours before reported_at
for idx, r in df_samples.iterrows():
    c = r['case_id']
    rep_time = r['rep_dt']
    window_start = rep_time - timedelta(hours=3)
    window_end = rep_time + timedelta(minutes=15)
    
    worker_acts = df_act[
        (df_act['source_system'] == 'deletion_worker') &
        (df_act['dt'] >= window_start) &
        (df_act['dt'] <= window_end)
    ]
    print(f"{c} (rep: {r['reported_at']}): found {len(worker_acts)} deletion_worker acts in window")
    resources = worker_acts['resource_id'].tolist()
    print(f"   resources: {resources}")
