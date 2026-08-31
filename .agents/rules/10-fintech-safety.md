# PAYRECOVER FINTECH SAFETY RULE

Apply this rule to all payment/recovery code.

## Trust boundary

Untrusted:
- webhook payloads
- LLM output
- customer-controlled text
- external API responses
- browser input
- synthetic scenario input

Trusted only after validation:
- payment state
- policy decision
- authorized action
- persisted idempotency record

## Never trust LLM output

LLM output must be:
1. parsed
2. schema validated
3. normalized
4. policy checked
5. safety checked

Malformed output must fail closed.

## State invariants

Never execute a recovery action when:
- payment is captured
- payment is already recovered
- action has already executed
- retry ceiling reached
- cooldown not satisfied
- automation disabled
- fraud hold active
- dispute hold active
- customer-contact restriction violated
- decision is stale
- required data is missing

## Idempotency

Every executable recovery action must have a stable action identity.

Duplicate delivery must never create duplicate execution.

## Race conditions

A payment state update always wins over a stale recovery decision.

Example:

payment.failed
→ retry scheduled
→ payment.captured
→ retry cancelled/rejected

## Kill switch

Global automation pause must be checked immediately before execution.

## Failure mode

When uncertainty increases:
- do less
- pause
- escalate
- record the reason

Never "try anyway."

## Audit

Record:
- event
- decision
- model version
- policy version
- action
- authorization
- execution result
- timestamps
- failure reason
