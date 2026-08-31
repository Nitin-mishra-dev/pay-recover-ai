# PayRecover AI — Authoritative Claim Ledger

This ledger is the single source of truth for all public, README, pitch video, and documentation claims.
**No claim may appear in public materials without a corresponding `VERIFIED` entry in this table.**

---

## Authoritative Claim Ledger

| Claim ID | Public Claim Description | Verified Value | Evidence Source | Exact Verification Command / Script | Generated Artifact File | Verification Date | Reproducibility Status | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CLM-001** | Net Incremental Value (NIV) uplift over Static Rules | *To be generated* | `eval/report.json` | `python -m eval.run --split holdout --seed 42 --n 10000` | `eval/results/benchmark_holdout_s42.json` | *Pending Run* | 100% Deterministic (`seed=42`) | `PENDING_BENCHMARK` |
| **CLM-002** | Recovery rate uplift vs Baseline 0 (No Action) | *To be generated* | `eval/report.json` | `python -m eval.run --split holdout --seed 42 --n 10000` | `eval/results/benchmark_holdout_s42.json` | *Pending Run* | 100% Deterministic (`seed=42`) | `PENDING_BENCHMARK` |
| **CLM-003** | Duplicate payment executions under race conditions | **0 duplicate executions** | Test Suite | `pytest tests/integration/test_concurrency.py` | `eval/results/race_test_output.log` | *Pending Run* | 100% Deterministic | `PENDING_TEST` |
| **CLM-004** | Stale retry rejection on `payment.captured` race | **100% rejected / cancelled** | State Machine Tests | `pytest tests/unit/test_state_machine.py` | `eval/results/state_test_output.log` | *Pending Run* | 100% Deterministic | `PENDING_TEST` |
| **CLM-005** | Malformed LLM output fail-closed rate | **100% safe fallback** | Red Team Suite | `pytest tests/red_team/test_adversarial_inputs.py` | `eval/results/red_team_output.log` | *Pending Run* | 100% Deterministic | `PENDING_TEST` |
| **CLM-006** | Global Kill Switch response and blockage | **0 unauthorized executions** | Safety Tests | `pytest tests/unit/test_safety_kernel.py` | `eval/results/safety_test_output.log` | *Pending Run* | 100% Deterministic | `PENDING_TEST` |

---

## Claim Verification Protocol

1. Run the exact command listed in the ledger.
2. Inspect the output artifact JSON / log.
3. Compare the generated number with the README text.
4. If there is any discrepancy, update the README to match the exact generated artifact.
5. Never edit ledger values manually without regenerating the artifact.
