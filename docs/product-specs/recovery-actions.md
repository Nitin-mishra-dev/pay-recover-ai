# PAYRECOVER AI — CANONICAL RECOVERY ACTION CONTRACT

This specification is the authoritative, machine-readable contract for all executable interventions within PayRecover AI.
The LLM and decision reasoner may **only** evaluate, score, and recommend actions from this catalog. The LLM cannot invent or alter actions.

---

## Action Taxonomy & State Matrix

```
                          ┌───────────────────────────┐
                          │   payment.failed Ingest   │
                          └─────────────┬─────────────┘
                                        │
                         [Filter: Permanent Hard Decline]
                                        ├── (Fraud / Stolen / Lost) ──► ESCALATE_TO_SUPPORT (or NO_ACTION)
                                        │
                                        ▼
                         [Evaluate Candidate Actions]
                                        │
         ┌──────────────────────────────┼──────────────────────────────┐
         ▼                              ▼                              ▼
┌──────────────────┐          ┌───────────────────┐          ┌───────────────────┐
│  RETRY_PAYMENT   │          │ NOTIFY_PAYMENT_   │          │ ESCALATE_TO_      │
│  (Direct API)    │          │ LINK (SMS/Email)  │          │ SUPPORT (Manual)  │
└──────────────────┘          └───────────────────┘          └───────────────────┘
```

---

## 1. Action: `RETRY_PAYMENT`

* **Identifier**: `retry_payment`
* **Description**: Deterministically triggers an automated payment re-attempt via Razorpay's recurring/smart-retry API with degradation-aware delay.
* **Eligibility**:
  * Payment method is recurring card mandate, UPI auto-pay, or server-retriable token.
  * Failure error code is classified as `SOFT_DECLINE` or `GATEWAY_TEMPORARY_ERROR` (e.g., bank timeout, temporary insufficiency, network glitch).
  * Transaction age $< 72$ hours.
  * Retry attempt count $< \text{max\_retries}$ (Merchant limit, default: 3).
* **Inputs**:
  * `payment_id`: string (Authoritative Razorpay payment identifier)
  * `order_id`: string (Razorpay order ID)
  * `amount`: integer (in paise, exact original amount)
  * `currency`: string (e.g., `"INR"`)
  * `delay_seconds`: integer ($0 \le t \le 86400$, adjusted for bank degradation / SLO health)
* **Forbidden States**:
  * `CAPTURED` or `PAID`
  * `REFUNDED`
  * `FRAUD_HOLD` or `DISPUTED`
  * `RETRY_LIMIT_EXCEEDED`
  * `COOLING_DOWN`
  * `AUTOMATION_PAUSED`
* **Risk Level**: `LOW_TO_MEDIUM`
* **Max Retries**: 3 attempts per payment lifecycle.
* **Cooldown**: Minimum 300 seconds between successive retries.
* **Expiry**: Scheduled retry expires in 120 seconds if worker does not claim execution.
* **Expected Value Formulation**:
  $$\text{ENIV} = (P_{\text{recovery}} \times \text{Amount}) - \text{Cost}_{\text{gateway}} - (P_{\text{fraud}} \times \text{Amount})$$
* **Expected Cost**: Direct API/gateway re-attempt fee (default: ₹0.50 per attempt).
* **Required Authorization**: Deterministic Safety Gate clearance (checks kill-switch, merchant policy, idempotency lock).
* **Idempotency Key Formulation**:
  $$\text{idempotency\_key} = \text{SHA256}(\text{"retry:"} + \text{payment\_id} + \text{":"} + \text{attempt\_count})$$
* **Audit Events**:
  * `ACTION_SCHEDULED`
  * `SAFETY_CHECK_PASSED`
  * `EXECUTION_ATTEMPTED`
  * `EXECUTION_SUCCESS` / `EXECUTION_FAILED`
  * `STATE_TRANSITION_CAPTURED` / `STATE_TRANSITION_CANCELLED`
* **Failure Behavior**: On network failure or HTTP 5xx, retry with exponential backoff up to 2 internal attempts; if still failed, record `RETRY_API_FAILED` and flag for review. Fail closed.

---

## 2. Action: `NOTIFY_PAYMENT_LINK`

* **Identifier**: `notify_payment_link`
* **Description**: Generates a fresh, secure Razorpay Payment Link and dispatches a customer-friendly notification via permitted channel (Email / SMS) requesting re-authorization.
* **Eligibility**:
  * Customer contact details (email or phone) verified and compliant with DND / customer communication limits.
  * Failure classified as `CUSTOMER_ACTIONABLE` (e.g., 3DS failure, card expired, insufficient funds requiring top-up).
  * Merchant policy permits customer notification.
  * Customer notification count $< \text{max\_notifications}$ (default: 2 per failed invoice).
* **Inputs**:
  * `payment_id`: string
  * `customer_id`: string
  * `customer_contact`: object (`{"email": "...", "phone": "..."}`)
  * `channel`: enum (`"EMAIL"`, `"SMS"`)
  * `template_id`: string (Pre-approved, non-hallucinated template identifier)
  * `link_expiry_minutes`: integer (default: 1440 mins / 24 hours)
* **Forbidden States**:
  * `CAPTURED` or `PAID`
  * `OPTED_OUT` or `DND_ACTIVE`
  * `MAX_NOTIFICATIONS_REACHED`
  * `FRAUD_HOLD`
  * `AUTOMATION_PAUSED`
* **Risk Level**: `LOW`
* **Max Retries**: 2 customer communications per order.
* **Cooldown**: Minimum 7,200 seconds (2 hours) between customer notifications.
* **Expiry**: Link expires in 24 hours.
* **Expected Value Formulation**:
  $$\text{ENIV} = (P_{\text{customer\_pay}} \times \text{Amount}) - \text{Cost}_{\text{channel}} - \text{Cost}_{\text{annoyance\_penalty}}$$
* **Expected Cost**: ₹0.20 (SMS) / ₹0.02 (Email) + annoyance penalty (modeled at ₹2.00).
* **Required Authorization**: Deterministic policy approval verifying frequency capping and DND status.
* **Idempotency Key Formulation**:
  $$\text{idempotency\_key} = \text{SHA256}(\text{"notify:"} + \text{order\_id} + \text{":"} + \text{channel} + \text{":"} + \text{notification\_count})$$
* **Audit Events**:
  * `LINK_GENERATED`
  * `COMMUNICATION_DISPATCHED`
  * `LINK_OPENED`
  * `PAYMENT_CAPTURED_VIA_LINK`
* **Failure Behavior**: If notification provider fails, queue for single retry in 5 minutes; if payment link creation fails, abort and flag error. Fail closed.

---

## 3. Action: `ESCALATE_TO_SUPPORT`

* **Identifier**: `escalate_to_support`
* **Description**: Freezes automated actions, builds a structured diagnostic case file, and escalates high-value or ambiguous failed transactions to merchant finance/operations team.
* **Eligibility**:
  * Transaction amount $> \text{high\_value\_threshold}$ (e.g., > ₹25,000) with repeated failures.
  * OR Failure reason is ambiguous / complex / potential contract dispute.
  * OR Automated retry limits reached without capture.
* **Inputs**:
  * `case_id`: string
  * `payment_id`: string
  * `amount`: integer
  * `failure_reason`: string
  * `diagnostic_summary`: string (Generated LLM reasoning)
  * `attempt_history`: array of prior attempts
* **Forbidden States**:
  * `CAPTURED`
  * `CASE_ALREADY_ESCALATED`
* **Risk Level**: `ZERO` (Safe fallback)
* **Max Retries**: 1 escalation ticket per case.
* **Cooldown**: N/A
* **Expiry**: Ticket remains open until manual merchant resolution.
* **Expected Value Formulation**:
  $$\text{ENIV} = (P_{\text{manual\_recovery}} \times \text{Amount}) - \text{Cost}_{\text{human\_ops}}$$
* **Expected Cost**: ₹50.00 (estimated merchant operations cost per case).
* **Required Authorization**: Automatic when automated ENIV $\le 0$ or safety bounds exceeded.
* **Idempotency Key Formulation**:
  $$\text{idempotency\_key} = \text{SHA256}(\text{"escalate:"} + \text{case\_id})$$
* **Audit Events**:
  * `AUTOMATION_CEILING_REACHED`
  * `ESCALATION_TICKET_CREATED`
* **Failure Behavior**: Persist escalation record locally; log alert for monitoring if webhook delivery to merchant CRM fails.

---

## 4. Action: `NO_ACTION`

* **Identifier**: `no_action`
* **Description**: Deterministically halts all interventions. Used when expected recovery is negligible, costs exceed gains, or permanent hard decline (stolen card/fraud) is detected.
* **Eligibility**:
  * Hard decline (e.g., card stolen, account closed, permanent blacklisted).
  * OR Expected Net Incremental Value ($\text{ENIV}$) is negative for all candidate actions.
* **Inputs**:
  * `case_id`: string
  * `reason`: string (e.g., `"HARD_DECLINE_STOLEN_CARD"`, `"NEGATIVE_EXPECTED_VALUE"`)
* **Forbidden States**: None.
* **Risk Level**: `ZERO`
* **Max Retries**: N/A
* **Cooldown**: N/A
* **Expiry**: Terminal state.
* **Expected Value Formulation**: $\text{ENIV} = 0$
* **Expected Cost**: ₹0.00
* **Required Authorization**: Automatic when all candidate actions fail safety/policy/economic thresholds.
* **Idempotency Key Formulation**:
  $$\text{idempotency\_key} = \text{SHA256}(\text{"no_action:"} + \text{case\_id})$$
* **Audit Events**:
  * `CASE_CLOSED_NO_ACTION`
  * `REASON_RECORDED`
* **Failure Behavior**: Immediate idempotent write to audit log.
