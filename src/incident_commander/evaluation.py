from __future__ import annotations

from dataclasses import dataclass

from incident_commander.domain import HypothesisStatus, ScriptedInvestigation


REQUIRED_EVIDENCE_IDS = ("E-001", "E-002", "E-004")
ROOT_CAUSE_TERMS = ("connection pool", "50", "5", "saturation")


@dataclass(frozen=True)
class EvaluationResult:
    incident_id: str
    mode: str
    status: str
    passed: bool
    root_cause_correct: bool
    required_evidence_found: bool
    evidence_correctness: float
    unsupported_claim_count: int
    false_hypothesis_count: int
    tool_calls: int


def evaluate_investigation(
    investigation: ScriptedInvestigation,
    mode: str,
    status: str = "COMPLETED",
    tool_calls: int | None = None,
) -> EvaluationResult:
    evidence_ids = set(investigation.final_report.evidence_ids)
    required = set(REQUIRED_EVIDENCE_IDS)
    found_required = evidence_ids & required
    root_cause = investigation.final_report.root_cause.lower()
    root_cause_correct = all(term in root_cause for term in ROOT_CAUSE_TERMS)
    required_evidence_found = required.issubset(evidence_ids)
    unsupported_claim_count = len(required - evidence_ids)
    false_hypothesis_count = sum(
        1
        for hypothesis in investigation.hypotheses
        if hypothesis.hypothesis_id != "H-001"
        and hypothesis.status not in {HypothesisStatus.WEAKENED, HypothesisStatus.REJECTED}
        and hypothesis.confidence >= 0.20
    )
    effective_tool_calls = tool_calls
    if effective_tool_calls is None:
        effective_tool_calls = sum(1 for event in investigation.events if event.kind == "Tool")
    passed = (
        status == "COMPLETED"
        and root_cause_correct
        and required_evidence_found
        and unsupported_claim_count == 0
        and false_hypothesis_count == 0
    )
    return EvaluationResult(
        investigation.incident.incident_id,
        mode,
        status,
        passed,
        root_cause_correct,
        required_evidence_found,
        len(found_required) / len(required),
        unsupported_claim_count,
        false_hypothesis_count,
        effective_tool_calls,
    )
