import pandas as pd
df_act = pd.read_csv('dataset/system_activity.csv')
for idx, r in df_act[df_act['target_system'] == 'account_service'].tail(30).iterrows():
    print(r['activity_id'], r['event_time'], r['event_type'], r['resource_id'], r['reported_result'], r['details'])
