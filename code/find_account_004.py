import os

for root, dirs, files in os.walk('dataset'):
    for f in files:
        if f.endswith(('.csv', '.json', '.txt', '.log', '.sql')):
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                    if 'account_004' in fp.read():
                        print(f"Found account_004 in {p}")
            except Exception:
                pass
