# ADR 0001: CLI-First AI Incident Commander

## Status

Accepted

## Problem

The project needs a focused product surface for learning long-running agent harness engineering. A web frontend would add unrelated product and UI complexity. A generic chatbot interface would hide the operational structure that this project is meant to teach.

## Options Considered

### CLI-first

Use a polished command-line interface for creating incidents, starting investigations, watching progress, inspecting state, approving remediation, replaying runs, and launching evaluations.

Benefits:

- Keeps attention on harness behavior.
- Works naturally with SRE workflows.
- Easy to test in CI.
- Makes structured events and state transitions visible.

Costs:

- Less visually rich than a dashboard.
- Requires careful CLI design to remain discoverable.

### Web frontend

Build a browser UI for incidents and investigations.

Benefits:

- Easier to visualize timelines and traces.
- More demo-friendly for some audiences.

Costs:

- Adds frontend complexity outside the core learning objective.
- Risks spending time on UI instead of harness engineering.

### Chat interface

Expose the system primarily as a conversational assistant.

Benefits:

- Familiar agent interaction model.
- Fast to prototype.

Costs:

- Makes the system look like a chatbot.
- Obscures run lifecycle, state, evidence, budgets, and tool boundaries.

## Decision

AI Incident Commander will be CLI-first.

FastAPI may be introduced later only where it helps the runtime or control plane, such as exposing run status, worker coordination, or service-to-service APIs.

## Consequences

- Milestone 1 starts with CLI and deterministic incident simulation.
- All investigation progress should be represented as structured events that the CLI can stream and tests can assert.
- The system should remain usable without a frontend.
- Documentation and demos should emphasize harness state, evidence, and recovery rather than chat transcripts.

