# HackerRank Orchestrate - October 2026

## Ghost Data Still Exists: AI Deletion-Audit Agent

Official Challenge & Submission URL:  
https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists

---

## 1. System Architecture

The solution implements an end-to-end autonomous audit pipeline designed around a **Goal -> Plan -> Act -> Observe -> Decide** cognitive loop and a **Hybrid Multimodal RAG** indexer:

```
                  +--------------------------------+
                  |    Customer Deletion Request   |
                  +---------------+----------------+
                                  |
                                  v
                  +--------------------------------+
                  |  PLAN: Request Intent Parser   |
                  |  (Identifies Non-Deletion)     |
                  +---------------+----------------+
                                  |
        +-------------------------+-------------------------+
        | Deletion Request                                  | Non-Deletion Inquiry
        v                                                   v
+-------------------------------+                  +-------------------+
| ACT: Multi-Hop Identity Graph |                  |  NOT_APPLICABLE   |
| (Current & Historical PII)    |                  |  steps_json: []   |
+---------------+---------------+                  +-------------------+
                |
                v
+-------------------------------+
| ACT: Multimodal RAG Retrieval |
| (SQLite, JSON, Logs, Docs)    |
+---------------+---------------+
                |
                v
+-------------------------------+
| OBSERVE: Temporal State Replay|
| (Zero-Trust vs Claims at t<=t*|
+---------------+---------------+
                |
                v
+-------------------------------+
| DECIDE: Policy Decision Engine|
| (Apply deletion_rules.csv)    |
+---------------+---------------+
                |
                v
+-------------------------------+
| COMPILER: Deterministic Steps |
| (Sort Phase -> Op -> Sys-> Res|
+---------------+---------------+
                |
                v
+-------------------------------+
| Output Row in output.csv      |
+-------------------------------+
```

### Core Components:
1. **Multimodal & Structured RAG Indexer (`code/rag_indexer.py`)**:
   - Indexes all evidence under `dataset/evidence/` into an optimized cache (`code/evidence_cache.json`).
   - Executes `.sql` snapshots in SQLite in-memory databases (`:memory:`), unpacking nested JSON columns (`customer_data_primary`, `customer_data_read_replica`, `customer_accounts_failover_replica`).
   - Traces distributed logging pipelines across services, correlating asynchronous events by `trace_id` so context (`subject_ref`, `correlation_key`) propagates across lines.
   - Extracts structured facts from PDFs and text handover exports.

2. **Agentic Audit Loop (`code/agent.py`)**:
   - **Goal**: Audit `case_id` at `audit_at` to determine `deletion_status` (`COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE`).
   - **Plan**: Inspect `request_text` to verify authorization. If non-deletion (e.g. data portability, marketing unsubscribe, address update), output `NOT_APPLICABLE` with `[]`.
   - **Act**: Resolve connected identity graph (current and historical emails, names, phone numbers, and email hashes from `user_identities.csv` and `user_audit_log.csv`).
   - **Observe**: Reconstruct true ground-truth state at `audit_at`. Treats reported statuses as unverified claims and inspects actual database replicas, search indices, support tickets, and backup configs.
   - **Decide**: Evaluates each discovered record against `deletion_rules.csv`. Detects remaining records, exposed PII on account tombstones, active sync bridges, and unblocked restore risks.

3. **Strict Deterministic Step Compiler (`code/compiler.py`)**:
   - Formats steps strictly per schema: `step_no`, `phase`, `system_id`, `resource_id`, `operation`, `state`, `evidence_id`.
   - Enforces canonical phase order: `FINDING` -> `REMEDIATION` -> `VERIFICATION`.
   - Enforces operation table order:
     * `FINDING`: `REPORT_REMAINING_RECORD` -> `REPORT_EXPOSED_PII` -> `REPORT_ACTIVE_DATA_FLOW` -> `REPORT_RESTORE_RISK`
     * `REMEDIATION`: `DISABLE_DATA_FLOW` -> `BLOCK_RESTORE` -> `DELETE_RECORD` -> `REDACT_RECORD` -> `ANONYMIZE_RECORD`
     * `VERIFICATION`: `VERIFY_RECORD_ABSENT` -> `VERIFY_RECORD_PRESENT` -> `VERIFY_RECORD_REDACTED` -> `VERIFY_RECORD_ANONYMIZED` -> `VERIFY_DATA_FLOW_DISABLED` -> `VERIFY_RESTORE_BLOCKED`
   - Secondary sorts by `system_id` ascending, `resource_id` ascending.
   - Renumbers consecutive integers starting at 1.

---

## 2. Setup & Execution

### Prerequisites:
- Python 3.10+
- Dependencies: `pandas`, `pypdf`, `pillow` (all standard or installed via requirements)

### Running the Full Audit (518 Cases):
```bash
python code/main.py
```

This autonomously:
1. Loads the pre-indexed evidence cache and dataset tables.
2. Audits all 518 evaluation requests in `dataset/deletion_requests.csv`.
3. Validates output rows and writes predictions to BOTH `output.csv` (repository root) AND `dataset/output.csv`.
4. Prints execution statistics and verification summary.

### Validating on Sample Ground Truth (32 Cases):
```bash
python code/validate_samples.py
```

---

## 3. Evaluation & Usage Reports

As required by challenge specifications, detailed markdown reports are located in `code/evaluation/` and `evaluation/`:
- `code/evaluation/evaluation_report.md`: Case-level, step-level, and sequence accuracy, 3 custom end-to-end evaluation cases, failure analysis, and architectural improvements.
- `code/evaluation/usage_report.md`: Model provider accounting, token counts (input/output/total), latency, and per-request cost breakdown.

---

## 4. Packaging the Submission

To generate the required `code.zip`:

**Windows (PowerShell):**
```powershell
Compress-Archive -Path README.md, code, evaluation -DestinationPath code.zip -Force
```

**Linux / macOS:**
```bash
zip -r code.zip README.md code evaluation -x "*/__pycache__/*" "*/.git/*"
```

The submission package contains:
- `code.zip`: Complete runnable codebase, prompts, and evaluation reports (no `dataset/`, `.env`, or secrets).
- `output.csv`: Complete 518-row prediction file at repository root.
- `chat_transcript`: Root `log.txt` generated during the session per `AGENTS.md`.
