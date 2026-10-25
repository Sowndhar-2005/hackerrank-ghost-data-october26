import pandas as pd
df = pd.read_csv('dataset/system_activity.csv')
rows = df[df['resource_id'] == 'account_001']
print(rows.to_dict('records'))
