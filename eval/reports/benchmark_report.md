# PayRecover AI — Economic Evaluation Benchmark Report
**Generated At**: `2026-08-31T15:04:15.924909+00:00` | **Split**: `HOLDOUT` | **World**: `V1_STANDARD`
**Configuration**: Seeds: 5 | Cases per Seed: 2,000 in Holdout | Total Evaluated Observations: 10,000

---

## 1. Headline Selection Metrics
* **PayRecover AI Mean Net Incremental Value (NIV)**: **₹1,934,406.94** (Total: ₹9,672,034.68)
* **Static Rules Engine Mean NIV**: ₹1,775,967.42 (Total: ₹8,879,837.10)
* **Oracle Upper Bound Mean NIV**: **₹3,483,441.42** (Policy Efficiency: **55.53%**)
* **Uplift Statement**: **+8.92% Net Incremental Value uplift (+₹792,197.58 across all 10,000 holdout transactions, or an average of +₹158,439.52 per 2,000-case seed batch)**
* **Recovery Uplift over No Action Floor**: **+749.47%**
* **Safety Violations**: **0**

---

## 2. Multi-Seed Comparative Leaderboard
| Strategy | Mean Recovered Revenue | Mean Cost | Mean Net Incremental Value (NIV) | Std Dev | Mean Recovery Rate | Mean Action Regret | Policy Efficiency | Brier Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Baseline 0: No Action** | ₹258,429.40 | ₹0.00 | **₹0.00** | ±₹0.00 | 6.07% | ₹1,741.71 | 0.00% | 0.0736 |
| **Baseline 1: Blind Retry** | ₹1,567,950.00 | ₹1,000.00 | **₹1,308,520.60** | ±₹70,329.39 | 36.85% | ₹1,087.45 | 37.56% | 0.2500 |
| **Baseline 2: Static Rules Engine** | ₹2,036,539.20 | ₹2,142.38 | **₹1,775,967.42** | ±₹27,069.51 | 47.88% | ₹853.72 | 50.98% | 0.2505 |
| **Baseline 3: PayRecover AI** | ₹2,195,274.80 | ₹2,438.46 | **₹1,934,406.94** | ±₹56,422.78 | 51.60% | ₹774.51 | 55.53% | 0.2400 |
| **Baseline 4: Oracle Upper Bound** | ₹3,746,506.20 | ₹4,635.38 | **₹3,483,441.42** | ±₹77,945.72 | 88.06% | ₹0.00 | 100.00% | 0.0000 |

---

## 3. Scientific Invariants Verified
1. **Non-Circularity**: True latent outcomes generated upstream by `HiddenWorldPhysics`, completely sealed from policy scoring.
2. **Zero Holdout Leakage**: Evaluation performed on isolated holdout split without hyperparameter or prompt tuning.
3. **Oracle Upper Bound**: Latent counterfactual oracle guarantees theoretical maximum NIV bound ($NIV_{Oracle} \ge NIV_{PayRecover} \ge NIV_{Static}$).
4. **Heterogeneous Optimization**: PayRecover dynamic actions balance immediate retries on healthy rails, delayed retries on degraded rails, customer SMS/Email links, and support escalations.
5. **Truthful Telemetry**: Zero duplicate executions or uncontracted actions across all evaluations.