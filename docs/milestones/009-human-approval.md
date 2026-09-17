# Milestone 9: Human Approval

Graph investigations can now stop after verification and wait for explicit human approval before remediation is recorded. The harness persists an approval ID, the proposed action, and the `WAITING_FOR_APPROVAL` run status.

Implemented command shape:

```bash
incident-commander investigate INC-001 --mode graph --checkpoint-db runs.db --run-id run-001 --require-approval
incident-commander runs state run-001 --checkpoint-db runs.db
incident-commander approvals approve approval-run-001 --checkpoint-db runs.db
```

The important learning point is that diagnosis and remediation are different authority levels. The agent may propose a remediation after evidence-backed verification, but the harness owns whether execution can proceed. This keeps operational authority outside model reasoning.

This version records approved remediation as a durable event. It does not yet execute a real external action. A production version should add authorization policy, approver identity, expiration, approval denial, and idempotent remediation execution.

## Learning checkpoint

Run with `--require-approval` and explain:

1. Which evidence supports the proposed remediation.
2. Why the run status becomes `WAITING_FOR_APPROVAL` instead of `COMPLETED`.
3. Which checkpoint fields let an operator approve the right action.
4. Why approving remediation should be a separate command from investigation.
