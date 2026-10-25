import json
import pandas as pd

for path in ['output.csv', 'dataset/output.csv']:
    df = pd.read_csv(path)
    assert list(df.columns) == ['case_id', 'deletion_status', 'steps_json'], f"Invalid columns: {df.columns}"
    assert len(df) == 518, f"Expected 518 rows, got {len(df)}"
    assert df['case_id'].iloc[0] == 'case_33', f"First case: {df['case_id'].iloc[0]}"
    assert df['case_id'].iloc[-1] == 'case_550', f"Last case: {df['case_id'].iloc[-1]}"
    
    # Check each row JSON
    for idx, r in df.iterrows():
        steps = json.loads(r['steps_json'])
        assert isinstance(steps, list), f"{r['case_id']} steps is not list"
        if r['deletion_status'] == 'NOT_APPLICABLE':
            assert len(steps) == 0, f"{r['case_id']} NOT_APPLICABLE must have empty steps"
        else:
            for i, s in enumerate(steps, 1):
                assert s['step_no'] == i, f"step_no mismatch in {r['case_id']}"
                assert s['phase'] in ['FINDING', 'REMEDIATION', 'VERIFICATION']
                assert 'system_id' in s and 'resource_id' in s and 'operation' in s and 'state' in s
    print(f"Verification PASSED for {path}: 518 valid rows!")
