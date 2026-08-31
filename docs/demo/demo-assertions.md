# PayRecover AI — Demo Assertion Checklist

These assertions are verified automatically during every dry-run of the demo script.

---

## Technical Assertion Checklist

| Step | Target Component | Asserted Behavior / Query | Required Output |
| :--- | :--- | :--- | :--- |
| **AST-01** | Webhook Ingest | Verify HMAC-SHA256 signature verification | HTTP 200 OK |
| **AST-02** | Decision Room UI | Fetch case `pay_demo_happy_001` via API | JSON contains `action: "retry_payment"`, `eniv > 0`, `safety_checks: "PASSED"` |
| **AST-03** | State Machine | Check state of `pay_demo_happy_001` after retry | State transitions to `CAPTURED` |
| **AST-04** | Deduplication | Re-post `evt_duplicate_test_002` | `duplicate_execution_count` increments by 1 |
| **AST-05** | Race Handling | Check status of `pay_demo_race_003` | Status equals `CANCELLED_STALE`; `stale_action_rejection_count` increments by 1 |
| **AST-06** | LLM Fail-Closed | Post malformed output to decision pipeline | `policy_validation_failure_count` increments by 1; zero unauthorized calls |
| **AST-07** | Kill Switch | Attempt action while kill switch is active | `kill_switch_rejection_count` increments by 1; zero external calls |
| **AST-08** | Audit Integrity | Verify cryptographic hash chain on audit log | All block hashes verify successfully (`SHA256(prev_hash + data)`) |
