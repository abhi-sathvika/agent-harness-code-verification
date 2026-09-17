from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CompactedContext:
    summary: str
    recent_events: list[dict[str, Any]]
    compacted_event_count: int


def compact_events(
    events: list[dict[str, Any]],
    evidence: list[Any],
    hypotheses: list[Any],
    keep_recent: int,
    previous_summary: str = "",
    previous_count: int = 0,
) -> CompactedContext:
    """Create a deterministic context summary while keeping recent raw events."""
    if keep_recent < 1:
        raise ValueError("keep_recent must be at least 1")
    if len(events) <= keep_recent:
        return CompactedContext(previous_summary, events, previous_count)

    compacted = events[:-keep_recent]
    recent = events[-keep_recent:]
    count = previous_count + len(compacted)
    evidence_ids = [getattr(item, "evidence_id", None) or item.get("evidence_id") for item in evidence]
    evidence_ids = [item for item in evidence_ids if item]
    top_hypothesis = _top_hypothesis(hypotheses)
    last = compacted[-1]
    last_message = str(last.get("message", "")).rstrip(".")
    parts = []
    if previous_summary:
        parts.append(previous_summary)
    parts.append(
        f"Compacted {count} earlier events; last compacted event was "
        f"{last.get('kind')}: {last_message}."
    )
    if evidence_ids:
        parts.append(f"Evidence retained in ledger: {', '.join(evidence_ids)}.")
    if top_hypothesis:
        parts.append(f"Leading hypothesis: {top_hypothesis}.")
    return CompactedContext(" ".join(parts), recent, count)


def _top_hypothesis(hypotheses: list[Any]) -> str:
    if not hypotheses:
        return ""
    top = max(hypotheses, key=lambda item: getattr(item, "confidence", 0.0) if not isinstance(item, dict) else item.get("confidence", 0.0))
    if isinstance(top, dict):
        return top.get("statement", "")
    return getattr(top, "statement", "")
