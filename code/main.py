import os
import sys
import json
import time
import argparse
import pandas as pd

# Add local directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import DeletionAuditAgent

def main():
    parser = argparse.ArgumentParser(description="Ghost Data Still Exists - Deletion Audit Agent")
    parser.add_argument('--input', default='dataset/deletion_requests.csv', help='Path to deletion requests CSV')
    parser.add_argument('--output', default='output.csv', help='Path to output CSV')
    parser.add_argument('--dataset_dir', default='dataset', help='Path to dataset directory')
    args = parser.parse_args()

    print("==================================================================")
    print("HackerRank Orchestrate: Ghost Data Still Exists — Audit Agent")
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print("==================================================================")

    start_time = time.time()
    agent = DeletionAuditAgent(dataset_dir=args.dataset_dir)
    print(f"Loaded evidence cache and agent models in {time.time() - start_time:.2f}s")

    df_requests = pd.read_csv(args.input)
    total_cases = len(df_requests)
    print(f"Auditing {total_cases} requests...")

    results = []
    status_counts = {'COMPLETE': 0, 'INCOMPLETE': 0, 'NOT_APPLICABLE': 0}

    for idx, row in df_requests.iterrows():
        case_id = row['case_id']
        res = agent.audit_case(row)
        results.append(res)
        status_counts[res['deletion_status']] = status_counts.get(res['deletion_status'], 0) + 1
        if (idx + 1) % 50 == 0 or (idx + 1) == total_cases:
            print(f"Processed {idx + 1}/{total_cases} cases (Elapsed: {time.time() - start_time:.1f}s)...")

    # Sort results by case_id
    results.sort(key=lambda x: (
        int(x['case_id'].split('_')[1]) if x['case_id'].startswith('case_') and x['case_id'].split('_')[1].isdigit() else 999999,
        x['case_id']
    ))

    df_out = pd.DataFrame(results, columns=['case_id', 'deletion_status', 'steps_json'])

    # Write to target output path
    df_out.to_csv(args.output, index=False)
    print(f"\nWrote {len(df_out)} rows to {args.output}")

    # Also write to dataset/output.csv if output was root output.csv
    if args.output == 'output.csv' or os.path.basename(args.output) == 'output.csv':
        alt_path = os.path.join(args.dataset_dir, 'output.csv')
        df_out.to_csv(alt_path, index=False)
        print(f"Also wrote {len(df_out)} rows to {alt_path}")

    elapsed = time.time() - start_time
    print("==================================================================")
    print(f"Audit completed in {elapsed:.2f}s ({elapsed / total_cases * 1000:.1f}ms per case)")
    print(f"Summary: COMPLETE={status_counts.get('COMPLETE', 0)}, "
          f"INCOMPLETE={status_counts.get('INCOMPLETE', 0)}, "
          f"NOT_APPLICABLE={status_counts.get('NOT_APPLICABLE', 0)}")
    print("==================================================================")

if __name__ == '__main__':
    main()
