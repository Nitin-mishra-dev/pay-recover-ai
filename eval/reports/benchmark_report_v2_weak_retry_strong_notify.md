# PayRecover AI — Economic Evaluation Benchmark Report
**Generated At**: `2026-08-31T15:03:52.601118+00:00` | **Split**: `HOLDOUT` | **World**: `V2_WEAK_RETRY_STRONG_NOTIFY`
**Configuration**: Seeds: 2 | Cases per Seed: 2,000 in Holdout | Total Evaluated Observations: 4,000

---

## 1. Headline Selection Metrics
* **PayRecover AI Mean Net Incremental Value (NIV)**: **₹1,638,250.00** (Total: ₹3,276,500.00)
* **Static Rules Engine Mean NIV**: ₹1,466,842.60 (Total: ₹2,933,685.20)
* **Oracle Upper Bound Mean NIV**: **₹3,440,449.00** (Policy Efficiency: **47.62%**)
* **Uplift Statement**: **+11.69% Net Incremental Value uplift (+₹342,814.80 across all 4,000 holdout transactions, or an average of +₹171,407.40 per 2,000-case seed batch)**
* **Recovery Uplift over No Action Floor**: **+627.3%**
* **Safety Violations**: **0**

---

## 2. Multi-Seed Comparative Leaderboard
| Strategy | Mean Recovered Revenue | Mean Cost | Mean Net Incremental Value (NIV) | Std Dev | Mean Recovery Rate | Mean Action Regret | Policy Efficiency | Brier Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Baseline 0: No Action** | ₹261,542.00 | ₹0.00 | **₹0.00** | ±₹0.00 | 6.19% | ₹1,720.20 | 0.00% | 0.0740 |
| **Baseline 1: Blind Retry** | ₹886,948.00 | ₹1,000.00 | **₹624,406.00** | ±₹21,508.77 | 20.98% | ₹1,407.99 | 18.15% | 0.2500 |
| **Baseline 2: Static Rules Engine** | ₹1,730,490.00 | ₹2,105.40 | **₹1,466,842.60** | ±₹66,313.18 | 40.95% | ₹986.78 | 42.64% | 0.3155 |
| **Baseline 3: PayRecover AI** | ₹1,902,186.00 | ₹2,394.00 | **₹1,638,250.00** | ±₹54,336.57 | 45.00% | ₹901.07 | 47.62% | 0.3269 |
| **Baseline 4: Oracle Upper Bound** | ₹3,707,530.50 | ₹5,539.50 | **₹3,440,449.00** | ±₹74,870.39 | 87.67% | ₹0.00 | 100.00% | 0.0000 |

---

## 3. Scientific Invariants Verified
1. **Non-Circularity**: True latent outcomes generated upstream by `HiddenWorldPhysics`, completely sealed from policy scoring.
2. **Zero Holdout Leakage**: Evaluation performed on isolated holdout split without hyperparameter or prompt tuning.
3. **Oracle Upper Bound**: Latent counterfactual oracle guarantees theoretical maximum NIV bound ($NIV_{Oracle} \ge NIV_{PayRecover} \ge NIV_{Static}$).
4. **Heterogeneous Optimization**: PayRecover dynamic actions balance immediate retries on healthy rails, delayed retries on degraded rails, customer SMS/Email links, and support escalations.
5. **Truthful Telemetry**: Zero duplicate executions or uncontracted actions across all evaluations.