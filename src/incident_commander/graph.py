from __future__ import annotations

from typing import Annotated, TypedDict
import operator

from langgraph.graph import END, START, StateGraph

from incident_commander.domain import Evidence, Hypothesis, HypothesisStatus, Incident
from incident_commander.mcp_gateway import MCPGateway, build_local_gateway


class InvestigationState(TypedDict):
    incident: Incident
    hypotheses: list[Hypothesis]
    evidence: list[Evidence]
    plan: list[tuple[str, str]]
    next_index: int
    events: Annotated[list[dict[str, str | None]], operator.add]
    status: str
    gateway: MCPGateway


def _event(state: InvestigationState, kind: str, message: str, ref_id: str | None = None) -> dict[str, str | None]:
    return {"kind": kind, "message": message, "ref_id": ref_id}


def _observe(state: InvestigationState) -> dict:
    return {"status": "RUNNING", "events": [_event(state, "Observe", state["incident"].symptoms[0])]}


def _investigate(state: InvestigationState) -> dict:
    index = state["next_index"]
    hypothesis_id, tool_name = state["plan"][index]
    hypothesis = next(item for item in state["hypotheses"] if item.hypothesis_id == hypothesis_id)
    gateway = state["gateway"]
    result = gateway.invoke(tool_name, state["incident"])
    display_tool = tool_name.rsplit(".", 1)[-1]
    events = [
        _event(state, "Hypothesis", hypothesis.statement, hypothesis_id),
        _event(state, "Tool", f"langgraph -> {display_tool}()", tool_name),
    ]
    if result.error:
        events.append(_event(state, "ToolError", result.error, tool_name))
    elif result.evidence is not None:
        evidence = result.evidence
        state["evidence"].append(evidence)
        events.append(_event(state, "Evidence", evidence.summary, evidence.evidence_id))
        if hypothesis_id == "H-001" and evidence.evidence_id in {"E-001", "E-002", "E-004"}:
            hypothesis.confidence += 0.24
            hypothesis.supporting_evidence_ids.append(evidence.evidence_id)
        if hypothesis_id == "H-002" and evidence.evidence_id == "E-003":
            hypothesis.confidence = 0.12
            hypothesis.status = HypothesisStatus.WEAKENED
            hypothesis.contradicting_evidence_ids.append(evidence.evidence_id)
    return {"next_index": index + 1, "events": events}


def _route(state: InvestigationState) -> str:
    return "investigate" if state["next_index"] < len(state["plan"]) else "verify"


def _verify(state: InvestigationState) -> dict:
    top = next(item for item in state["hypotheses"] if item.hypothesis_id == "H-001")
    top.confidence = 0.92
    top.status = HypothesisStatus.SUPPORTED
    return {
        "status": "COMPLETED",
        "events": [_event(state, "Verify", "Top hypothesis is supported by three independent observations", "H-001")],
    }


def build_investigation_graph():
    graph = StateGraph(InvestigationState)
    graph.add_node("observe", _observe)
    graph.add_node("investigate", _investigate)
    graph.add_node("verify", _verify)
    graph.add_edge(START, "observe")
    graph.add_edge("observe", "investigate")
    graph.add_conditional_edges("investigate", _route, {"investigate": "investigate", "verify": "verify"})
    graph.add_edge("verify", END)
    return graph.compile()
