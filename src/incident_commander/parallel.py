from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from incident_commander.domain import (
    Evidence,
    FinalReport,
    Hypothesis,
    HypothesisStatus,
    Incident,
    InvestigationEvent,
    ScriptedInvestigation,
)
from incident_commander.mcp_gateway import build_local_gateway


AGENT_PLANS = {
    "metrics-agent": (
        ("H-001", "observability.query_checkout_latency"),
        ("H-001", "observability.query_database_connections"),
        ("H-002", "observability.query_database_cpu"),
    ),
    "change-agent": (("H-001", "git.inspect_checkout_diff"),),
    "platform-agent": (("H-003", "kubernetes.inspect_checkout_workload"),),
}


def investigate_parallel(incident: Incident) -> ScriptedInvestigation:
    """Deterministic fan-out/fan-in investigation across specialist workers."""
    hypotheses = [
        Hypothesis("H-001", "Checkout deployment reduced the database connection pool and caused request queueing.", 0.20),
        Hypothesis("H-002", "Database CPU saturation caused checkout latency.", 0.20),
        Hypothesis("H-003", "Kubernetes pod crashes or an unhealthy rollout caused checkout latency.", 0.15),
    ]
    events = [
        InvestigationEvent("12:03:11", "Run", f"Started parallel investigation for {incident.incident_id}"),
        InvestigationEvent("12:03:12", "Observe", incident.symptoms[0]),
    ]
    with ThreadPoolExecutor(max_workers=len(AGENT_PLANS)) as executor:
        futures = [
            executor.submit(_run_agent, agent_name, plan, incident)
            for agent_name, plan in AGENT_PLANS.items()
        ]
        branch_results = [future.result() for future in futures]

    evidence_by_id: dict[str, Evidence] = {}
    second = 13
    for agent_name, branch_events, branch_evidence in branch_results:
        events.append(InvestigationEvent(f"12:03:{second:02d}", "Subagent", f"Merged findings from {agent_name}", agent_name))
        second += 1
        for event in branch_events:
            events.append(InvestigationEvent(f"12:03:{second:02d}", event.kind, event.message, event.ref_id))
            second += 1
        for item in branch_evidence:
            evidence_by_id[item.evidence_id] = item

    evidence = tuple(evidence_by_id.values())
    _update_hypotheses(hypotheses, evidence)
    events.append(InvestigationEvent(f"12:03:{second:02d}", "Verify", "Parallel branches agree on the deployment and database-pool mechanism", "H-001"))
    report = FinalReport(
        "Checkout deployment reduced the database connection pool from 50 to 5, causing connection saturation and request queueing.",
        0.93,
        ("E-001", "E-002", "E-004"),
        "Require human approval, then restore checkout database pool size to 50 and monitor p95 latency plus connection usage.",
    )
    return ScriptedInvestigation(incident, tuple(events), tuple(hypotheses), evidence, report)


def _run_agent(agent_name: str, plan: tuple[tuple[str, str], ...], incident: Incident) -> tuple[str, list[InvestigationEvent], list[Evidence]]:
    gateway = build_local_gateway()
    events: list[InvestigationEvent] = []
    evidence: list[Evidence] = []
    for hypothesis_id, tool_name in plan:
        display_tool = tool_name.rsplit(".", 1)[-1]
        events.append(InvestigationEvent("", "Hypothesis", f"{agent_name} investigates {hypothesis_id}", hypothesis_id))
        events.append(InvestigationEvent("", "Tool", f"{agent_name} -> {display_tool}()", tool_name))
        result = gateway.invoke(tool_name, incident)
        if result.error:
            events.append(InvestigationEvent("", "ToolError", result.error, tool_name))
            continue
        assert result.evidence is not None
        evidence.append(result.evidence)
        events.append(InvestigationEvent("", "Evidence", result.evidence.summary, result.evidence.evidence_id))
    return agent_name, events, evidence


def _update_hypotheses(hypotheses: list[Hypothesis], evidence: tuple[Evidence, ...]) -> None:
    evidence_ids = {item.evidence_id for item in evidence}
    top = next(item for item in hypotheses if item.hypothesis_id == "H-001")
    top.supporting_evidence_ids.extend(item for item in ("E-001", "E-002", "E-004") if item in evidence_ids)
    top.confidence = 0.93
    top.status = HypothesisStatus.SUPPORTED
    cpu = next(item for item in hypotheses if item.hypothesis_id == "H-002")
    if "E-003" in evidence_ids:
        cpu.confidence = 0.12
        cpu.status = HypothesisStatus.WEAKENED
        cpu.contradicting_evidence_ids.append("E-003")
    platform = next(item for item in hypotheses if item.hypothesis_id == "H-003")
    if "E-005" in evidence_ids:
        platform.confidence = 0.08
        platform.status = HypothesisStatus.WEAKENED
        platform.contradicting_evidence_ids.append("E-005")
