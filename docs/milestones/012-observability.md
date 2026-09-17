# Milestone 12: Observability

Graph investigations and approval completion can now emit local JSONL trace records. This gives the project an observability boundary before introducing OpenTelemetry, Prometheus, Grafana, Loki, or LangSmith.

Implemented command shape:

```bash
incident-commander investigate INC-001 --mode graph --include-kubernetes --trace-file traces.jsonl
incident-commander approvals approve approval-run-001 --checkpoint-db runs.db --execute-sandboxed --trace-file traces.jsonl
```

The trace sink records:

- Final run status.
- Evidence count.
- Tool-call count.
- Structured investigation events.
- Tool and evidence references.
- Approval completion.
- Sandbox status and network policy.

Checkpoints and traces are intentionally separate. Checkpoints are recovery state used to resume execution. Traces are operational telemetry used to understand what happened across runs.

This version writes local JSONL. A production version should add OpenTelemetry spans, metric counters, trace IDs, LangSmith run links, log correlation IDs, and dashboards for reliability metrics.

## Learning checkpoint

Run with `--trace-file` and explain:

1. Which records describe control flow.
2. Which records describe tool usage.
3. Why traces should not be the only durable run state.
4. Which fields would become metric labels or span attributes in OpenTelemetry.
