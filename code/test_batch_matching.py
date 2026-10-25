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

# Build a mapping from email / user_id to deletion activity batch
def find_user_resources(user_id, emails, reported_at):
    # Search system_activity within 3 hours of reported_at
    rep_dt = pd.to_datetime(reported_at)
    w_start = (rep_dt - pd.Timedelta(hours=3)).isoformat()
    w_end = (rep_dt + pd.Timedelta(minutes=30)).isoformat()
    
    sub = df_act[(df_act['source_system'] == 'deletion_worker') & 
                 (df_act['event_time'] >= w_start) & 
                 (df_act['event_time'] <= w_end)]
    
    # Check which activities relate to this user
    # If user has an explicit resource in evidence, match that batch
    return sub

print("Analyzing sample cases...")
