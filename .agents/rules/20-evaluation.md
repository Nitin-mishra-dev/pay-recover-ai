# PAYRECOVER EVALUATION STANDARD

## Core requirement

All performance claims must come from reproducible experiments.

## Never do this

Do not make simulated outcomes depend directly on model predictions.

Bad:

model predicts 0.90
→ simulator uses 0.90 probability
→ model appears correct

This is circular.

## Correct architecture

Independent hidden environment
→ actual outcome

Model
→ predicted probability/value

Then compare prediction with outcome.

## Baselines

Always compare:

1. No Action
2. Blind Retry
3. Static Rules
4. PayRecover

## Primary business metrics

Prefer:
- incremental recovered revenue
- uplift vs baseline
- net incremental value
- intervention cost
- cost per recovered rupee

## Safety metrics

Measure:
- duplicate executions
- invalid executions
- stale-action executions
- retry-limit violations
- unauthorized actions
- failed-safe rate

## Reproducibility

Evaluation must support:

python -m eval.run --seed 42 --n 10000

The same seed must produce reproducible results.

## Reporting

Never invent metrics.

README metrics must match:
- evaluation output
- generated report
- submission numbers

## Limitations

Always disclose:
- synthetic data
- simulation assumptions
- absence of real merchant production data
- uncertainty in causal interpretation
