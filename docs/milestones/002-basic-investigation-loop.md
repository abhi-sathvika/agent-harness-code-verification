# Milestone 2: Basic Investigation Loop

The scripted milestone proved the output shape, but every decision was pre-written. This milestone makes the harness explicit: it observes the incident, selects a tool, records evidence, updates hypothesis state, and terminates only after verification.

The tools are deliberately in-process. They have the same typed boundary we will later expose through MCP, so we can study control flow before adding protocol, networking, or model variability.

## Learning checkpoint

You should be able to trace one iteration as:

`hypothesis -> tool selection -> tool result -> evidence ledger -> confidence update`.

Ask yourself: what state would be lost if the process crashed after the tool returned but before the evidence event was recorded? That gap motivates checkpoints in Milestone 5.
