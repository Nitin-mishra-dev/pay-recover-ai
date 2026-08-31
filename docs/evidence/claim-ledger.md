# PayRecover AI — Authoritative Claim Ledger

This ledger is the single source of truth for all public, README, pitch video, and documentation claims.
**No claim may appear in public materials without a corresponding `VERIFIED` entry in this table.**

---

## Authoritative Claim Ledger

| Claim ID | Claim Type | Public Claim Description | Verified Value | Evidence Source | Exact Verification Command / Script | Generated Artifact File | Verification Date | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CLM-001** | `SIMULATION RESULT` | Net Incremental Value (NIV) mean uplift over Static Rules | **+8.92% (Mean NIV: ₹1.934M vs ₹1.776M)** | `eval/results/` | `python -m eval.run --split holdout --seeds 42,43,44,45,46 --n 10000` | `eval/results/benchmark_holdout_multiseed.json` | 2026-08-31 | **VERIFIED** |
| **CLM-002** | `SIMULATION RESULT` | Recovery revenue uplift vs Baseline 0 (No Action Organic Floor) | **+749.47% (₹2.195M vs ₹0.258M)** | `eval/results/` | `python -m eval.run --split holdout --seeds 42,43,44,45,46 --n 10000` | `eval/results/benchmark_holdout_multiseed.json` | 2026-08-31 | **VERIFIED** |
| **CLM-003** | `ENGINEERING PROPERTY` | Duplicate payment executions under race conditions | **0 duplicate executions (Strict 0)** | Test Suite | `pytest tests/integration/test_concurrency.py` | Pytest Execution (17/17 passed) | 2026-08-31 | **VERIFIED** |
| **CLM-004** | `ENGINEERING PROPERTY` | Stale retry cancellation on `payment.captured` race | **100.0% rejected / cancelled** | State Machine Tests | `pytest tests/unit/test_state_machine.py` | Pytest Execution (17/17 passed) | 2026-08-31 | **VERIFIED** |
| **CLM-005** | `ENGINEERING PROPERTY` | Malformed reasoner output fail-closed rate | **100.0% safe fail-closed** | Red Team Suite | `pytest tests/unit/test_policy_engine.py` | Pytest Execution (17/17 passed) | 2026-08-31 | **VERIFIED** |
| **CLM-006** | `ENGINEERING PROPERTY` | Global Kill Switch execution blockage | **< 50ms (0 leaks)** | Safety Tests | `pytest tests/unit/test_safety_kernel.py` | Pytest Execution (17/17 passed) | 2026-08-31 | **VERIFIED** |
| **CLM-007** | `FACT` | Razorpay webhook at-least-once delivery & event ID deduplication | **x-razorpay-event-id** | Razorpay Docs | Razorpay Webhook Best Practices Documentation | `docs/buildathon/track-03-requirements.md` | 2026-08-31 | **VERIFIED** |

---

## Claim Verification Protocol

1. Run the exact command listed in the ledger.
2. Inspect the output artifact JSON / log.
3. Compare the generated number with the README text.
4. If there is any discrepancy, update the README to match the exact generated artifact.
5. Never edit ledger values manually without regenerating the artifact.
