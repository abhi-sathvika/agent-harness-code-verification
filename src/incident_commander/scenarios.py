from __future__ import annotations

from incident_commander.domain import Incident, Severity


INCIDENTS: dict[str, Incident] = {
    "INC-001": Incident(
        incident_id="INC-001",
        title="Checkout API latency increased 4x after deployment",
        service="checkout",
        severity=Severity.SEV2,
        symptoms=(
            "checkout p95 latency increased from 250ms to 1000ms",
            "regression began shortly after deployment 2026.09.14-17",
            "error rate is mostly unchanged",
        ),
        started_at="2026-09-14T12:03:00-07:00",
        scenario_id="checkout-db-pool-regression",
    )
}


def list_incidents() -> tuple[Incident, ...]:
    return tuple(INCIDENTS.values())


def get_incident(incident_id: str) -> Incident | None:
    return INCIDENTS.get(incident_id.upper())
