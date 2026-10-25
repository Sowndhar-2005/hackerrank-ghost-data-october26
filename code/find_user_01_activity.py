import pandas as pd
df = pd.read_csv('dataset/system_activity.csv')
for col in ['details', 'resource_id']:
    m = df[df[col].str.contains('user_01|amina', case=False, na=False)]
    if not m.empty:
        print(f"Match in {col}:")
        print(m[['activity_id', 'event_time', 'event_type', 'source_system', 'target_system', 'resource_id', 'details']])
