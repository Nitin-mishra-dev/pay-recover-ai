# Competition Readiness Workflow

The master, end-to-end orchestration procedure to verify full submission readiness before tagging a release.

---

## 6-Stage Execution Pipeline

```
1. BENCHMARK
   ↓
2. RED-TEAM
   ↓
3. EVIDENCE AUDIT
   ↓
4. DEMO AUDIT
   ↓
5. ADVERSARIAL JUDGE
   ↓
6. RELEASE CHECK
```

---

## Stage 1: Benchmark Execution (`/benchmark`)
* Run complete evaluation suite on the sealed holdout split:
  ```bash
  python -m eval.run --split holdout --seed 42 --n 10000
  ```
* Verify all 4 baselines run (`No Action`, `Blind Retry`, `Static Rules`, `PayRecover`).
* Verify output artifacts in `eval/results/` and `eval/report/`.

## Stage 2: Adversarial Red-Team Attack (`/red-team`)
* Execute the complete red-team test suite covering the 5D State-Space Matrix:
  ```bash
  pytest tests/red_team/ tests/integration/test_concurrency.py
  ```
* Assert zero duplicate executions, zero stale action executions, zero unauthorized actions, and 100% fail-closed rate on malformed inputs.

## Stage 3: Evidence & Claim Ledger Audit
* Cross-reference all numbers in `README.md` against `docs/evidence/claim-ledger.md` and `eval/report.json`.
* Block release if any claim lacks a matching `VERIFIED` artifact.

## Stage 4: Deterministic Demo Audit
* Run the demo reset script:
  ```bash
  python -m scripts.demo_reset --seed 42
  ```
* Execute the 5-minute demo assertions checklist (`docs/demo/demo-assertions.md`).
* Ensure all happy-path and failure-path scenarios pass deterministically.

## Stage 5: Adversarial Judge Simulation
* Run the `buildathon-judge` skill against the codebase, docs, and demo script.
* Ensure all Top 5 Critical Judge Fixes have been addressed.

## Stage 6: Final Release Check (`/release-check`)
* Verify repo cleanliness, absence of secrets/API keys, git diff, and packaging.
* Produce final verdict: `RELEASE`, `RELEASE WITH FIXES`, or `BLOCK RELEASE`.
