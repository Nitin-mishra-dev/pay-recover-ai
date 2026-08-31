# PayRecover AI — "What Broke & How We Handled It" Failure Demonstration

A top-tier Track 03 submission directly demonstrates edge-case failures, race conditions, and defensive engineering.

---

## 4 Concrete Failure Scenarios Demonstrated in Video / Live Evaluation

### 1. The Race Condition: `payment.captured` Wins
* **The Failure**: A customer manually pays on another device while an automated smart retry is queued with a 5-minute delay.
* **The Risk**: Charging the customer twice, triggering chargebacks and regulatory scrutiny.
* **The Defense**: State observer intercepts `payment.captured`, cancels the pending retry job in Redis/DB, and logs `STALE_ACTION_CANCELLED`.

### 2. The Adversarial / Hallucinated LLM Output
* **The Failure**: An LLM hallucinates an arbitrary non-contract action (e.g. `{"action": "issue_full_refund_and_bonus"}`).
* **The Risk**: Unauthorized financial drain or unpermitted merchant mutations.
* **The Defense**: Pydantic/JSON Schema validation rejects the payload immediately at Stage 1 of the decision pipeline. Fails closed with zero execution.

### 3. Asynchronous Webhook Duplicate Flood
* **The Failure**: Razorpay gateway retries webhook delivery 5 times within 1 second due to network flap.
* **The Risk**: 5 separate recovery workflows spun up simultaneously for the same payment.
* **The Defense**: Ingestion layer uses an atomic `SETNX` lock on `x-razorpay-event-id`. Only the first request executes; 4 duplicates return HTTP 200 `duplicate_ignored`.

### 4. Global Kill Switch Under System Maintenance
* **The Failure**: Merchant notices unexpected payment anomalies across their core banking partner and toggles the kill switch.
* **The Risk**: Automated agent continuing to execute retries and notifications during banking downtime.
* **The Defense**: Pre-execution check halts all in-flight jobs within 50ms, safely buffering events for later replay.
