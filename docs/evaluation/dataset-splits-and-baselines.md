# Evaluation Dataset Splits & Locked Baseline Specifications

To ensure zero evaluation data leakage and defensible claims, PayRecover AI enforces strict data partitioning and immutable baseline definitions.

---

## 1. Dataset Partitioning Standard

All synthetic transaction evaluation batches are generated with deterministic random seeds and partitioned into three isolated splits:

```
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│       DEV SPLIT (60%)        │       TEST SPLIT (20%)       │      HOLDOUT SPLIT (20%)     │
│       N = 6,000 cases        │       N = 2,000 cases        │       N = 2,000 cases        │
├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ • Model training & tuning    │ • Hyperparameter selection   │ • Zero-tuning sealed eval    │
│ • Prompt engineering         │ • Prompt calibration         │ • Final benchmark numbers    │
│ • Feature exploration        │ • Error analysis             │ • Claim ledger verification  │
└──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```

### Strict Partitioning Invariants
* **Hidden Ground Truth**: The simulator determines actual counterfactual outcomes using an independent latent probability matrix based on customer tenure, gateway health, decline category, and attempt history. The agent never observes this matrix.
* **Sealed Holdout**: The `HOLDOUT` split is evaluated exactly once per release cycle via `python -m eval.run --split holdout --seed 42`. No model parameters, prompt templates, or policy thresholds may be modified after viewing holdout results.

---

## 2. Locked Baseline Specifications

To avoid moving targets or unfair comparisons, the four evaluated baselines are locked and frozen:

### Baseline 0: `No Action` (Floor)
* **Strategy**: Do nothing upon receiving a `payment.failed` event.
* **Mechanism**: Record the loss. Only natural customer-initiated reattempts (if any) succeed.
* **Purpose**: Measures the absolute floor and quantifies natural organic recovery without intervention.

### Baseline 1: `Blind Retry` (Naïve Heuristic)
* **Strategy**: Blindly retry all failed payments once after a fixed 5-minute delay.
* **Mechanism**: Dispatches `retry_payment` with fixed delay $t = 300\text{s}$ for all decline codes, including hard declines. Max attempts = 1.
* **Cost Incurred**: ₹0.50 gateway fee per retry across 100% of failed payments.
* **Purpose**: Demonstrates the cost inefficiency and fraud exposure of uncalibrated retries.

### Baseline 2: `Static Rules Engine` (Industry Standard)
* **Strategy**: Deterministic rule table based solely on decline codes:
  * If `SOFT_DECLINE` (e.g. temporary insufficient funds, bank timeout): Retry at fixed intervals (6h, 24h, 72h) up to 3 attempts.
  * If `HARD_DECLINE` (e.g. stolen card, invalid credentials): Halt immediately / No Action.
  * If `CUSTOMER_ACTIONABLE` (e.g. 3DS timeout): Send 1 SMS notification after 15 minutes.
* **Purpose**: Represents modern standard payment gateway dunning rules without ML or degradation awareness.

### Baseline 3: `PayRecover AI` (Proposed Decision Engine)
* **Strategy**: Counterfactual uplift scoring + Degradation-aware timing + Deterministic safety gate:
  * Predicts individual treatment effect $\tau_i$ for each candidate action.
  * Adjusts retry delay dynamically based on real-time gateway latency / error SLO spikes.
  * Selects action that maximizes Net Incremental Value ($\text{NIV}$).
  * Halts or escalates when $\text{ENIV} \le 0$.
