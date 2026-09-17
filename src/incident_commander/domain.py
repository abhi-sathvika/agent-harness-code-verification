from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"


class RunStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class HypothesisStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUPPORTED = "SUPPORTED"
    WEAKENED = "WEAKENED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class Incident:
    incident_id: str
    title: str
    service: str
    severity: Severity
    symptoms: tuple[str, ...]
    started_at: str
    scenario_id: str


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    source: str
    summary: str
    supports: tuple[str, ...] = ()
    contradicts: tuple[str, ...] = ()


@dataclass
class Hypothesis:
    hypothesis_id: str
    statement: str
    confidence: float
    status: HypothesisStatus = HypothesisStatus.ACTIVE
    supporting_evidence_ids: list[str] = field(default_factory=list)
    contradicting_evidence_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class InvestigationEvent:
    timestamp: str
    kind: str
    message: str
    ref_id: str | None = None


@dataclass(frozen=True)
class FinalReport:
    root_cause: str
    confidence: float
    evidence_ids: tuple[str, ...]
    recommended_action: str


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    evidence: Evidence | None = None
    error: str | None = None


@dataclass(frozen=True)
class ScriptedInvestigation:
    incident: Incident
    events: tuple[InvestigationEvent, ...]
    hypotheses: tuple[Hypothesis, ...]
    evidence: tuple[Evidence, ...]
    final_report: FinalReport
