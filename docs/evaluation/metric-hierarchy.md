# PayRecover AI — Metric Hierarchy & Mathematical Formulations

PayRecover AI rejects misleading vanity metrics (such as raw recovery rate). The entire system is governed by a strict hierarchy of business, economic, and safety metrics evaluated via an independent counterfactual simulation environment and estimated incremental value optimization.

---

## 1. Action-Level Selection Metric: Expected Incremental Value ($\text{IEV}$)

For evaluating any candidate action $a \in \mathcal{A}$ given transaction context $x$:

$$\text{IncrementalProbability}(a \mid x) = P(\text{recovery} \mid a, x) - P(\text{natural recovery} \mid \text{no action}, x)$$

$$\mathbf{IEV}(a \mid x) = \left[ \text{IncrementalProbability}(a \mid x) \times \text{PaymentValue} \right] - \text{ActionCost}(a) - \text{RiskPenalty}(a)$$

Where:
* $P(\text{natural recovery} \mid \text{no action}, x)$: The baseline probability that the customer would have re-attempted and succeeded organically without any merchant intervention.
* $\text{ActionCost}(a)$: Direct gateway fee (₹0.50) + channel communication costs (₹0.20 SMS / ₹0.02 Email) + customer annoyance penalty.
* $\text{RiskPenalty}(a)$: $P(\text{fraud} \mid x) \times (\text{PaymentValue} + C_{\text{chargeback}})$.

**Optimal Decision Rule**:
$$a^* = \arg\max_{a \in \mathcal{A}} \mathbf{IEV}(a \mid x) \quad \text{subject to } \mathbf{IEV}(a^*) > 0 \text{ and Safety Gate Approval}$$

---

## 2. Benchmark Realized Metric: Net Incremental Value ($\text{NIV}$)

Across an evaluation batch $\mathcal{D} = \{ (X_i, Z_i) \}_{i=1}^N$:

$$\mathbf{NIV} = \left( R_{\text{PayRecover}} - R_{\text{Baseline}} \right) - C_{\text{Intervention}}$$

Where:
* $R_{\text{PayRecover}}$: Total INR recovered by PayRecover across the evaluation batch.
* $R_{\text{Baseline}}$: Total INR recovered under the baseline strategy (e.g. `No Action` or `Static Rules`) on the identical batch.
* $C_{\text{Intervention}}$: Total realized intervention costs across all executed actions.

---

## 3. Secondary Economic & Efficiency Metrics

1. **Incremental Recovery Uplift ($\Delta R$)**:
   $$\Delta R = \frac{R_{\text{PayRecover}} - R_{\text{Baseline}}}{R_{\text{Baseline}}} \times 100\%$$
2. **Cost per Recovered Rupee (CPRR)**:
   $$\text{CPRR} = \frac{C_{\text{Intervention}}}{R_{\text{PayRecover}} - R_{\text{Baseline 0}}}$$
3. **Intervention Rate**:
   $$\text{Intervention Rate} = \frac{N_{\text{Interventions}}}{N_{\text{Failed Payments}}} \times 100\%$$
4. **False Positive Intervention Rate**:
   $$\text{FP Rate} = \frac{\text{Interventions on Permanently Unrecoverable Failures}}{N_{\text{Permanently Unrecoverable}}} \times 100\%$$

---

## 4. Runtime Safety & State Correctness Metrics

Every evaluation batch must track and report safety invariant adherence:

| Metric Name | Formula / Definition | Target Threshold |
| :--- | :--- | :--- |
| **Duplicate Event Count** | $N_{\text{duplicate\_webhooks\_ingested}}$ | Tracked ($\ge 0$) |
| **Duplicate Execution Attempt Count** | $N_{\text{duplicate\_executions\_attempted}}$ | **0 (Strict Invariant)** |
| **Stale Action Rejection Rate** | $\frac{N_{\text{stale\_actions\_blocked}}}{N_{\text{race\_condition\_events}}}$ | **100.0% Blocked** |
| **Unauthorized Action Rate** | $\frac{N_{\text{unauthorized\_actions}}}{N_{\text{total\_proposals}}}$ | **0.0% Executed** |
| **Partial Execution Containment Rate** | $\frac{N_{\text{partial\_execution\_contained}}}{N_{\text{partial\_execution\_injected}}}$ | **100.0% (Contained)** |
| **Unsafe Execution Count** | $N_{\text{unsafe\_executions}}$ | **0 (Strict Invariant)** |
| **Failed-Safe Rate** | $\frac{N_{\text{graceful\_fail\_closed\_on\_error}}}{N_{\text{system\_anomalies}}}$ | **100.0%** |
| **Kill-Switch Response Latency** | Time from toggle to 100% execution blockage | **< 50ms** |
