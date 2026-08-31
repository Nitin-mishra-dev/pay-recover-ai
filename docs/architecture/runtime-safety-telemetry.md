# PayRecover AI — Runtime Safety Telemetry & Counters

Rather than relying on decorative UI indicators, PayRecover tracks real, hard runtime safety metrics using atomic in-memory/database counters.

---

## Authoritative Safety Counters

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              PAYRECOVER SAFETY TELEMETRY                               │
├──────────────────────────────────────┬─────────────────────────────────────────────────┤
│ duplicate_event_count                │ Total duplicate webhooks received and ignored   │
│ duplicate_execution_attempt_count    │ Duplicate financial execution attempts blocked  │
│ stale_action_rejection_count         │ Scheduled retries aborted due to newer capture  │
│ unauthorized_action_count            │ Actions blocked by safety kernel / policy       │
│ kill_switch_rejection_count          │ Actions halted by global emergency stop         │
│ policy_validation_failure_count      │ Malformed LLM / input payloads failed closed    │
│ partial_execution_count              │ Ambiguous network timeouts safely contained     │
└──────────────────────────────────────┴─────────────────────────────────────────────────┘
```

### Telemetry Counter Specifications

1. **`duplicate_event_count`**:
   * **Trigger**: Incremented whenever an incoming webhook payload carries an `x-razorpay-event-id` that has already been ingested.
   * **Expected Value**: $\ge 0$ (demonstrates active webhook deduplication).
2. **`duplicate_execution_attempt_count`**:
   * **Trigger**: Incremented if an internal execution worker attempts to dispatch an action for which an idempotency lock already exists.
   * **Expected Value**: **0** (Invariant: duplicate executions are strictly prevented).
3. **`stale_action_rejection_count`**:
   * **Trigger**: Incremented whenever a scheduled retry is cancelled/rejected because the payment has transitioned to `CAPTURED`, `REFUNDED`, or `DISPUTED`.
   * **Expected Value**: Matches number of race-condition events.
4. **`unauthorized_action_count`**:
   * **Trigger**: Incremented whenever a proposed action violates hard merchant limits (e.g. retry ceiling exceeded, cooldown violation, DND active).
   * **Expected Value**: Matches number of invalid candidate actions proposed.
5. **`kill_switch_rejection_count`**:
   * **Trigger**: Incremented when an action is blocked because `GLOBAL_KILL_SWITCH = true`.
6. **`policy_validation_failure_count`**:
   * **Trigger**: Incremented whenever an LLM reasoning payload fails JSON Schema validation or produces an unrecognized enum.
7. **`partial_execution_count`**:
   * **Trigger**: Incremented if a downstream API call experiences a network timeout (e.g. HTTP 504) and is safely transitioned to `IN_FLIGHT_PENDING_RECON` without duplicate re-attempts.
