# Architecture

## Problem

AI Incident Commander investigates production incidents by coordinating model reasoning with deterministic harness behavior. The system must manage state, tools, evidence, budgets, retries, checkpoints, cancellation, and recovery around the model.

The interesting engineering problem is not "call an LLM". It is building a harness that can keep a long-running investigation coherent, auditable, interruptible, recoverable, and evidence-based.

## Target Architecture

```text
User
  |
  v
CLI: incident-commander
  |
  v
Run Manager
  |
  v
LangGraph Investigation Harness
  |
  +--> State Store: PostgreSQL
  +--> Coordination: Redis
  +--> Trace Sink: LangSmith / OpenTelemetry
  |
  v
MCP Gateway
  |
  +--> Observability MCP Server
  |     +--> Prometheus
  |     +--> Loki
  |     +--> Traces
  |
  +--> Kubernetes MCP Server
  |     +--> Pods
  |     +--> Deployments
  |     +--> Events
  |
  +--> Git MCP Server
  |     +--> Commit History
  |     +--> Deployment History
  |     +--> Diffs
  |
  +--> Incident State MCP Server
        +--> Incidents
        +--> Hypotheses
        +--> Evidence
        +--> Ground Truth for Evaluation
```

## Major Components

### CLI

The CLI is the main product surface. It starts investigations, streams progress, shows hypotheses and evidence, pauses or resumes runs, handles approvals, replays runs, and launches evaluations.

Example commands:

```bash
incident-commander incidents list
incident-commander incidents create --scenario checkout-latency
incident-commander investigate INC-001
incident-commander runs watch RUN-001
incident-commander runs state RUN-001
incident-commander hypotheses list RUN-001
incident-commander evidence list RUN-001
incident-commander approve APPROVAL-001
incident-commander evaluate benchmark checkout-latency
```

### Run Manager

The run manager owns run IDs, lifecycle transitions, cancellation, resume behavior, and high-level run metadata.

The initial lifecycle is:

```text
CREATED
  -> RUNNING
  -> WAITING_FOR_APPROVAL
  -> COMPLETED
  -> FAILED
  -> CANCELLED
```

Later milestones will add `QUEUED`, `PAUSED`, `RECOVERING`, and `BUDGET_EXCEEDED`.

### LangGraph Investigation Harness

LangGraph will eventually represent the investigation as explicit stateful nodes:

```text
understand_incident
  -> generate_hypotheses
  -> choose_next_action
  -> call_tool
  -> record_observation
  -> update_hypotheses
  -> should_continue
  -> verify_root_cause
  -> propose_resolution
```

The graph should not hide important state. The project should define its own investigation state, hypothesis state, evidence records, and termination conditions.

### MCP Gateway

MCP is the architectural boundary between agent reasoning and operational tools.

The agent should not directly query Prometheus, Kubernetes, Git, or the incident database. It should request tool calls through MCP servers with typed schemas, timeouts, authorization checks, structured results, and error handling.

### Simulated Production Environment

The simulated environment eventually runs on Kubernetes and includes:

- API gateway
- Checkout
- Payments
- Inventory
- Database
- Cache
- Queue and worker

Incident injectors will create realistic failures with hidden ground truth so the harness can be evaluated.

## Data Flow

```text
1. User starts investigation from CLI.
2. Run Manager creates a run ID and initial incident state.
3. Harness loads incident context and checkpoint state.
4. Harness asks the model to reason about the next step.
5. Harness validates and routes selected tool calls through MCP.
6. MCP server executes a bounded operational query.
7. Harness records observations as structured evidence.
8. Harness updates hypotheses and confidence.
9. Harness decides whether to continue, verify, pause, ask for approval, or resolve.
10. CLI streams progress from run events.
11. Evaluation compares final findings to hidden ground truth.
```

## What We Intentionally Do Not Build First

- Real Kubernetes.
- Real Prometheus, Loki, or Grafana.
- Real remediation execution.
- Subagents.
- Complex auth.
- Production-grade scheduling.
- A web UI.

The first implementation should simulate enough of the world to make the harness behavior understandable and testable.

