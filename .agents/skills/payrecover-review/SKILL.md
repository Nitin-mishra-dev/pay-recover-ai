---
name: payrecover-review
description: Reviews PayRecover AI changes for correctness, architecture, payment-state safety, economic logic, evaluation quality, and buildathon defensibility.
---

# PayRecover Review Skill

When reviewing any PayRecover change, inspect:

1. Correctness
2. State transitions
3. Safety
4. Idempotency
5. Economic reasoning
6. Evaluation integrity
7. Error handling
8. Test coverage
9. Documentation
10. Buildathon relevance

## Review sequence

Inspect diff.

Trace data flow.

Trace state transitions.

Identify trust boundaries.

Check failure paths.

Check tests.

Run relevant tests.

Then classify findings:

CRITICAL
HIGH
MEDIUM
LOW

Do not praise before identifying weaknesses.

A change is not approved merely because tests pass.

Ask whether it creates:
- hidden financial risk
- evaluation leakage
- duplicated behavior
- stale state
- unexplained decisions
- misleading metrics

Return:

VERDICT:
APPROVE / APPROVE WITH FIXES / REJECT

CRITICAL FINDINGS:
...

RECOMMENDED FIXES:
...

VERIFICATION:
commands and observed outputs
