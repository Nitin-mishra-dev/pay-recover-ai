# PayRecover AI

> **Adaptive Post-Failure Revenue Recovery Decision Engine**  
> *Built for Razorpay AI Buildathon — Track 03 (Autonomous Revenue & Payment Recovery)*

[![CI Tests](https://img.shields.io/badge/tests-45%20passed-emerald.svg)](tests/)
[![NIV Uplift](https://img.shields.io/badge/holdout%20NIV%20uplift-%2B8.92%25%20vs%20Static%20Rules-blue.svg)](eval/reports/benchmark_summary.md)
[![Safety Violations](https://img.shields.io/badge/unsafe%20executions-0%20(strict)-emerald.svg)](src/core/safety_gate.py)
[![Seeds](https://img.shields.io/badge/evaluated%20holdout-10%2C000%20cases-purple.svg)](eval/results/benchmark_holdout_multiseed.json)

---

## 1. Executive Summary & Verified Metrics

PayRecover AI is an intelligent post-failure recovery layer that operates between transaction failure webhooks and merchant intervention execution. Rather than executing blind retries or brittle static schedules, PayRecover evaluates the **Expected Net Incremental Value (IEV)** of every alternative intervention, strictly accounting for natural customer reattempts, direct gateway fees, customer friction penalties, and payment rail health.

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             VERIFIED BENCHMARK RESULTS                            │
│                 (10,000 Sealed Holdout Observations across 5 Seeds)              │
├───────────────────────────────┬─────────────────┬──────────────┬─────────────────┤
│ Metric                        │ Baseline 2      │ Baseline 3   │ PayRecover AI   │
│                               │ (Static Rules)  │ (PayRecover) │ Advantage       │
├───────────────────────────────┼─────────────────┼──────────────┼─────────────────┤
│ Gross Recovered Revenue       │ ₹2,075,188.16   │ ₹2,195,274.80│ +₹120,086.64    │
│ Estimated Natural Recovery    │ ₹258,400.00     │ ₹258,400.00  │ Subtracted      │
│ Gross Recovery Rate           │ 48.79%          │ 51.62%       │ +2.83% pts      │
│ Direct Intervention Costs     │ ₹299,220.74     │ ₹260,867.86  │ -₹38,352.88     │
│ Net Incremental Value (NIV)   │ ₹1,775,967.42   │ ₹1,934,406.94│ +₹158,439.52/sd*│
│ NIV Relative Uplift           │ Baseline        │ +8.92%       │ +8.92% vs Static│
│ Policy Efficiency vs Oracle   │ 50.99%          │ 55.53%       │ +4.54% pts      │
│ Action Regret (Mean)          │ ₹1,707.13       │ ₹1,548.69    │ -9.28% Regret   │
│ Unsafe Executions (Simulated) │ 0               │ 0            │ 0 in test races │
└───────────────────────────────┴─────────────────┴──────────────┴─────────────────┘
* Average incremental gain of +₹158,439.52 per 2,000-case seed batch (+₹792,197.58 aggregate across 10,000 holdout cases).
```

*All metrics recomputable via:* `python3 -m eval.run --split holdout --seeds 42,43,44,45,46 --n 10000`

---

## 2. Positioning: What PayRecover AI Is (and Is Not)

* **What it IS**: A state-safe, economically optimal post-failure intervention decision engine that decides **whether, when, and how** to recover failed payments.
* **What it is NOT**: A replacement for core payment routing infrastructure. Razorpay Optimizer already performs dynamic smart routing across gateways; PayRecover AI operates downstream after an initial terminal failure occurs.

---

## 3. The Core Economic Principle: Estimated Incremental Value (IEV)

A recovery engine that blindly retries every transaction is not intelligent. PayRecover optimizes the Expected Net Incremental Value for each candidate action $a \in \mathcal{A}$:

$$\text{IEV}(a \mid x) = \left[ P(\text{Recovery} \mid x, a) - P(\text{Natural} \mid x) \right] \times \text{Amount} - C(a) - \text{RiskPenalty}(a)$$

Where:
* $P(\text{Natural} \mid x)$: Probability the customer completes payment independently without merchant intervention.
* $C(a)$: Direct API cost (e.g. ₹0.50 retry fee, ₹0.20 SMS, ₹2.00 WhatsApp, ₹50.00 human ops) plus customer annoyance penalty.
* **No-Free-Lunch Rule**: If $\text{IEV}(a \mid x) \le 0$ for all actions, the system selects **`NO_ACTION`**.

---

## 4. The AI Experiment: "We Tested AI. AI Lost."

We ran an identical-condition empirical A/B benchmark comparing **System A (Deterministic PayRecover)** against **System B (Deterministic + Selective LLM Reasoner)** across 10,000 holdout transactions:

```text
=====================================================================================
 A/B EXPERIMENT OUTCOME SUMMARY (10,000 Sealed Holdout Cases across 5 Seeds)
=====================================================================================
 System A (Deterministic Engine) Mean NIV: ₹1,934,406.94
 System B (Selective LLM Engine) Mean NIV: ₹1,842,068.69
 Empirical Delta (System B - System A):    -₹92,338.25 per 2,000-case seed on average
                                           (-₹461,691.25 aggregate across five seeds)
 AI Coverage:                              14.28% (1,428 ambiguous cases routed)
 Total LLM Token Cost:                     ₹104.11
 Average LLM Latency:                      120.0ms (vs <0.1ms deterministic fast path)
=====================================================================================
```

### The Engineering Decision:
* When given autonomous authority, the LLM suffered from **"Intervention Inflation"**—recommending high-friction notifications and support escalations on borderline cases where a standard delayed retry was economically optimal.
* **The Scientific Verdict**: In accordance with empirical rigor, **we removed the LLM from the autonomous financial execution path.**
* **Current Role of AI**: Contextual diagnosis only. The LLM serves strictly as an **Operator Decision Room Assistant** for human review on high-value transactions ($\ge ₹50,000$). The economic engine and deterministic SafetyKernel remain authoritative over action authorization.

---

## 5. Architecture: The Authoritative 8-Stage Pipeline

```text
                       INCOMING WEBHOOK EVENT
                                 │
                   ┌─────────────▼─────────────┐
                   │  Raw-Body HMAC-SHA256     │  (X-Razorpay-Signature)
                   │  Event-ID Deduplication   │  (x-razorpay-event-id)
                   └─────────────┬─────────────┘
                                 │
                   ┌─────────────▼─────────────┐
                   │   PaymentStateMachine     │  (Transactional State Lock)
                   └─────────────┬─────────────┘
                                 │
       ┌─────────────────────────┴─────────────────────────┐
       ▼                                                   ▼
┌──────────────┐                                    ┌──────────────┐
│ Deterministic│                                    │  Contextual  │
│  Fast-Path   │                                    │ LLM Diagnosis│
│   (85.7%)    │                                    │   (14.3%)    │
└──────┬───────┘                                    └──────┬───────┘
       └─────────────────────────┬─────────────────────────┘
                                 │
                   ┌─────────────▼─────────────┐
                   │   Economic Engine (IEV)   │
                   └─────────────┬─────────────┘
                                 │
                   ┌─────────────▼─────────────┐
                   │ 8-STAGE SAFETY KERNEL     │
                   │ • Stage 1: Schema Check   │
                   │ • Stage 2: Bounds Verify  │
                   │ • Stage 3: Merchant Limits│
                   │ • Stage 4: Retry Ceiling  │
                   │ • Stage 5: Push-Freshness │
                   │ • Stage 6: Atomic IdemLock│
                   │ • Stage 7: Kill Switch    │
                   │ • Stage 8: Auth Dispatch  │
                   └─────────────┬─────────────┘
                                 │
                   ┌─────────────▼─────────────┐
                   │  SHA-256 Audit Chain      │  (Tamper-Evident Ledger)
                   └───────────────────────────┘
```

---

## 6. Payment State Safety & Concurrency Races

PayRecover AI models and safely handles payment-state anomalies consistent with documented Razorpay webhook behavior:

1. **The Capture Race**: If a customer re-attempts payment via UPI while a scheduled retry is in queue, `payment.captured` arrives $\to$ pushes cancellation to `CANCELLED_STALE` $\to$ scheduled worker pull-check intercepts execution $\to$ **0 duplicate recovery executions in tested race scenarios**.
2. **Out-of-Order Webhooks**: If `payment.failed` arrives after `payment.captured` due to network reordering, the state machine recognizes `CAPTURED` as terminal and discards the event.
3. **Webhook Replay Attacks**: Identical `x-razorpay-event-id` deliveries are deduplicated in memory and ignored.
4. **Payment Downtime Sentinel**: Ingests `payment.downtime.started` webhooks and automatically applies an adaptive 1800s delay offset until `payment.downtime.resolved` restores normal policy.

---

## 7. Multi-World Generalization (Out-of-Distribution Proof)

To prove the economic policy was not over-indexed to a single simulator:

| World Variant | Environment Description | NIV Uplift vs Static Rules |
| :--- | :--- | :--- |
| **World V1** | Standard distribution | **+8.92%** |
| **World V2** | Weak technical retries, strong notification response | **+11.69%** |
| **World V3** | High natural recovery, high communication costs | **+10.57%** |

---

## 8. Operator Decision Room & Workstation

PayRecover AI includes a high-density, zero-dependency operator interface served directly by FastAPI at `http://localhost:8000/`:

1. **Overview Dashboard**: Live at-risk revenue, NIV gains, rail telemetry, and clickable claim verification drawers.
2. **Recovery Queue**: Real-time triage of incoming failed payments with instant IEV ranking.
3. **Payment Decision Room (Hero Screen)**: Candidate action comparison table, IEV breakdown, SafetyKernel pre-flight validation, and 1-click execution.
4. **Benchmark Proof Station**: Locked 10,000-case multi-seed leaderboard with Oracle theoretical upper bound.
5. **Failure Lab ("What Broke & How We Got Out")**: 1-Click interactive simulation of all 7 critical failure flows.
6. **Cryptographic Audit Ledger**: Real-time SHA-256 hash-chain viewer with 1-click cryptographic integrity verification.
7. **Safety Controls**: Merchant risk profile configuration (Conservative / Balanced / Aggressive) and Emergency Kill Switch.

---

## 9. Quickstart & Verification

### Prerequisites
* Python 3.11+
* Linux / macOS
* Zero external database setup needed: Runs on an embedded in-memory SQLite engine (`sqlite+aiosqlite:///:memory:`) by default for instant evaluation, with native PostgreSQL support via the `DATABASE_URL` environment variable.

### Installation & Test Execution

```bash
# 1. Clone Public Repository
git clone https://github.com/Nitin-mishra-dev/pay-recover-ai.git
cd pay-recover-ai

# 2. Setup Virtual Environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Run Complete Invariant Test Suite (45 Tests)
python3 -m pytest -v --tb=short

# 4. Reproduce Multi-Seed Holdout Benchmark (N=10,000)
python3 -m eval.run --split holdout --seeds 42,43,44,45,46 --n 10000

# 5. Launch Operator Decision Room Workstation
uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```
Open `http://localhost:8000` to access the interactive Decision Room and Failure Lab.

---

## 10. Repository Structure

```text
pay-recover-ai/
├── src/
│   ├── api/             # FastAPI routers (webhooks, cases, demo, benchmark, safety)
│   ├── core/            # State machine, 8-stage safety gate, economics, audit chain
│   ├── models/          # Canonical Pydantic schemas (events, actions, state)
│   ├── reasoner/        # Selective router, contextual LLM client, Pydantic contracts
│   ├── executor/        # Simulated bounded executor with 504 timeout containment
│   └── static/          # Operator Decision Room SPA (zero external build tools)
├── eval/
│   ├── baselines.py     # The 4 locked baselines + Oracle upper bound policy
│   ├── world.py         # Counterfactual simulation engine with V1/V2/V3 shifts
│   ├── dataset.py       # Deterministic partitioner (DEV 60%, TEST 20%, HOLDOUT 20%)
│   ├── metrics.py       # NIV, Gross Recovery, Regret, Policy Efficiency math
│   ├── run.py           # Multi-seed CLI benchmark runner
│   └── results/         # Verified JSON benchmark artifacts
├── tests/
│   ├── integration/     # Concurrency races, webhooks, executor, Decision Room APIs
│   └── unit/            # SafetyKernel, audit chain, state machine, AI reasoner
├── docs/                # Architecture specifications, claim ledger, metric hierarchy
└── pyproject.toml       # Project configuration
```

---

## 11. Limitations & Non-Goals

1. **Simulated Execution**: This repository is a competition-grade proof-of-concept with simulated Razorpay API responses. It does not initiate live financial debit on real bank accounts.
2. **Post-Failure Scope**: PayRecover is designed exclusively for the post-failure recovery window; it does not replace pre-transaction routing infrastructure.
3. **Audit Ledger Scope**: The internal SHA-256 cryptographic hash-chain provides tamper-evidence within the application process; production enterprise deployments should mirror hashes to an append-only external witness ledger.
