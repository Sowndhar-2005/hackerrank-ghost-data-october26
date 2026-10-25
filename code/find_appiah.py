import os

for root, dirs, files in os.walk('dataset'):
    for f in files:
        if f.endswith(('.log', '.txt', '.json', '.sql')):
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                    if 'k.appiah88@gmail.com' in content:
                        print(f"Found k.appiah in {p}")
                    if 'audit_record_4902' in content:
                        print(f"Found audit_record_4902 in {p}")
            except Exception:
                pass
