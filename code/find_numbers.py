import os

for root, dirs, files in os.walk('dataset'):
    for f in files:
        p = os.path.join(root, f)
        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                txt = fp.read()
                if '6645' in txt:
                    print(f"6645 found in: {p}")
                if '5569' in txt:
                    print(f"5569 found in: {p}")
        except Exception:
            pass
