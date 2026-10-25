import pandas as pd
df = pd.read_csv('dataset/system_activity.csv')
print(df.iloc[3595:3612][['activity_id', 'event_time', 'event_type', 'source_system', 'target_system', 'resource_id', 'reported_result', 'details']])
