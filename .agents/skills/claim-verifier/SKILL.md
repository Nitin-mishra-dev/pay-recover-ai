---
name: claim-verifier
description: Independently audits and verifies every factual, quantitative, and performance claim in README, pitch materials, and documentation against executable command outputs and test artifacts.
---

# Claim Verifier Skill

Your job is strict, adversarial epistemic auditing. You ensure that **no claim exists without verifiable, executable proof**.

## Audit Workflow

1. **Extract Claims**: Scan `README.md`, docs, and demo scripts for quantitative metrics (e.g. "X% uplift", "₹Y recovered", "0 duplicate executions", "tamper-evident hash chain").
2. **Locate Claim Type**:
   * `FACT`: Verified external API behavior (e.g. Razorpay at-least-once webhook semantics).
   * `SIMULATION RESULT`: Outcome from benchmark run (`eval/results/benchmark_holdout_s42.json`).
   * `ENGINEERING PROPERTY`: State machine or safety invariant verified by automated test suites.
   * `DESIGN CLAIM`: System architectural decision.
3. **Execute Verification Command**: Run the exact command listed in `docs/evidence/claim-ledger.md` (e.g. `python -m eval.run --split holdout --seed 42 --n 10000` or `pytest tests/integration/test_concurrency.py`).
4. **Compare Values**: Assert that the number in the documentation matches the generated artifact to the exact decimal.
5. **Verdict**:
   * `VERIFIED`: Exact match between text and output artifact.
   * `DRIFT_DETECTED`: Number in docs differs from artifact $\to$ update docs to match artifact.
   * `UNVERIFIED_BLOCKED`: Claim has no executable test or artifact $\to$ block release.

## Output Format

```markdown
# CLAIM VERIFICATION REPORT

## AUDITED CLAIMS SUMMARY
- Total Claims Audited: X
- Verified: Y
- Discrepancies / Drift: Z

## DETAILED CLAIM AUDIT TABLE
| Claim ID | Text Claim | Artifact Value | Command | Status |
| :--- | :--- | :--- | :--- | :--- |
| CLM-001 | +18.4% NIV | +18.42% | python -m eval.run ... | VERIFIED |

## BLOCKERS & DISCREPANCIES
- ...
```
