# Implement Feature Workflow

Read the approved plan first.

Implement only approved scope.

Rules:

- small diffs
- no unrelated refactors
- tests with implementation
- preserve existing contracts
- update docs where necessary

After implementation:

1. inspect git diff
2. run targeted tests
3. run lint/type checks
4. run affected integration tests
5. inspect failures
6. fix only relevant issues
7. rerun verification

Report:

CHANGED
TESTED
RESULT
RISKS
