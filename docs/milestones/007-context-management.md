# Milestone 7: Context Management

Graph checkpoints can now compact older event history into a deterministic context summary while keeping the evidence ledger and a bounded window of recent raw events.

Implemented command shape:

```bash
incident-commander investigate INC-001 --mode graph --checkpoint-db runs.db --run-id run-001 --pause-after-steps 2 --compact-after-events 3
incident-commander runs state run-001 --checkpoint-db runs.db
incident-commander runs resume run-001 --checkpoint-db runs.db
```

This is intentionally not LLM summarization yet. The first learning step is to separate durable facts from prompt context:

- Evidence remains structured and addressable.
- Hypotheses retain confidence and supporting or contradicting evidence IDs.
- Recent events remain verbatim.
- Older events become a summary that can be carried into resume.

Compaction is not an audit log replacement. A production version should persist the full event stream separately and compact only the model-facing context window.

## Learning checkpoint

Pause a run with `--compact-after-events 3`, inspect the checkpoint, and explain:

1. Which data remained structured after compaction?
2. Which data became summary text?
3. Why evidence IDs are safer to carry forward than prose-only summaries.
4. Why the model-facing context window and the audit log should be different storage concerns.
