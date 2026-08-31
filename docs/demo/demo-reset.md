# PayRecover AI — Demo Environment Reset Procedure

To ensure 100% clean, repeatable demo executions, run this reset procedure before recording or live presentations:

---

## 1-Command Reset

```bash
python -m scripts.demo_reset --seed 42
```

## Detailed Actions Performed
1. Flush in-memory / Redis cache state for mock webhooks.
2. Truncate demo database tables (`payment_cases`, `actions_in_flight`, `audit_ledger`).
3. Re-seed demo database with canonical baseline merchant policies (`merchant_id: "merch_demo_01"`).
4. Reset all runtime safety telemetry counters to 0.
5. Re-initialize SHA-256 genesis block for the cryptographic audit log.
6. Verify local FastAPI server is healthy (`GET /health` returns `200 OK`).
