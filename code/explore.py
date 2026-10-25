import pandas as pd
import json

def inspect():
    for f in ['user_identities.csv', 'user_audit_log.csv', 'system_activity.csv', 'deletion_rules.csv', 'evidence_files.csv']:
        df = pd.read_csv(f'dataset/{f}')
        print(f"=== {f} (shape: {df.shape}) ===")
        print("Columns:", df.columns.tolist())
        print(df.head(2))
        print()

if __name__ == '__main__':
    inspect()
