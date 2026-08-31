# Verification Workflow

The goal is to prove the implementation works.

Do not say "looks good."

Run:

1. repository status
2. targeted tests
3. full test suite
4. type checking
5. linting
6. build
7. API smoke tests
8. relevant integration tests
9. relevant benchmark
10. inspect logs/errors
11. inspect git diff

For every claim provide command + result.

Classify:

PASS
FAIL
BLOCKED

A PASS without command evidence is invalid.

If something fails:
- diagnose
- fix
- rerun
- report final result

Do not hide failures.
