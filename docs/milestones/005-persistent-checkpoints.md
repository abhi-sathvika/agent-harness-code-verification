# Milestone 5: Persistent Checkpoints

The CLI can now persist investigation snapshots with `--checkpoint-db`. The graph writes a snapshot after each node boundary. The store uses SQLite for a zero-infrastructure learning environment, but exposes a small interface that can be replaced by PostgreSQL without changing the harness model.

The serialized snapshot excludes the live MCP gateway because connections and handlers are runtime resources, not durable state. A future resume operation must reconstruct those dependencies and validate the checkpoint before continuing.

## Learning checkpoint

Identify the remaining consistency gap: a crash during a tool call can still leave an external side effect uncertain. The next version should define whether each tool is safe to retry or needs an idempotency key, then add resume from the last durable node.
