---
name: benchmark-audit
description: Audits PayRecover evaluation methodology for leakage, circular simulation, unfair baselines, reproducibility, and misleading financial metrics.
---

# Benchmark Audit

Verify:

- outcome generation is independent
- model never sees hidden ground truth
- test and training populations are separated where applicable
- baselines are fair
- seeds are recorded
- metrics are reproducible
- monetary calculations are internally consistent
- action costs are included
- natural recovery is accounted for where modeled
- no metric is inflated by simulator design

Run the benchmark.

Inspect results.

Recompute headline metrics independently.

Reject any result that cannot be reproduced.

Output:

DATASET AUDIT
METHODOLOGY AUDIT
BASELINE AUDIT
METRIC AUDIT
REPRODUCIBILITY AUDIT
FINAL VERDICT
