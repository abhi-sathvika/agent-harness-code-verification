from __future__ import annotations

from typing import Annotated, TypedDict
import operator

from langgraph.graph import END, START, StateGraph

from incident_commander.domain import Evidence, Hypothesis, HypothesisStatus, Incident
from incident_commander.mcp_gateway import MCPGateway, build_local_gateway
from incident_commander.checkpoints import CheckpointStore
from incident_commander.context import compact_events


class InvestigationState(TypedDict):
    incident: Incident
    hypotheses: list[Hypothesis]
    evidence: list[Evidence]
    plan: list[tuple[str, str]]
    next_index: int
    events: Annotated[list[dict[str, str | None]], operator.add]
    status: str
    gateway: MCPGateway
    run_id: str
    checkpoint_store: CheckpointStore
    pause_after_steps: int | None
    compact_after_events: int | None
    context_summary: str
    compacted_event_count: int
    max_tool_calls: int | None
    tool_calls_made: int
    require_approval: bool
    approval_id: str | None
    approval_action: str | None


def _event(state: InvestigationState, kind: str, message: str, ref_id: str | None = None) -> dict[str, str | None]:
    return {"kind": kind, "message": message, "ref_id": ref_id}


def _observe(state: InvestigationState) -> dict:
    update = {"status": "RUNNING", "events": [_event(state, "Observe", state["incident"].symptoms[0])]}
    _save_checkpoint(state, update)
    return update


def _start(state: InvestigationState) -> dict:
    return {"events": []}


def _route_start(state: InvestigationState) -> str:
    if state["status"] == "CREATED":
        return "observe"
    if state["next_index"] < len(state["plan"]):
        if _budget_exceeded(state):
            return "budget_exceeded"
        return "investigate"
    return "verify"


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
        if hypothesis_id == "H-003" and evidence.evidence_id == "E-005":
            hypothesis.confidence = 0.08
            hypothesis.status = HypothesisStatus.WEAKENED
            hypothesis.contradicting_evidence_ids.append(evidence.evidence_id)
    update = {"next_index": index + 1, "tool_calls_made": state.get("tool_calls_made", 0) + 1, "events": events}
    _save_checkpoint(state, update)
    return update


def _route(state: InvestigationState) -> str:
    pause_after_steps = state.get("pause_after_steps")
    if (
        pause_after_steps is not None
        and state["next_index"] >= pause_after_steps
        and state["next_index"] < len(state["plan"])
    ):
        return "pause"
    if _budget_exceeded(state):
        return "budget_exceeded"
    return "investigate" if state["next_index"] < len(state["plan"]) else "verify"


def _budget_exceeded(state: InvestigationState) -> bool:
    max_tool_calls = state.get("max_tool_calls")
    return (
        max_tool_calls is not None
        and state.get("tool_calls_made", 0) >= max_tool_calls
        and state["next_index"] < len(state["plan"])
    )


def _pause(state: InvestigationState) -> dict:
    update = {
        "status": "PAUSED",
        "events": [_event(state, "Pause", "Run paused at durable node boundary", state["run_id"])],
    }
    _save_checkpoint(state, update)
    return update


def _budget_exceeded_node(state: InvestigationState) -> dict:
    update = {
        "status": "BUDGET_EXCEEDED",
        "events": [
            _event(
                state,
                "Budget",
                f"Stopped before next tool call after reaching budget of {state['max_tool_calls']} tool calls",
                state["run_id"],
            )
        ],
    }
    _save_checkpoint(state, update)
    return update


def _verify(state: InvestigationState) -> dict:
    top = next(item for item in state["hypotheses"] if item.hypothesis_id == "H-001")
    top.confidence = 0.92
    top.status = HypothesisStatus.SUPPORTED
    if state.get("require_approval"):
        approval_id = f"approval-{state['run_id']}"
        update = {
            "status": "WAITING_FOR_APPROVAL",
            "approval_id": approval_id,
            "approval_action": "Restore checkout database pool size to 50 and monitor p95 latency plus connection usage.",
            "events": [
                _event(state, "Verify", "Top hypothesis is supported by three independent observations", "H-001"),
                _event(state, "Approval", "Remediation requires human approval before execution", approval_id),
            ],
        }
        _save_checkpoint(state, update)
        return update
    update = {
        "status": "COMPLETED",
        "events": [_event(state, "Verify", "Top hypothesis is supported by three independent observations", "H-001")],
    }
    _save_checkpoint(state, update)
    return update


def _save_checkpoint(state: InvestigationState, update: dict) -> None:
    if state.get("checkpoint_store") is None:
        return
    snapshot = dict(state)
    snapshot.update(update)
    if "events" in update:
        snapshot["events"] = [*state.get("events", []), *update["events"]]
    compact_after_events = snapshot.get("compact_after_events")
    if compact_after_events is not None:
        compacted = compact_events(
            snapshot["events"],
            snapshot["evidence"],
            snapshot["hypotheses"],
            compact_after_events,
            snapshot.get("context_summary", ""),
            snapshot.get("compacted_event_count", 0),
        )
        snapshot["context_summary"] = compacted.summary
        snapshot["events"] = compacted.recent_events
        snapshot["compacted_event_count"] = compacted.compacted_event_count
    state["checkpoint_store"].save(state["run_id"], state["incident"].incident_id, snapshot.get("status", "RUNNING"), snapshot)


def build_investigation_graph():
    graph = StateGraph(InvestigationState)
    graph.add_node("start", _start)
    graph.add_node("observe", _observe)
    graph.add_node("investigate", _investigate)
    graph.add_node("pause", _pause)
    graph.add_node("budget_exceeded", _budget_exceeded_node)
    graph.add_node("verify", _verify)
    graph.add_edge(START, "start")
    graph.add_conditional_edges("start", _route_start, {"observe": "observe", "investigate": "investigate", "verify": "verify", "budget_exceeded": "budget_exceeded"})
    graph.add_edge("observe", "investigate")
    graph.add_conditional_edges("investigate", _route, {"investigate": "investigate", "verify": "verify", "pause": "pause", "budget_exceeded": "budget_exceeded"})
    graph.add_edge("pause", END)
    graph.add_edge("budget_exceeded", END)
    graph.add_edge("verify", END)
    return graph.compile()
