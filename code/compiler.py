import json

OPERATION_ORDER = {
    # Findings
    "REPORT_REMAINING_RECORD": 1,
    "REPORT_EXPOSED_PII": 2,
    "REPORT_ACTIVE_DATA_FLOW": 3,
    "REPORT_RESTORE_RISK": 4,
    # Remediation
    "DISABLE_DATA_FLOW": 1,
    "BLOCK_RESTORE": 2,
    "DELETE_RECORD": 3,
    "REDACT_RECORD": 4,
    "ANONYMIZE_RECORD": 5,
    # Verification
    "VERIFY_RECORD_ABSENT": 1,
    "VERIFY_RECORD_PRESENT": 2,
    "VERIFY_RECORD_REDACTED": 3,
    "VERIFY_RECORD_ANONYMIZED": 4,
    "VERIFY_DATA_FLOW_DISABLED": 5,
    "VERIFY_RESTORE_BLOCKED": 6,
}

PHASE_ORDER = {
    "FINDING": 1,
    "REMEDIATION": 2,
    "VERIFICATION": 3,
}

def step_sort_key(step):
    p_rank = PHASE_ORDER.get(step['phase'], 99)
    op_rank = OPERATION_ORDER.get(step['operation'], 99)
    sys_id = str(step.get('system_id') or '')
    res_id = str(step.get('resource_id') or '')
    return (p_rank, op_rank, sys_id, res_id)

def compile_steps(steps):
    """
    Sorts, deduplicates, and renumbers steps according to strict hackathon spec.
    """
    if not steps:
        return []

    # Deduplicate while preserving fields
    seen = set()
    unique_steps = []
    for s in steps:
        key = (s['phase'], s['system_id'], s['resource_id'], s['operation'], s['state'])
        if key not in seen:
            seen.add(key)
            unique_steps.append(s)

    # Sort
    unique_steps.sort(key=step_sort_key)

    # Assign consecutive step_no starting at 1
    compiled = []
    for idx, s in enumerate(unique_steps, 1):
        step_dict = {
            "step_no": idx,
            "phase": s["phase"],
            "system_id": s["system_id"],
            "resource_id": s["resource_id"],
            "operation": s["operation"],
            "state": s["state"],
            "evidence_id": s.get("evidence_id", "")
        }
        compiled.append(step_dict)

    return compiled

if __name__ == '__main__':
    with open('code/ground_truth_steps.json') as f:
        ground_truth = json.load(f)

    # Validate that re-compiling ground truth matches original order perfectly
    mismatches = 0
    for case_id, steps in ground_truth.items():
        recompiled = compile_steps(steps)
        if len(recompiled) != len(steps):
            print(f"Length mismatch on {case_id}: {len(recompiled)} vs {len(steps)}")
            mismatches += 1
            continue
        for s1, s2 in zip(recompiled, steps):
            for k in ['phase', 'system_id', 'resource_id', 'operation', 'state']:
                if s1[k] != s2[k]:
                    print(f"Diff on {case_id} step {s1['step_no']}: {k} {s1[k]} vs {s2[k]}")
                    mismatches += 1
                    break
    if mismatches == 0:
        print("100% sort key alignment on all ground truth steps!")
