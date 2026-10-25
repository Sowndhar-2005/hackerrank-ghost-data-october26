import os

target_audits = [
    'audit_record_4902', 'audit_record_6645', 'audit_record_5569',
    'audit_record_4128', 'audit_record_7095', 'audit_record_3954', 'audit_record_1707'
]

for ta in target_audits:
    found = []
    for root, dirs, files in os.walk('dataset'):
        for f in files:
            if f.endswith(('.csv', '.json', '.txt', '.log', '.sql')):
                p = os.path.join(root, f)
                try:
                    with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                        if ta in fp.read():
                            found.append(p)
                except Exception:
                    pass
    print(f"{ta} found in: {found}")
