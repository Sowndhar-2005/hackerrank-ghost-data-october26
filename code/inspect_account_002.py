import pandas as pd
df = pd.read_csv('dataset/system_activity.csv')
print(df[df['resource_id'] == 'account_002'].to_dict('records'))
