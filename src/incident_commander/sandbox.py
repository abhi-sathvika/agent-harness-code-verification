from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SandboxPlan:
    image: str
    network: str
    read_only_rootfs: bool
    drop_capabilities: tuple[str, ...]
    timeout_seconds: int
    command: tuple[str, ...]


@dataclass(frozen=True)
class SandboxResult:
    status: str
    summary: str
    plan: SandboxPlan

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["plan"]["drop_capabilities"] = list(self.plan.drop_capabilities)
        payload["plan"]["command"] = list(self.plan.command)
        return payload


def plan_remediation(action: str) -> SandboxPlan:
    """Build the sandbox envelope for approved remediation."""
    return SandboxPlan(
        image="incident-commander/remediation-runner:local",
        network="none",
        read_only_rootfs=True,
        drop_capabilities=("ALL",),
        timeout_seconds=30,
        command=("restore_checkout_pool", "--pool-size", "50"),
    )


def execute_remediation(action: str) -> SandboxResult:
    plan = plan_remediation(action)
    return SandboxResult(
        "SUCCEEDED",
        "Sandboxed remediation simulation restored checkout database pool size to 50.",
        plan,
    )
