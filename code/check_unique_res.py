import os
import json
import pandas as pd

with open('code/ground_truth_steps.json') as f:
    ground_truth = json.load(f)

# Let's inspect the exact set of resources for each sample case
for case_id, steps in ground_truth.items():
    res_list = [f"{s['system_id']}:{s['resource_id']}" for s in steps]
    # deduplicate preserving order
    seen = set()
    uniq = []
    for r in res_list:
        if r not in seen:
            seen.add(r)
            uniq.append(r)
    print(f"{case_id}: {uniq}")
