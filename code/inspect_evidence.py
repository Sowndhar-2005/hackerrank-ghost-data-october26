import pandas as pd
from pathlib import Path

df_evid = pd.read_csv('dataset/evidence_files.csv')
for origin, group in df_evid.groupby('origin'):
    print(f"=== {origin} ({len(group)} files) ===")
    for idx, r in group.head(2).iterrows():
        print(f"   {r['file_id']}: {r['file_path']}")
