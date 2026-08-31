# PayRecover AI — 5-Minute Pitch & Technical Demo Script

This script defines the exact, minute-by-minute narrative and technical sequence for the submission video and live panel evaluation.

---

## 5-Minute Demo Timeline

```
[0:00 - 0:45] The Problem & Economic Thesis
  • Show digital merchant losing ₹10L/month to failed payments.
  • Explain why naive retries waste fees and annoy users: we need Net Incremental Value (NIV).

[0:45 - 2:00] Happy Path: The Decision Room
  • Ingest failed payment webhook (`payment.failed`).
  • Decision Room displays: Amount (₹4,500), Failure Reason (Bank Network Spike), Recoverability (78%).
  • Economic Engine evaluates candidate actions: `retry_payment` with 300s degradation delay yields highest ENIV (+₹3,510).
  • Deterministic Safety Gate validates policy, checks kill-switch, acquires idempotency lock, executes retry.
  • Webhook receives `payment.captured`. Revenue recovered!

[2:00 - 3:30] The Hardening & Failure Proof (What Broke & How We Handled It)
  • Scenario A: Duplicate Webhook Delivery → Deduped instantly via `x-razorpay-event-id`.
  • Scenario B: Race Condition (`payment.captured` arrives while retry is scheduled) → Stale action cancelled.
  • Scenario C: Malformed LLM Output → Fails closed to deterministic static rules without crashing.
  • Scenario D: Emergency Operator Pause → Global Kill Switch immediately blocks execution.

[3:30 - 4:30] The Benchmark & Evidence Proof
  • Run reproducible benchmark on 10,000 cases (`--seed 42`).
  • Show comparative matrix: No Action vs Blind Retry vs Static Rules vs PayRecover AI.
  • Highlight Net Incremental Value (NIV) uplift and zero safety violations.

[4:30 - 5:00] Conclusion & Why PayRecover Wins
  • Summary: Production-grade state safety, counterfactual economic optimization, verifiable audit trail.
```
