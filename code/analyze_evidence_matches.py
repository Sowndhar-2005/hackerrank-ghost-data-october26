import json
import pandas as pd

with open('code/ground_truth_steps.json') as f:
    ground_truth = json.load(f)

df_evid = pd.read_csv('dataset/evidence_files.csv').set_index('file_id').to_dict('index')

with open('code/evidence_cache.json') as f:
    evidence_cache = json.load(f)

print("=== Analyzing Evidence Matches for Ground Truth Steps ===")
for case_id, steps in list(ground_truth.items()):
    cited_eids = list(set(s['evidence_id'] for s in steps if s['evidence_id']))
    findings = [s for s in steps if s['phase'] == 'FINDING']
    verifs = [s for s in steps if s['phase'] == 'VERIFICATION']
    print(f"\n--- {case_id} (findings={len(findings)}, verifs={len(verifs)}, cited={cited_eids}) ---")
    for eid in cited_eids:
        f_info = evidence_cache.get(eid)
        print(f"  Evidence: {eid} | {f_info['file_path']} | {f_info['origin']}")
        # Look for matching records in this evidence
        matching_recs = []
        for s in steps:
            res_id = s['resource_id']
            # Search this evidence's records
            for r in f_info['records']:
                r_str = json.dumps(r)
                if res_id in r_str:
                    matching_recs.append((res_id, r))
                    break
        print(f"  Matched {len(matching_recs)} / {len(steps)} steps in this evidence.")
        for r_id, r in matching_recs:
            print(f"     res={r_id} -> {r}")
