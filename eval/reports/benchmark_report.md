# PayRecover AI — Economic Evaluation Benchmark Report
**Generated At**: `2026-08-31T14:48:17.256851+00:00` | **Split**: `HOLDOUT` | **Seeds**: `[42, 43, 44, 45, 46]`
**Evaluated Transactions**: `10,000` (`2,000` per seed)

---

## 1. Headline Selection Metrics
* **PayRecover AI Mean Net Incremental Value (NIV)**: **₹1,934,406.94**
* **Static Rules Engine Mean NIV**: ₹1,775,967.42
* **NIV Uplift over Static Rules**: **+8.92%**
* **Recovery Uplift over No Action Floor**: **+749.47%**
* **Safety Violations**: **0**

---

## 2. Multi-Seed Comparative Leaderboard
| Strategy | Mean Recovered Revenue | Mean Cost | Mean Net Incremental Value (NIV) | Std Dev | Mean Recovery Rate | Mean Action Regret | Brier Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Baseline 0: No Action** | ₹258,429.40 | ₹0.00 | **₹0.00** | ±₹0.00 | 6.07% | ₹1,741.71 | 0.0736 |
| **Baseline 1: Blind Retry** | ₹1,567,950.00 | ₹1,000.00 | **₹1,308,520.60** | ±₹70,329.39 | 36.85% | ₹1,087.45 | 0.2500 |
| **Baseline 2: Static Rules Engine** | ₹2,036,539.20 | ₹2,142.38 | **₹1,775,967.42** | ±₹27,069.51 | 47.88% | ₹853.72 | 0.2505 |
| **Baseline 3: PayRecover AI** | ₹2,195,274.80 | ₹2,438.46 | **₹1,934,406.94** | ±₹56,422.78 | 51.60% | ₹774.51 | 0.2400 |

---

## 3. Scientific Invariants Verified
1. **Non-Circularity**: True latent outcomes generated upstream by `HiddenWorldPhysics`, completely sealed from policy scoring.
2. **Zero Holdout Leakage**: Evaluation performed on isolated holdout split without hyperparameter or prompt tuning.
3. **Heterogeneous Optimization**: PayRecover dynamic actions balance immediate retries on healthy rails, delayed retries on degraded rails, customer SMS/Email links, and support escalations.
4. **Truthful Telemetry**: Zero duplicate executions or uncontracted actions across all evaluations.