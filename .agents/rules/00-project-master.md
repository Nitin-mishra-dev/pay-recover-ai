# PAYRECOVER AI — MASTER ENGINEERING CONSTITUTION

## Mission

Build PayRecover AI as a production-grade, state-safe, economically optimized revenue-recovery decision engine.

The objective is not maximum feature count.

The objective is maximum product defensibility from:
- measurable business impact & Net Incremental Value (NIV)
- technical depth and robust state management
- safe, deterministic agentic behavior
- reproducible, un-leaked evaluation
- payment-state correctness under asynchronous concurrency
- clear, transparent decision explainability
- disciplined engineering judgment

## Operating Doctrine

Every major change must satisfy:

1. Correctness
2. Safety
3. Testability
4. Observability
5. Measurability
6. Reproducibility
7. Explainability

If a feature does not materially improve one of these, challenge whether it should exist.

## Source of Truth

Before making architectural decisions:
- inspect the repository
- inspect docs/
- inspect existing code
- inspect tests
- inspect current decisions

Do not invent existing behavior.
Do not overwrite working functionality unnecessarily.

## AI Boundary

The LLM may:
- analyze ambiguity
- synthesize context
- classify difficult cases
- produce structured recommendations adhering to schemas
- explain decisions

The LLM may NOT:
- bypass policy
- modify safety limits
- execute financial actions directly
- disable fraud protection
- disable idempotency
- disable merchant controls
- override payment state

Deterministic code is authoritative for execution.

## Financial Safety

Never execute an action unless:
- payment state is valid
- action is authorized
- policy permits it
- safety checks pass
- idempotency is satisfied
- action is not stale
- automation is enabled

## State Correctness

Treat external payment events as asynchronous and potentially duplicated.

Never assume event ordering.

Payment state must be authoritative.

A stale scheduled action must be cancelled or rejected when a newer payment state makes it invalid.

## Definition of Ready (DoR)

Before any feature implementation may begin:
1. Problem and objective are explicitly defined.
2. Acceptance criteria are documented.
3. Financial and operational risks are identified.
4. State transitions and race conditions are mapped.
5. Canonical action contract adheres to `docs/product-specs/recovery-actions.md`.
6. Independent evaluation methodology is specified.
7. Rollback, failure, and fail-closed behaviors are known.
8. Verification test plan is approved.

## Definition of Done (DoD)

A feature is complete only when:
- implementation exists and adheres to approved plan
- unit and integration tests exist
- all tests pass with command evidence
- failure and edge-case behavior is tested
- documentation matches implementation
- demo behavior is reproducible
- metrics are verified against evaluation artifacts and claim ledger

## Evidence-First Development

Never claim:
- a test passed without running it
- a benchmark succeeded without running it
- a metric exists without generating it
- a feature is production-safe without defining its limits
- an external fact is verified without a source

When reporting completion, provide:
- what changed
- files changed
- tests executed
- commands executed
- observed results
- remaining risks

## Scope Control

Reject feature creep.

Do NOT add unless explicitly approved:
- voice agents
- WhatsApp integration
- unnecessary RAG
- multi-agent complexity
- unnecessary vector databases
- live-money execution
- unnecessary cloud infrastructure
- Kubernetes
- premature optimization

## Escalation Behavior

If requirements are ambiguous:
1. inspect existing sources/docs
2. make the smallest defensible assumption
3. document the assumption
4. continue only if the assumption is low risk

For high-risk ambiguity, stop and ask the user.
