# Milestone 10: Docker Sandboxing

Approved remediation can now pass through a local sandbox boundary. The current implementation records a deterministic Docker-shaped sandbox plan instead of executing a real container, because the project does not yet have real infrastructure to mutate.

Implemented command shape:

```bash
incident-commander investigate INC-001 --mode graph --checkpoint-db runs.db --run-id run-001 --require-approval
incident-commander approvals approve approval-run-001 --checkpoint-db runs.db --execute-sandboxed
incident-commander runs state run-001 --checkpoint-db runs.db
```

The sandbox plan records:

- The remediation runner image.
- No network access.
- A read-only root filesystem.
- Dropped Linux capabilities.
- A timeout.
- The bounded command to execute.

This milestone keeps the agent away from arbitrary shell access. The agent proposes remediation, the operator approves it, and the harness maps that approval to a constrained execution envelope.

A production version should replace the simulated executor with real Docker invocation, image pinning, resource limits, mounted input/output directories, seccomp/AppArmor profiles, and immutable audit artifacts.

## Learning checkpoint

Approve with `--execute-sandboxed` and explain:

1. Which layer maps the approved action to a concrete command.
2. Why `network=none` and dropped capabilities matter.
3. Why the sandbox result is persisted with the run checkpoint.
4. Why sandboxing does not replace human approval.
