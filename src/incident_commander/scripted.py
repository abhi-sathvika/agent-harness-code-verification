from __future__ import annotations

from incident_commander.domain import (
    Evidence,
    FinalReport,
    Hypothesis,
    HypothesisStatus,
    Incident,
    InvestigationEvent,
    ScriptedInvestigation,
)


def investigate_scripted(incident: Incident) -> ScriptedInvestigation:
    if incident.scenario_id != "checkout-db-pool-regression":
        raise ValueError(f"unsupported scenario: {incident.scenario_id}")

    evidence = (
        Evidence(
            evidence_id="E-001",
            source="metrics.checkout.latency",
            summary="Checkout p95 latency rose from 250ms to 1000ms after deployment 2026.09.14-17.",
            supports=("H-001",),
        ),
        Evidence(
            evidence_id="E-002",
            source="metrics.database.connections",
            summary="Database connection usage reached 97% of the checkout pool limit during the incident.",
            supports=("H-001",),
        ),
        Evidence(
            evidence_id="E-003",
            source="metrics.database.cpu",
            summary="Database CPU remained below 45%, weakening the database CPU saturation hypothesis.",
            contradicts=("H-002",),
        ),
        Evidence(
            evidence_id="E-004",
            source="git.diff.checkout",
            summary="Recent deployment changed checkout database pool size from 50 to 5.",
            supports=("H-001",),
        ),
    )

    hypotheses = (
        Hypothesis(
            hypothesis_id="H-001",
            statement="Checkout deployment reduced the database connection pool and caused request queueing.",
            confidence=0.92,
            status=HypothesisStatus.SUPPORTED,
            supporting_evidence_ids=["E-001", "E-002", "E-004"],
        ),
        Hypothesis(
            hypothesis_id="H-002",
            statement="Database CPU saturation caused checkout latency.",
            confidence=0.12,
            status=HypothesisStatus.WEAKENED,
            contradicting_evidence_ids=["E-003"],
        ),
    )

    events = (
        InvestigationEvent("12:03:11", "Run", f"Started scripted investigation for {incident.incident_id}"),
        InvestigationEvent("12:03:12", "Observe", "Symptom: checkout p95 latency increased 4x after deployment"),
        InvestigationEvent("12:03:13", "Hypothesis", hypotheses[0].statement, "H-001"),
        InvestigationEvent("12:03:14", "Tool", "MCP -> query_metrics(service='checkout', metric='p95_latency')"),
        InvestigationEvent("12:03:15", "Evidence", evidence[0].summary, "E-001"),
        InvestigationEvent("12:03:16", "Tool", "MCP -> query_metrics(service='database', metric='connections')"),
        InvestigationEvent("12:03:17", "Evidence", evidence[1].summary, "E-002"),
        InvestigationEvent("12:03:18", "Hypothesis", hypotheses[1].statement, "H-002"),
        InvestigationEvent("12:03:19", "Tool", "MCP -> query_metrics(service='database', metric='cpu')"),
        InvestigationEvent("12:03:20", "Evidence", evidence[2].summary, "E-003"),
        InvestigationEvent("12:03:21", "Tool", "MCP -> inspect_git_diff(service='checkout', deployment='2026.09.14-17')"),
        InvestigationEvent("12:03:22", "Evidence", evidence[3].summary, "E-004"),
        InvestigationEvent("12:03:23", "Verify", "Root cause is supported by latency, connection, and Git evidence"),
        InvestigationEvent("12:03:24", "Resolve", "Recommend reverting pool size to 50 or applying a safe config patch"),
    )

    final_report = FinalReport(
        root_cause="Checkout deployment reduced the database connection pool from 50 to 5, causing connection saturation and request queueing.",
        confidence=0.92,
        evidence_ids=("E-001", "E-002", "E-004"),
        recommended_action="Require human approval, then restore checkout database pool size to 50 and monitor p95 latency plus connection usage.",
    )

    return ScriptedInvestigation(
        incident=incident,
        events=events,
        hypotheses=hypotheses,
        evidence=evidence,
        final_report=final_report,
    )
