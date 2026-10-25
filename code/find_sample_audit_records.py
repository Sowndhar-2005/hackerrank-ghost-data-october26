import pandas as pd
import json
import os

df_out = pd.read_csv('dataset/sample_output.csv')
audit_records = {}
for idx, r in df_out.iterrows():
    steps = json.loads(r['steps_json'])
    for s in steps:
        if s['system_id'] == 'security_service':
            audit_records[r['case_id']] = s['resource_id']

print("Sample audit records count:", len(audit_records))
print("Sample audit records:", audit_records)

# Let's search where each audit_record appears in dataset
for case_id, res_id in list(audit_records.items())[:5]:
    found_in = []
    for root, dirs, files in os.walk('dataset'):
        for f in files:
            if f.endswith(('.csv', '.json', '.txt', '.log', '.sql')):
                p = os.path.join(root, f)
                try:
                    with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                        if res_id in fp.read():
                            found_in.append(p)
                except Exception:
                    pass
    print(f"{case_id} ({res_id}) found in: {found_in}")
