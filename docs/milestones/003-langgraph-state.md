# Milestone 3: LangGraph State

LangGraph now represents the investigation as a state machine. The state is still ordinary, inspectable Python data: incident, hypotheses, evidence, plan cursor, events, and status.

LangGraph contributes graph execution and explicit transitions. It does not decide whether evidence is trustworthy, choose safe permissions, persist checkpoints, or make the model reliable. Those remain harness responsibilities.

## Learning checkpoint

Trace the `investigate -> investigate` self-loop and explain why a graph is a better representation than one large function when runs can pause, retry, or resume at a node boundary.
