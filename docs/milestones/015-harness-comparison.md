# Milestone 15: Harness Comparison

The evaluator can now compare multiple harness designs in one benchmark run. This turns the evaluation layer into an experiment report instead of a single-mode score.

Implemented command shape:

```bash
incident-commander evaluate compare checkout-latency
incident-commander evaluate compare checkout-latency --json
```

The comparison currently runs:

- `scripted`
- `loop`
- `graph`
- `graph+kubernetes`
- `parallel`

Each row reports pass/fail, evidence correctness, tool calls, and false hypothesis count. The point is not to crown the most complex harness. The point is to make tradeoffs visible: additional context and parallelism may improve coverage, but they also increase tool calls and coordination surface.

## Learning checkpoint

Run the comparison and explain:

1. Which modes collect the minimum required evidence.
2. Which modes spend extra tool calls.
3. Why `graph+kubernetes` and `parallel` can pass even though Kubernetes evidence is not required.
4. Which metric would matter most if this benchmark became expensive or flaky.
