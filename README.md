# AI Incident Commander

AI Incident Commander is a CLI-first autonomous SRE investigation agent for learning and demonstrating modern agent harness engineering.

The target user experience is:

```bash
incident-commander investigate INC-001
```

Given an incident such as "Checkout API latency increased 4x after a deployment", the agent should investigate a simulated production environment, inspect telemetry, form hypotheses, gather evidence, identify the likely root cause, and optionally propose or execute remediation with human approval.

This is not a chatbot project. The primary learning goal is to understand how reliable long-running agent harnesses are engineered around probabilistic model calls.

## Product Boundaries

The project will have:

- A polished CLI as the primary interface.
- A stateful investigation harness using LangGraph.
- MCP servers for observability, Kubernetes, Git/repository history, and incident state.
- Persistent run state and checkpoints in PostgreSQL.
- Redis for queues, coordination, and cancellation signals.
- A simulated production environment on Kubernetes.
- Prometheus, Grafana, Loki, and OpenTelemetry for telemetry.
- LangSmith for traces, debugging, datasets, and evaluations.
- GitHub Actions for CI.

The project will not have:

- A frontend.
- A knowledge graph.
- A generic chatbot interface.
- Arbitrary direct tool access from the agent.
- Production remediation without human approval.

## Core Harness Loop

The agent harness owns the deterministic control flow:

```text
Incident
  -> Understand
  -> Hypothesize
  -> Investigate
  -> Observe
  -> Update State
  -> Evaluate Hypothesis
  -> Continue or Change Direction
  -> Verify
  -> Resolve
```

The agent must not claim a root cause without evidence. Root cause findings should cite the observations, metrics, logs, traces, deployment data, or repository changes that support them.

## Milestone Roadmap

1. Milestone 0: Architecture and design documents.
2. Milestone 1: CLI skeleton and deterministic incident simulator.
3. Milestone 2: Basic investigation loop without LangGraph.
4. Milestone 3: LangGraph stateful orchestration.
5. Milestone 4: Tool abstraction and MCP boundaries.
6. Milestone 5: Persistent state and checkpoints.
7. Milestone 6: Long-running execution lifecycle.
8. Milestone 7: Context management and compaction.
9. Milestone 8: Reliability controls: retries, timeouts, budgets, cancellation.
10. Milestone 9: Human approval and remediation workflow.
11. Milestone 10: Docker sandboxing.
12. Milestone 11: Kubernetes simulated production environment.
13. Milestone 12: Observability with OpenTelemetry, Prometheus, Loki, Grafana, and LangSmith.
14. Milestone 13: Evaluation benchmark and harness experiments.
15. Milestone 14: Subagents and parallel investigation.

Each milestone should produce a small working increment, tests, failure exercises, updated documentation, and a senior-engineer review.

## Learning Contract

Before implementation in each milestone, explain:

- The problem being solved.
- Why the problem exists in long-running agent systems.
- The architecture of the milestone.
- The distributed systems, security, and reliability concepts involved.
- The smallest useful implementation.
- How to test it and how to break it deliberately.

After implementation, explain:

- What changed.
- What is fragile.
- What would break at scale.
- What security risks remain.
- What the learner should now understand.
- What questions should be answered before moving on.

## Documentation

Start with these documents:

- [Architecture](docs/architecture.md)
- [System Design](docs/system-design.md)
- [Threat Model](docs/threat-model.md)
- [Failure Modes](docs/failure-modes.md)
- [Evaluation Plan](docs/evaluation.md)
- [ADR 0001: CLI-First Incident Commander](docs/decisions/0001-cli-first-incident-commander.md)

