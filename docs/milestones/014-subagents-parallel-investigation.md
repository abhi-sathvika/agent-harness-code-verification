# Milestone 14: Subagents and Parallel Investigation

The project now includes a deterministic parallel investigation mode. It fans out to specialist workers, gathers evidence through the same MCP gateway, and merges the results into one final investigation report.

Implemented command shape:

```bash
incident-commander investigate INC-001 --mode parallel
incident-commander evaluate benchmark checkout-latency --mode parallel
```

The first specialist workers are:

- `metrics-agent`: checks checkout latency, database connections, and database CPU.
- `change-agent`: checks the checkout deployment diff.
- `platform-agent`: checks simulated Kubernetes workload health.

The important learning point is that subagents are an orchestration pattern, not magic intelligence. The harness still owns tool boundaries, evidence IDs, hypothesis updates, final verification, and evaluation.

This version uses deterministic local workers. A production version should add branch budgets, cancellation propagation, independent traces, per-agent context windows, conflict resolution, and careful handling for tools with side effects.

## Learning checkpoint

Run the parallel mode and explain:

1. Which evidence each specialist collected.
2. How duplicate or conflicting evidence should be merged.
3. Why final root-cause verification should remain centralized.
4. What new failure modes appear when branches run concurrently.
