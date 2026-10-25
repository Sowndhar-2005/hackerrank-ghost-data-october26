import pandas as pd
df_users = pd.read_csv('dataset/user_identities.csv')
m = df_users[df_users['email'] == 'amina.elmasri@gmail.com']
print(m)
