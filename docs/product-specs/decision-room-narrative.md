# PayRecover AI — Decision Room UI Narrative Flow

The Decision Room is the primary screen in PayRecover AI. It tells a complete, counterfactual, transparent story for every at-risk transaction.

---

## The 12-Step Counterfactual Decision Walkthrough

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           THE DECISION ROOM NARRATIVE                           │
│                                                                                 │
│   1. ₹X AT RISK           ► Total lost revenue on this failed payment           │
│   2. WHY?                 ► Extracted gateway error code + contextual failure   │
│   3. RECOVERABILITY       ► Baseline recovery vs predicted uplift score         │
│   4. CANDIDATE OPTIONS    ► Evaluated actions (Retry, Link, Escalate, No Action)│
│   5. EXPECTED VALUE (EV)  ► Gross expected recovery in INR                      │
│   6. INTERVENTION COST    ► Direct gateway fees + contact annoyance penalty     │
│   7. RECOMMENDED ACTION   ► Selected action maximizing Net Incremental Value    │
│   8. WHY THIS ACTION?     ► Structured LLM reasoning synthesis                 │
│   9. SAFETY CHECKS        ► Policy limits, cooldown, retry cap, DND, idempotency│
│  10. EXECUTION STATE      ► Scheduled delay / executing / completed             │
│  11. OBSERVED RESULT      ► Payment captured / link paid / terminal status      │
│  12. NET VALUE REALIZED   ► Final incremental profit delivered to merchant      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## UI Component Wireframe

* **Header**: Payment ID, Order ID, Customer Tier, Time of Failure, Amount (₹).
* **Failure Analysis Card**: Error category (`SOFT_DECLINE`), Root Cause summary, Bank Gateway health status score (0-100).
* **Action Comparison Matrix Table**:
  | Candidate Action | Predicted Lift ($\Delta P$) | Expected Gross Value | Cost of Intervention | Expected Net Incremental Value ($\text{ENIV}$) | Status |
  | :--- | :--- | :--- | :--- | :--- | :--- |
  | `retry_payment` (300s delay) | +78% | ₹3,510.00 | ₹0.50 | **+₹3,509.50** | **SELECTED** |
  | `notify_payment_link` (SMS) | +42% | ₹1,890.00 | ₹2.20 | +₹1,887.80 | Alternative |
  | `escalate_to_support` | +60% | ₹2,700.00 | ₹50.00 | +₹2,650.00 | Alternative |
  | `no_action` | 0% | ₹0.00 | ₹0.00 | ₹0.00 | Rejected |
* **Safety & Invariant Verification Card**:
  - [x] Retry ceiling $< 3$ (Attempt 1 of 3)
  - [x] Cooldown elapsed (320s since failure)
  - [x] Payment state validated (`FAILED`, not captured)
  - [x] Idempotency key generated (`sha256:8f2a...`)
  - [x] Global kill switch `INACTIVE`
* **Execution & Cryptographic Audit Hash**: Shows live API response status and SHA-256 block hash in immutable audit log.
