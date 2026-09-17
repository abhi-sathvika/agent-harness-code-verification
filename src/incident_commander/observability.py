from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TraceRecord:
    timestamp: str
    run_id: str
    incident_id: str
    event_type: str
    attributes: dict[str, Any]


class TraceRecorder:
    """Local JSONL trace sink; later replaceable with OpenTelemetry or LangSmith."""

    def __init__(self, path: str):
        self.path = Path(path)

    def record(self, run_id: str, incident_id: str, event_type: str, **attributes: Any) -> None:
        record = TraceRecord(_now(), run_id, incident_id, event_type, attributes)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")


def trace_graph_state(path: str | None, state: dict[str, Any]) -> None:
    if path is None:
        return
    recorder = TraceRecorder(path)
    incident = state["incident"]
    run_id = state["run_id"]
    recorder.record(
        run_id,
        incident.incident_id,
        "run.finished",
        status=state["status"],
        evidence_count=len(state.get("evidence", [])),
        tool_calls_made=state.get("tool_calls_made", 0),
    )
    for event in state.get("events", []):
        recorder.record(
            run_id,
            incident.incident_id,
            f"event.{event['kind'].lower()}",
            message=event["message"],
            ref_id=event.get("ref_id"),
        )


def trace_approval(path: str | None, run_id: str, incident_id: str, approval_id: str, status: str, sandbox_result: dict[str, Any] | None = None) -> None:
    if path is None:
        return
    recorder = TraceRecorder(path)
    attributes: dict[str, Any] = {"approval_id": approval_id, "status": status}
    if sandbox_result is not None:
        attributes["sandbox_status"] = sandbox_result["status"]
        attributes["sandbox_network"] = sandbox_result["plan"]["network"]
    recorder.record(run_id, incident_id, "approval.completed", **attributes)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
