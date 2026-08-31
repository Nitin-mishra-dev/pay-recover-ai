# PayRecover AI — Multi-Agent Subagent Protocol & Evaluator Isolation

To prevent confirmation bias, hallucinated progress, and merge conflicts, PayRecover AI enforces a strict multi-agent separation of concerns.

---

## Agent Topology

```
                  ┌──────────────────────────────┐
                  │    Primary Builder Agent     │
                  │   (Implementation Lead)      │
                  └──────────────┬───────────────┘
                                 │
                   Dispatches Scoped Artifacts
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌──────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│ Independent      │   │ Adversarial       │   │ Benchmark         │
│ Test Engineer    │   │ Red-Team Agent    │   │ Auditor Agent     │
│ (tests/suite)    │   │ (attacks/fuzzing) │   │ (eval/metrics)    │
└──────────────────┘   └───────────────────┘   └───────────────────┘
```

---

## Operating Protocols

### 1. The Primary Builder
* Responsible for writing clean, tested application code according to approved implementation plans.
* Operates in the main workspace directory.
* Does NOT declare a feature "complete" without submitting it to independent verification.

### 2. Independent Evaluator Isolation (No Context Contamination)
* When evaluating benchmark claims, testing race conditions, or reviewing diffs, subagents are invoked with **isolated prompts and clean context**.
* The evaluator does **not** inherit the builder's self-assurances.
* The evaluator executes the test or benchmark script directly in the terminal, reads the raw stdout/JSON output, and independently computes metrics.

### 3. Concurrency Locking Invariant
* **No two agents may edit the same source file concurrently.**
* Parallel subagents may only run independent tasks (e.g. Agent A runs pytest on state machine while Agent B audits dataset generation logic).
