# System Design

## Functional Requirements

The system should eventually support:

- Create and list incidents.
- Start, pause, resume, cancel, watch, and replay investigations.
- Stream structured investigation progress.
- Track run IDs, incident state, hypotheses, evidence, tool calls, and final reports.
- Route all operational tool calls through MCP.
- Query simulated metrics, logs, traces, Kubernetes status, deployment history, and Git diffs.
- Persist checkpoints and recover interrupted runs.
- Enforce retries, timeouts, budgets, and termination conditions.
- Require human approval for remediation.
- Evaluate investigations against hidden ground truth.
- Compare harness configurations.

## Non-Functional Requirements

The system should be:

- Understandable: important state is explicit and inspectable.
- Recoverable: interrupted runs can resume from checkpoints.
- Observable: key decisions, tool calls, failures, and evidence are traceable.
- Secure by design: tool access is mediated and remediation requires approval.
- Testable: incidents have hidden ground truth and reproducible scenarios.
- Incremental: each milestone should work without needing the whole final platform.

## Initial Domain Model

### Incident

Represents the operational problem to investigate.

Fields:

- `incident_id`
- `title`
- `service`
- `severity`
- `started_at`
- `symptoms`
- `scenario_id`
- `ground_truth` for evaluation-only use

### Investigation Run

Represents one attempt to investigate an incident.

Fields:

- `run_id`
- `incident_id`
- `status`
- `started_at`
- `finished_at`
- `harness_config`
- `budget`
- `current_step`
- `final_report`

### Hypothesis

Represents a candidate explanation.

Fields:

- `hypothesis_id`
- `run_id`
- `statement`
- `confidence`
- `status`
- `supporting_evidence_ids`
- `contradicting_evidence_ids`

### Evidence

Represents an observation used to support or weaken a hypothesis.

Fields:

- `evidence_id`
- `run_id`
- `source`
- `summary`
- `raw_ref`
- `supports`
- `timestamp`

### Tool Call

Represents a bounded external action.

Fields:

- `tool_call_id`
- `run_id`
- `tool_name`
- `input`
- `status`
- `started_at`
- `finished_at`
- `error`
- `result_ref`

## First Scenario

The first deterministic incident should be simple:

```text
INC-001: Checkout API latency increased 4x after deployment.
```

Hidden ground truth:

```text
The checkout service deployment changed the database connection pool size from 50 to 5, causing connection saturation and request queueing.
```

Initial available observations:

- Checkout p95 latency increased after deployment.
- Error rate is mostly flat.
- Database CPU is normal.
- Database active connections are near pool limit.
- Recent Git diff contains a connection pool configuration change.

The correct final report must connect the symptom to the deployment and cite evidence from metrics and Git history.

## Milestone 1 Shape

Milestone 1 should create a local CLI and deterministic simulator with no model call yet.

Target commands:

```bash
incident-commander incidents list
incident-commander incidents show INC-001
incident-commander investigate INC-001 --mode scripted
```

The scripted mode should produce structured progress so the user can first learn what good harness artifacts look like before model uncertainty enters the system.

