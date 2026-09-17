# Milestone 8: Reliability Controls

Graph investigations now support a deterministic tool-call budget. The harness stops before the next tool call when the budget is exhausted, records `BUDGET_EXCEEDED`, and persists the bounded state to the checkpoint database.

Implemented command shape:

```bash
incident-commander investigate INC-001 --mode graph --checkpoint-db runs.db --run-id run-001 --max-tool-calls 2
incident-commander runs state run-001 --checkpoint-db runs.db
```

The budget belongs in the harness, not in the model prompt. A model may choose actions, but the harness owns whether an action is allowed to execute. This keeps cost, time, and blast radius bounded even when reasoning loops are imperfect.

This milestone implements only one reliability control. Future controls should add:

- Per-tool timeouts.
- Retry policies by error type.
- Idempotency keys for side-effecting tools.
- Cancellation checks between nodes.
- Separate token, wall-clock, and remediation budgets.

## Learning checkpoint

Run with `--max-tool-calls 2` and explain:

1. Why the third tool call never executes.
2. Why `BUDGET_EXCEEDED` is a terminal run status rather than a tool error.
3. Which checkpoint fields let an operator see what happened before the stop.
4. Why retry and timeout policies need tool-specific metadata before real MCP tools are introduced.
