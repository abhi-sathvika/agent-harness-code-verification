from __future__ import annotations

from incident_commander.domain import (
    FinalReport, Hypothesis, HypothesisStatus, Incident, InvestigationEvent,
    ScriptedInvestigation,
)
from incident_commander.tools import run_tool


def investigate_loop(incident: Incident) -> ScriptedInvestigation:
    """Deterministic harness loop: choose tool, observe, update, terminate."""
    if incident.scenario_id != "checkout-db-pool-regression":
        raise ValueError(f"unsupported scenario: {incident.scenario_id}")

    events: list[InvestigationEvent] = [
        InvestigationEvent("12:03:11", "Run", f"Started loop investigation for {incident.incident_id}"),
        InvestigationEvent("12:03:12", "Observe", incident.symptoms[0]),
    ]
    hypotheses = [
        Hypothesis("H-001", "Checkout deployment reduced the database connection pool and caused request queueing.", 0.20),
        Hypothesis("H-002", "Database CPU saturation caused checkout latency.", 0.20),
    ]
    evidence = []
    plan = [
        ("H-001", "query_checkout_latency"),
        ("H-001", "query_database_connections"),
        ("H-002", "query_database_cpu"),
        ("H-001", "inspect_checkout_diff"),
    ]
    second = 13
    for hypothesis_id, tool_name in plan:
        hypothesis = next(item for item in hypotheses if item.hypothesis_id == hypothesis_id)
        events.append(InvestigationEvent(f"12:03:{second:02d}", "Hypothesis", hypothesis.statement, hypothesis_id))
        second += 1
        events.append(InvestigationEvent(f"12:03:{second:02d}", "Tool", f"local -> {tool_name}()", tool_name))
        second += 1
        result = run_tool(tool_name, incident)
        if result.error:
            events.append(InvestigationEvent(f"12:03:{second:02d}", "ToolError", result.error, tool_name))
            second += 1
            continue
        assert result.evidence is not None
        item = result.evidence
        evidence.append(item)
        events.append(InvestigationEvent(f"12:03:{second:02d}", "Evidence", item.summary, item.evidence_id))
        second += 1
        if hypothesis_id == "H-001" and item.evidence_id in {"E-001", "E-002", "E-004"}:
            hypothesis.confidence += 0.24
            hypothesis.supporting_evidence_ids.append(item.evidence_id)
        if hypothesis_id == "H-002" and item.evidence_id == "E-003":
            hypothesis.confidence = 0.12
            hypothesis.status = HypothesisStatus.WEAKENED
            hypothesis.contradicting_evidence_ids.append(item.evidence_id)
    hypotheses[0].confidence = 0.92
    hypotheses[0].status = HypothesisStatus.SUPPORTED
    events.extend([
        InvestigationEvent("12:03:25", "Verify", "Top hypothesis has three independent supporting observations", "H-001"),
        InvestigationEvent("12:03:26", "Resolve", "Recommend human-approved restoration of the pool size to 50"),
    ])
    report = FinalReport(
        "Checkout deployment reduced the database connection pool from 50 to 5, causing connection saturation and request queueing.",
        0.92, ("E-001", "E-002", "E-004"),
        "Require human approval, then restore checkout database pool size to 50 and monitor p95 latency plus connection usage.",
    )
    return ScriptedInvestigation(incident, tuple(events), tuple(hypotheses), tuple(evidence), report)
