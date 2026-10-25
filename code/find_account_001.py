import os

for root, dirs, files in os.walk('dataset'):
    for f in files:
        if f.endswith(('.csv', '.json', '.txt', '.log', '.sql')):
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                    if 'account_001' in content:
                        print(f"Found account_001 in {p}")
            except Exception:
                pass
