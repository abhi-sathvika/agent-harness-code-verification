# Milestone 13: Evaluation Benchmark

The project now has a deterministic benchmark evaluator for `INC-001`. It scores the investigation artifact instead of just checking whether the final report sounds plausible.

Implemented command shape:

```bash
incident-commander evaluate benchmark checkout-latency --mode scripted
incident-commander evaluate benchmark checkout-latency --mode loop
incident-commander evaluate benchmark checkout-latency --mode graph
incident-commander evaluate benchmark checkout-latency --mode graph --include-kubernetes --json
```

The first benchmark checks:

- Final run status.
- Root-cause correctness.
- Required evidence IDs.
- Evidence correctness.
- Unsupported claim count.
- False hypothesis count.
- Tool-call count.

The important learning point is that evaluation should compare harness behavior, not just prompts. A report is only correct when it connects symptom, mechanism, and evidence: latency rose, database connections saturated, and the deployment diff changed the pool size.

This version is intentionally small and deterministic. A production version should add multiple incidents, hidden ground truth, trace-derived timing, retry counts, interruption recovery checks, cost/token accounting, and experiment comparison reports.

## Learning checkpoint

Run the benchmark across `scripted`, `loop`, and `graph` modes and explain:

1. Which evidence IDs are required for correctness.
2. Why naming checkout alone is not enough.
3. How Kubernetes evidence changes tool-call count but not the required root-cause evidence.
4. Which future metric would best expose unreliable retry or timeout behavior.
