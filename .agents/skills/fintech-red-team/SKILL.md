---
name: fintech-red-team
description: Adversarially tests PayRecover AI for payment-state races, duplicate execution, stale decisions, unsafe automation, malformed AI output, and failure containment.
---

# Fintech Red Team

Assume the system will fail.

Attack:

- duplicate webhook
- out-of-order webhook
- payment captured after failure
- stale retry
- concurrent execution
- malformed LLM JSON
- LLM timeout
- LLM unavailable
- policy conflict
- fraud state
- dispute state
- retry ceiling
- kill switch
- scheduler restart
- gateway timeout
- partial execution

For every attack:

ATTACK
EXPECTED
ACTUAL
INVARIANT
FAILURE
FIX
TEST

No hand-waving.

Every critical vulnerability should become an automated regression test.
