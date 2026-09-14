# Failure Modes

## Failure-First Design Questions

For every distributed or long-running component, ask:

- What can fail?
- What state survives?
- What state is lost?
- Can the operation be retried?
- Is retry safe?
- How do we detect the failure?
- How does the user inspect what happened?

## Initial Failure Modes

### Tool Timeout

Example:

`query_metrics` does not return before its deadline.

Expected behavior:

- Record a failed tool call.
- Preserve the attempted input.
- Retry only if the policy allows it.
- Let the harness choose a fallback query or alternative evidence source.

### Bad Tool Result

Example:

Metrics return an empty series because the time window is wrong.

Expected behavior:

- Treat empty results as an observation, not necessarily a failure.
- Record the query parameters.
- Allow the agent to adjust the time range.

### Interrupted Investigation

Example:

The process crashes after two hypotheses and three evidence records.

Expected behavior:

- Completed checkpoints survive.
- The resumed run reloads current hypotheses and evidence.
- The harness does not duplicate already-recorded evidence.

### Runaway Investigation

Example:

The agent keeps querying the same metric without making progress.

Expected behavior:

- Detect repeated tool patterns.
- Enforce tool-call and time budgets.
- Terminate or ask for human guidance when progress stalls.

### Unsupported Root Cause

Example:

The final report says "database CPU saturation" even though no evidence supports it.

Expected behavior:

- Verification step rejects the final answer.
- Evaluation marks the run as unsupported or incorrect.

## Early Test Strategy

Milestone 1 should include deterministic tests for:

- Listing incidents.
- Showing `INC-001`.
- Running a scripted investigation.
- Emitting structured progress events.
- Producing a final report with evidence IDs.

Later milestones should add failure injection for timeouts, invalid tool results, interrupted runs, and cancelled runs.

