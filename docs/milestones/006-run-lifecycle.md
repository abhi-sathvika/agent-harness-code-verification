# Milestone 6: Run Lifecycle

Graph investigations now have a small operator-visible lifecycle. A run can be given a stable ID, paused at a durable node boundary, inspected from the checkpoint database, and resumed from the saved state.

Implemented commands:

```bash
incident-commander investigate INC-001 --mode graph --checkpoint-db runs.db --run-id run-001 --pause-after-steps 2
incident-commander runs list --checkpoint-db runs.db
incident-commander runs state run-001 --checkpoint-db runs.db
incident-commander runs resume run-001 --checkpoint-db runs.db
```

The important boundary is that resume reconstructs runtime-only dependencies, such as the MCP gateway, instead of trying to serialize them. Durable state records what happened and what should happen next; runtime wiring is recreated and validated when execution restarts.

## Learning checkpoint

Trace a paused run and explain:

1. Which fields are durable investigation state?
2. Which fields are runtime resources that must be rebuilt?
3. Why resuming at a graph node boundary is safer than resuming in the middle of a tool call.
4. What would need to change before external tools with side effects could be retried safely?
