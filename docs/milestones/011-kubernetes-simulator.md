# Milestone 11: Kubernetes Simulated Production

The project now includes a deterministic Kubernetes-shaped production simulator. The graph can optionally inspect the simulated checkout workload through the MCP gateway before deciding that pod crashes or rollout health are not the primary cause.

Implemented command shape:

```bash
incident-commander investigate INC-001 --mode graph --include-kubernetes
```

The simulated cluster currently contains:

- A `checkout-prod` namespace.
- A `checkout-api` deployment at revision `2026.09.14-17`.
- Two ready checkout pods with zero restarts.
- Neighboring payments and inventory workloads.

The important boundary is that the graph does not access Kubernetes directly. It requests `kubernetes.inspect_checkout_workload` through the MCP gateway, receives structured evidence, and updates the Kubernetes-health hypothesis from that evidence.

This is not a real Kubernetes integration yet. A production version should add kubeconfig handling, namespace scoping, RBAC, timeouts, event queries, rollout history, pod logs, and safeguards against mutation.

## Learning checkpoint

Run with `--include-kubernetes` and explain:

1. What Kubernetes evidence was collected.
2. Which hypothesis it weakens.
3. Why healthy pods do not disprove the database-pool root cause.
4. Why Kubernetes access should remain behind the MCP gateway.
