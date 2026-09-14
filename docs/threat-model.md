# Threat Model

## Security Assumption

Agents are treated as untrusted workloads. The harness should assume the model may misunderstand instructions, overreach, hallucinate, or be influenced by hostile data found in logs, Git diffs, tickets, or tool outputs.

## Assets

- Incident data.
- Investigation state.
- Evidence records.
- Tool credentials.
- Kubernetes access.
- Git repository access.
- Telemetry systems.
- Remediation capabilities.
- Evaluation ground truth.

## Trust Boundaries

```text
CLI/User
  -> Run Manager
  -> Agent Harness
  -> MCP Gateway
  -> External Operational Systems
```

Important boundary:

The agent reasons about what to do, but the harness authorizes and executes tool calls.

## Initial Threats

### Prompt Injection Through Operational Data

Logs, traces, Git commits, or incident descriptions may contain text instructing the model to ignore policy or falsify findings.

Initial defense:

- Treat tool outputs as untrusted evidence, not instructions.
- Keep system and harness rules outside tool output.
- Record evidence sources.

### Unauthorized Remediation

The agent may attempt to execute a risky action without approval.

Initial defense:

- No remediation execution in early milestones.
- Later remediation requires explicit human approval.
- Approval records should be persistent and auditable.

### Tool Overreach

The agent may query tools unrelated to the incident or with overly broad parameters.

Initial defense:

- Typed tool schemas.
- Time ranges and query scope.
- Later policy enforcement and budgets.

### Ground Truth Leakage

The evaluation answer key could leak into the agent context.

Initial defense:

- Store ground truth separately from agent-visible incident state.
- Evaluation code can read ground truth after the run, but the harness cannot.

### Evidence Fabrication

The model may claim evidence that was not observed.

Initial defense:

- Final reports must cite evidence IDs.
- Evaluation should detect unsupported root-cause claims.

## Later Security Work

- Agent identities.
- Tool permissions.
- Authenticated MCP calls.
- Policy enforcement.
- Sandbox isolation.
- Kubernetes RBAC.
- Secret management.
- Audit logs.

