# Deterministic Policy-Decision Execution Pipeline

```
                     ┌────────────────────────────────────┐
                     │ LLM / Reasoner JSON Proposal       │
                     └─────────────────┬──────────────────┘
                                       │
                                       ▼
                     [Stage 1: Schema Validation]
                       Fail Closed if malformed / extra fields
                                       │
                                       ▼
                      [Stage 2: Parameter Bounds Check]
                        Fail closed if parameters exceed allowed bounds
                                        │
                                        ▼
                      [Stage 3: Policy Compliance]
                        Merchant limits, frequency caps, channel rules
                                        │
                                        ▼
                      [Stage 4: Safety Authorization]
                        Hard ceilings, DND checks, fraud filters
                                        │
                                        ▼
                      [Stage 5: State Freshness Check]
                        Verify payment not captured, disputed, refunded
                                        │
                                        ▼
                      [Stage 6: Global Kill Switch]
                        Check runtime kill-switch flag before acquiring lock
                                        │
                                        ▼
                      [Stage 7: Idempotency Lock]
                        Atomic lock on hash(payment_id, action, attempt)
                                        │
                                        ▼
                      [Stage 8: Deterministic Execution]
                        Execute external API with immutable audit log
```

## Stage Descriptions

1. **Schema Validation**: Validates the raw decision JSON against [`policy-decision-schema.json`](file:///home/nitin-mishra/Workspace/Active/pay%20recover%20ai/docs/product-specs/policy-decision-schema.json). Any missing field, unrecognized action enum, or extra attribute causes immediate rejection and increments `policy_validation_failure_count`.
2. **Parameter Bounds Verification (Fail-Closed)**: Verifies delay bounds ($0 \le t \le 86400$) and expiry intervals ($5 \le t \le 10080$). Fails closed on out-of-bounds parameters with `STAGE_2_INVALID_DELAY_BOUNDS` / `STAGE_2_INVALID_EXPIRY_BOUNDS` instead of silently clamping.
3. **Policy Compliance**: Verifies the decision respects active merchant policies (e.g., maximum daily notifications, allowed contact channels).
4. **Safety Authorization**: Verifies global hard limits (maximum 3 retries, minimum 300s cooldown, risk threshold).
5. **Payment State Freshness**: Queries the authoritative local database / Redis state store to verify the payment is still in `FAILED` status. If a newer `payment.captured` event arrived, the action is marked `STALE_REJECTED` and increments `stale_action_rejection_count`.
6. **Global Kill Switch**: Evaluates the global emergency kill-switch boolean. If enabled, immediately halts execution, records `KILL_SWITCH_BLOCKED`, and increments `kill_switch_rejection_count` *prior* to acquiring the idempotency lock to prevent burning execution leases during emergency stops.
7. **Idempotency Lock**: Acquires an atomic lock / database uniqueness constraint on the calculated `idempotency_key`. If already acquired or executed, returns `DUPLICATE_IGNORED` / `STAGE_7_IDEMPOTENCY_CONFLICT` and increments `duplicate_execution_attempt_count`.
8. **Deterministic Execution & Audit**: Constructs the exact Razorpay API request payload with the `Idempotency-Key` header, dispatches the HTTP call, and commits a cryptographically verifiable SHA-256 hash-chained audit entry.
