import json

with open('code/ground_truth_steps.json') as f:
    data = json.load(f)

for case_id, steps in data.items():
    findings = [s for s in steps if s['phase'] == 'FINDING']
    remeds = [s for s in steps if s['phase'] == 'REMEDIATION']
    verifs = [s for s in steps if s['phase'] == 'VERIFICATION']
    status = "COMPLETE" if not findings else "INCOMPLETE"
    print(f"=== {case_id} ({status}) ===")
    if findings:
        print("  FINDINGS:")
        for s in findings:
            print(f"    - {s['system_id']} | {s['resource_id']} | {s['operation']} | {s['state']} | evid: {s['evidence_id']}")
    if remeds:
        print("  REMEDIATION:")
        for s in remeds:
            print(f"    - {s['system_id']} | {s['resource_id']} | {s['operation']} | {s['state']}")
    print("  VERIFICATION:")
    for s in verifs:
        print(f"    - {s['system_id']} | {s['resource_id']} | {s['operation']} | {s['state']} | evid: '{s['evidence_id']}'")
