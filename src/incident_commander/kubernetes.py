from __future__ import annotations

from dataclasses import dataclass

from incident_commander.domain import Evidence, Incident, ToolResult


@dataclass(frozen=True)
class Pod:
    name: str
    service: str
    ready: bool
    restarts: int
    image: str


@dataclass(frozen=True)
class Deployment:
    name: str
    namespace: str
    desired_replicas: int
    ready_replicas: int
    image: str
    revision: str


@dataclass(frozen=True)
class ClusterSnapshot:
    name: str
    namespace: str
    pods: tuple[Pod, ...]
    deployments: tuple[Deployment, ...]


CHECKOUT_CLUSTER = ClusterSnapshot(
    name="simulated-prod",
    namespace="checkout-prod",
    pods=(
        Pod("checkout-api-7c9b6c5d7d-k2m4p", "checkout", True, 0, "checkout:2026.09.14-17"),
        Pod("checkout-api-7c9b6c5d7d-r8x1q", "checkout", True, 0, "checkout:2026.09.14-17"),
        Pod("payments-api-58d9f6f4f9-q1p7z", "payments", True, 0, "payments:2026.09.12-03"),
        Pod("inventory-api-6bcb8f6c8c-h5n2v", "inventory", True, 0, "inventory:2026.09.10-11"),
    ),
    deployments=(
        Deployment("checkout-api", "checkout-prod", 2, 2, "checkout:2026.09.14-17", "2026.09.14-17"),
        Deployment("payments-api", "checkout-prod", 1, 1, "payments:2026.09.12-03", "2026.09.12-03"),
        Deployment("inventory-api", "checkout-prod", 1, 1, "inventory:2026.09.10-11", "2026.09.10-11"),
    ),
)


def get_cluster(incident: Incident) -> ClusterSnapshot | None:
    if incident.scenario_id != "checkout-db-pool-regression":
        return None
    return CHECKOUT_CLUSTER


def inspect_checkout_workload(incident: Incident) -> ToolResult:
    cluster = get_cluster(incident)
    if cluster is None:
        return ToolResult("inspect_checkout_workload", error=f"unsupported scenario: {incident.scenario_id}")
    deployment = next(item for item in cluster.deployments if item.name == "checkout-api")
    checkout_pods = tuple(item for item in cluster.pods if item.service == "checkout")
    restarts = sum(item.restarts for item in checkout_pods)
    if deployment.ready_replicas == deployment.desired_replicas and restarts == 0:
        summary = (
            "Kubernetes checkout deployment has 2/2 ready replicas on revision 2026.09.14-17 "
            "with zero pod restarts, weakening pod crash or rollout failure as the primary cause."
        )
    else:
        summary = "Kubernetes checkout workload is unhealthy and needs investigation before remediation."
    return ToolResult(
        "inspect_checkout_workload",
        evidence=Evidence(
            "E-005",
            "kubernetes.deployment.checkout",
            summary,
            supports=("H-001",),
            contradicts=("H-003",),
        ),
    )
