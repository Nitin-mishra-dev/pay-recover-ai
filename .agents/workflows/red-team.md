# Red Team Workflow

Assume the system is unsafe until proven otherwise.

Attack the current implementation.

At minimum test:

1. duplicate webhook
2. out-of-order webhook
3. payment captured before recovery
4. stale action
5. duplicate execution
6. malformed LLM response
7. LLM timeout
8. LLM unavailable
9. max retry
10. kill switch
11. fraud stop
12. dispute stop
13. concurrent execution
14. stale decision
15. invalid merchant policy

For each:

Attack
Expected
Actual
Evidence
Severity
Fix

Every CRITICAL/HIGH finding blocks release.
