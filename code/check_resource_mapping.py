import json
import pandas as pd

with open('code/ground_truth_steps.json') as f:
    gt_all = json.load(f)

with open('code/evidence_cache.json') as f:
    cache = json.load(f)

df_users = pd.read_csv('dataset/user_identities.csv')
df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')

# Build mapping of user_id -> email
u_to_e = {}
e_to_u = {}
for idx, r in df_users.iterrows():
    u_to_e[r['user_id']] = r['email'].lower()
    e_to_u[r['email'].lower()] = r['user_id']

# Map all resources to user
res_to_user = {}
for fid, finfo in cache.items():
    for rec in finfo['records']:
        r_id = rec.get('resource_id')
        if not r_id:
            continue
        # Find which user this rec mentions
        u_match = None
        for ref_col in ['user_id', 'customer_reference', 'subject_reference', 'subject_ref', 'lookup_key']:
            v = rec.get(ref_col)
            if v and isinstance(v, str):
                v_clean = v.strip('"\'')
                if v_clean in u_to_e:
                    u_match = v_clean
                    break
                if v_clean.lower() in e_to_u:
                    u_match = e_to_u[v_clean.lower()]
                    break
        for em_col in ['email', 'requester_email', 'customer_email', 'owner_email']:
            v = rec.get(em_col)
            if v and isinstance(v, str) and v.strip('"\'').lower() in e_to_u:
                u_match = e_to_u[v.strip('"\'').lower()]
                break
        if u_match:
            if r_id not in res_to_user:
                res_to_user[r_id] = set()
            res_to_user[r_id].add(u_match)

print(f"Total mapped resources: {len(res_to_user)}")

# Check ground truth steps
matched_res = 0
total_res = 0
for idx, r in df_samples.iterrows():
    c = r['case_id']
    u_id = e_to_u.get(r['email'].lower())
    gt_steps = gt_all[c]
    for s in gt_steps:
        total_res += 1
        r_id = s['resource_id']
        mapped = res_to_user.get(r_id, set())
        if u_id in mapped:
            matched_res += 1
        else:
            print(f"{c} ({u_id}): {s['system_id']} {r_id} not mapped to {u_id} (mapped to: {mapped})")

print(f"\nResource Mapping Coverage: {matched_res}/{total_res} ({matched_res/total_res*100:.1f}%)")
