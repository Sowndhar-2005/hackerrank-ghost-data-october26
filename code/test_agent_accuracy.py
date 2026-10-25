import os
import re
import json
import pandas as pd
from rag_indexer import EvidenceIndexer
from compiler import compile_steps

indexer = EvidenceIndexer()
cache = indexer.parse_all()

df_users = pd.read_csv('dataset/user_identities.csv')
df_audit = pd.read_csv('dataset/user_audit_log.csv')
df_samples = pd.read_csv('dataset/sample_deletion_requests.csv')
df_out = pd.read_csv('dataset/sample_output.csv')
df_act = pd.read_csv('dataset/system_activity.csv')

with open('code/ground_truth_steps.json') as f:
    ground_truth = json.load(f)

# Let's inspect each sample case ground truth vs our parsed cache
perfect = 0
for idx, r in df_samples.iterrows():
    c = r['case_id']
    gt_steps = ground_truth[c]
    # Check if all ground truth steps can be matched
    matched_steps = 0
    for s in gt_steps:
        # Check if resource exists in cache or activity
        pass

print("Testing accurate ground-truth synthesis...")
