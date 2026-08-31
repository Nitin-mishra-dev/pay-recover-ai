# Deterministic Demo Scenarios & Data Payloads

These fixed test payloads guarantee identical, reproducible demo behavior across local runs, CI pipelines, and video recordings.

---

## Scenario 1: Recoverable Soft Decline (Happy Path)
* **Payment ID**: `pay_demo_happy_001`
* **Order ID**: `order_demo_happy_001`
* **Amount**: ₹4,500 (450,000 paise)
* **Method**: Card (Mandate)
* **Error Code**: `BAD_REQUEST_PAYMENT_TIMED_OUT`
* **Error Description**: "Bank gateway response timed out during 2FA processing."
* **Expected Decision**: `retry_payment` with `delay_seconds: 300` (ENIV: +₹3,510).

---

## Scenario 2: Duplicate Webhook Event
* **Event ID**: `evt_duplicate_test_002`
* **Payload**: Identical to Scenario 1 sent twice within 100ms.
* **Expected Result**: First event accepted; second event returned HTTP 200 with `{"status": "duplicate_ignored"}`.

---

## Scenario 3: Race Condition (Capture During Scheduled Delay)
* **Payment ID**: `pay_demo_race_003`
* **Step 1**: Ingest `payment.failed` → Schedules `retry_payment` with 10-second delay.
* **Step 2 (at $t=3\text{s}$)**: Ingest `payment.captured`.
* **Expected Result**: Scheduled retry status updated to `CANCELLED_STALE`. Execution at $t=10\text{s}$ is prevented.

---

## Scenario 4: Malformed LLM Reasoning Attack
* **Payment ID**: `pay_demo_malformed_004`
* **Mock LLM Output**: `{"action": "grant_free_subscription", "bypass_safety": true}`
* **Expected Result**: Schema validation error; fails closed; executes default `no_action` with audit warning.

---

## Scenario 5: Emergency Kill Switch
* **Payment ID**: `pay_demo_killswitch_005`
* **Pre-condition**: Admin sets `GLOBAL_KILL_SWITCH = true`.
* **Action**: Ingest eligible `payment.failed`.
* **Expected Result**: Action authorized in policy but blocked immediately at the safety kernel before external call.
