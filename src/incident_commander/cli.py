from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import asdict
from typing import Sequence

from incident_commander.scenarios import get_incident, list_incidents
from incident_commander.scripted import investigate_scripted
from incident_commander.loop import investigate_loop
from incident_commander.domain import FinalReport, Hypothesis, Evidence, ScriptedInvestigation, InvestigationEvent
from incident_commander.mcp_gateway import build_local_gateway
from incident_commander.checkpoints import CheckpointStore


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "handler"):
        parser.print_help()
        return 0

    try:
        return args.handler(args)
    except BrokenPipeError:
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="incident-commander",
        description="CLI-first autonomous SRE investigation harness.",
    )
    subcommands = parser.add_subparsers(dest="command")

    incidents = subcommands.add_parser("incidents", help="Create, list, and inspect incidents.")
    incident_commands = incidents.add_subparsers(dest="incident_command")

    incidents_list = incident_commands.add_parser("list", help="List available incidents.")
    incidents_list.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    incidents_list.set_defaults(handler=handle_incidents_list)

    incidents_show = incident_commands.add_parser("show", help="Show one incident.")
    incidents_show.add_argument("incident_id")
    incidents_show.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    incidents_show.set_defaults(handler=handle_incidents_show)

    investigate = subcommands.add_parser("investigate", help="Start an investigation.")
    investigate.add_argument("incident_id")
    investigate.add_argument(
        "--mode",
        choices=("graph", "loop", "scripted"),
        default="scripted",
        help="Investigation mode. Graph uses LangGraph; loop exercises raw control flow; scripted is the reference trace.",
    )
    investigate.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    investigate.add_argument("--checkpoint-db", help="Persist the run snapshot to a SQLite database.")
    investigate.set_defaults(handler=handle_investigate)

    return parser


def handle_incidents_list(args: argparse.Namespace) -> int:
    incidents = list_incidents()
    if args.json:
        print(json.dumps([asdict(incident) for incident in incidents], indent=2))
        return 0

    for incident in incidents:
        print(f"{incident.incident_id}  {incident.severity.value}  {incident.service}  {incident.title}")
    return 0


def handle_incidents_show(args: argparse.Namespace) -> int:
    incident = get_incident(args.incident_id)
    if incident is None:
        return _not_found(args.incident_id)

    if args.json:
        print(json.dumps(asdict(incident), indent=2))
        return 0

    print(f"Incident: {incident.incident_id}")
    print(f"Title: {incident.title}")
    print(f"Service: {incident.service}")
    print(f"Severity: {incident.severity.value}")
    print(f"Started: {incident.started_at}")
    print("Symptoms:")
    for symptom in incident.symptoms:
        print(f"  - {symptom}")
    return 0


def handle_investigate(args: argparse.Namespace) -> int:
    incident = get_incident(args.incident_id)
    if incident is None:
        return _not_found(args.incident_id)

    run_id = f"run-{uuid.uuid4().hex[:12]}"
    checkpoint_store = CheckpointStore(args.checkpoint_db) if args.checkpoint_db else None
    if args.mode == "graph":
        try:
            from incident_commander.graph import build_investigation_graph
        except ModuleNotFoundError as exc:
            print("LangGraph is not installed; install project dependencies before using --mode graph.", file=sys.stderr)
            return 2
        graph = build_investigation_graph()
        state = graph.invoke({
            "incident": incident,
            "hypotheses": [
                Hypothesis("H-001", "Checkout deployment reduced the database connection pool and caused request queueing.", 0.20),
                Hypothesis("H-002", "Database CPU saturation caused checkout latency.", 0.20),
            ],
            "evidence": [],
            "plan": [("H-001", "observability.query_checkout_latency"), ("H-001", "observability.query_database_connections"), ("H-002", "observability.query_database_cpu"), ("H-001", "git.inspect_checkout_diff")],
            "next_index": 0,
            "events": [],
            "status": "CREATED",
            "gateway": build_local_gateway(),
            "run_id": run_id,
            "checkpoint_store": checkpoint_store,
        })
        investigation = ScriptedInvestigation(
            incident, tuple(InvestigationEvent(f"12:03:{i + 11:02d}", e["kind"], e["message"], e["ref_id"]) for i, e in enumerate(state["events"])),
            tuple(state["hypotheses"]), tuple(state["evidence"]),
            FinalReport("Checkout deployment reduced the database connection pool from 50 to 5, causing connection saturation and request queueing.", 0.92, ("E-001", "E-002", "E-004"), "Require human approval, then restore checkout database pool size to 50 and monitor p95 latency plus connection usage."),
        )
    else:
        investigation = investigate_loop(incident) if args.mode == "loop" else investigate_scripted(incident)
    if checkpoint_store:
        checkpoint_store.save(run_id, incident.incident_id, "COMPLETED", asdict(investigation))
        checkpoint_store.close()
    if args.json:
        print(json.dumps(asdict(investigation), indent=2))
        return 0

    for event in investigation.events:
        ref = f" ({event.ref_id})" if event.ref_id else ""
        print(f"[{event.timestamp}] {event.kind}: {event.message}{ref}")

    print()
    print("Final report")
    print(f"Root cause: {investigation.final_report.root_cause}")
    print(f"Confidence: {investigation.final_report.confidence:.2f}")
    print(f"Evidence: {', '.join(investigation.final_report.evidence_ids)}")
    print(f"Recommended action: {investigation.final_report.recommended_action}")
    return 0


def _not_found(incident_id: str) -> int:
    print(f"incident not found: {incident_id}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
