import os
import re

audit_map = {}
for root, dirs, files in os.walk('dataset'):
    for f in files:
        p = os.path.join(root, f)
        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                txt = fp.read()
                matches = re.findall(r'audit_record_\d+', txt)
                for m in set(matches):
                    if m not in audit_map:
                        audit_map[m] = []
                    audit_map[m].append(p)
        except Exception:
            pass

print(f"Total distinct audit_record IDs found in dataset: {len(audit_map)}")
print("Sample audit_record mappings:")
for k in list(audit_map.keys())[:10]:
    print(k, "->", audit_map[k])
