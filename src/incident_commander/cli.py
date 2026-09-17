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
from incident_commander.domain import (
    Evidence, FinalReport, Hypothesis, HypothesisStatus, InvestigationEvent, ScriptedInvestigation,
)
from incident_commander.mcp_gateway import build_local_gateway
from incident_commander.checkpoints import CheckpointStore
from incident_commander.sandbox import execute_remediation
from incident_commander.observability import trace_approval, trace_graph_state
from incident_commander.evaluation import evaluate_investigation


DEFAULT_PLAN = [
    ("H-001", "observability.query_checkout_latency"),
    ("H-001", "observability.query_database_connections"),
    ("H-002", "observability.query_database_cpu"),
    ("H-001", "git.inspect_checkout_diff"),
]

KUBERNETES_STEP = ("H-003", "kubernetes.inspect_checkout_workload")


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
    investigate.add_argument("--run-id", help="Use a caller-provided run ID instead of generating one.")
    investigate.add_argument(
        "--pause-after-steps",
        type=int,
        help="Graph mode only: pause after this many investigation tool steps.",
    )
    investigate.add_argument(
        "--compact-after-events",
        type=int,
        help="Graph mode only: keep this many recent events in checkpoint context.",
    )
    investigate.add_argument(
        "--max-tool-calls",
        type=int,
        help="Graph mode only: stop before exceeding this many tool calls.",
    )
    investigate.add_argument(
        "--require-approval",
        action="store_true",
        help="Graph mode only: wait for human approval before remediation.",
    )
    investigate.add_argument(
        "--include-kubernetes",
        action="store_true",
        help="Graph mode only: inspect the simulated Kubernetes workload.",
    )
    investigate.add_argument("--trace-file", help="Write local JSONL trace records.")
    investigate.set_defaults(handler=handle_investigate)

    runs = subcommands.add_parser("runs", help="Inspect and resume checkpointed runs.")
    run_commands = runs.add_subparsers(dest="run_command")

    runs_list = run_commands.add_parser("list", help="List checkpointed runs.")
    runs_list.add_argument("--checkpoint-db", required=True, help="SQLite checkpoint database.")
    runs_list.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    runs_list.set_defaults(handler=handle_runs_list)

    runs_state = run_commands.add_parser("state", help="Show a checkpointed run state.")
    runs_state.add_argument("run_id")
    runs_state.add_argument("--checkpoint-db", required=True, help="SQLite checkpoint database.")
    runs_state.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    runs_state.set_defaults(handler=handle_runs_state)

    runs_resume = run_commands.add_parser("resume", help="Resume a paused graph investigation.")
    runs_resume.add_argument("run_id")
    runs_resume.add_argument("--checkpoint-db", required=True, help="SQLite checkpoint database.")
    runs_resume.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    runs_resume.set_defaults(handler=handle_runs_resume)

    approvals = subcommands.add_parser("approvals", help="Review and approve remediation requests.")
    approval_commands = approvals.add_subparsers(dest="approval_command")

    approvals_approve = approval_commands.add_parser("approve", help="Approve and record a pending remediation.")
    approvals_approve.add_argument("approval_id")
    approvals_approve.add_argument("--checkpoint-db", required=True, help="SQLite checkpoint database.")
    approvals_approve.add_argument(
        "--execute-sandboxed",
        action="store_true",
        help="Execute the approved remediation through the local sandbox boundary.",
    )
    approvals_approve.add_argument("--trace-file", help="Write local JSONL trace records.")
    approvals_approve.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    approvals_approve.set_defaults(handler=handle_approvals_approve)

    evaluate = subcommands.add_parser("evaluate", help="Run evaluation benchmarks.")
    evaluate_commands = evaluate.add_subparsers(dest="evaluate_command")

    evaluate_benchmark = evaluate_commands.add_parser("benchmark", help="Evaluate a benchmark case.")
    evaluate_benchmark.add_argument("benchmark_id", choices=("checkout-latency",))
    evaluate_benchmark.add_argument(
        "--mode",
        choices=("graph", "loop", "scripted"),
        default="graph",
        help="Harness mode to evaluate.",
    )
    evaluate_benchmark.add_argument(
        "--include-kubernetes",
        action="store_true",
        help="Graph mode only: include Kubernetes simulator evidence.",
    )
    evaluate_benchmark.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    evaluate_benchmark.set_defaults(handler=handle_evaluate_benchmark)

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

    run_id = args.run_id or f"run-{uuid.uuid4().hex[:12]}"
    checkpoint_store = CheckpointStore(args.checkpoint_db) if args.checkpoint_db else None
    if args.mode == "graph":
        if args.compact_after_events is not None and args.compact_after_events < 1:
            if checkpoint_store:
                checkpoint_store.close()
            print("--compact-after-events must be at least 1", file=sys.stderr)
            return 2
        if args.max_tool_calls is not None and args.max_tool_calls < 1:
            if checkpoint_store:
                checkpoint_store.close()
            print("--max-tool-calls must be at least 1", file=sys.stderr)
            return 2
        state = _run_graph(_initial_graph_state(
            incident,
            run_id,
            checkpoint_store,
            args.pause_after_steps,
            args.compact_after_events,
            args.max_tool_calls,
            args.require_approval,
            args.include_kubernetes,
        ))
        trace_graph_state(args.trace_file, state)
        return _emit_graph_result(state, args.json, checkpoint_store)
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


def handle_runs_list(args: argparse.Namespace) -> int:
    store = CheckpointStore(args.checkpoint_db)
    rows = store.list_runs()
    store.close()
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for row in rows:
        print(f"{row['run_id']}  {row['status']}  {row['incident_id']}")
    return 0


def handle_runs_state(args: argparse.Namespace) -> int:
    store = CheckpointStore(args.checkpoint_db)
    row = store.load(args.run_id)
    store.close()
    if row is None:
        print(f"run not found: {args.run_id}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(row, indent=2))
        return 0
    state = row["state"]
    print(f"Run: {row['run_id']}")
    print(f"Incident: {row['incident_id']}")
    print(f"Status: {row['status']}")
    print(f"Next step: {state.get('next_index', 0)} of {len(state.get('plan', []))}")
    print(f"Evidence recorded: {len(state.get('evidence', []))}")
    print(f"Tool calls made: {state.get('tool_calls_made', 0)}")
    if state.get("max_tool_calls") is not None:
        print(f"Tool call budget: {state['max_tool_calls']}")
    if state.get("approval_id"):
        print(f"Approval: {state['approval_id']}")
        print(f"Approval action: {state.get('approval_action', '')}")
    if state.get("sandbox_result"):
        result = state["sandbox_result"]
        print(f"Sandbox: {result['status']}")
        print(f"Sandbox image: {result['plan']['image']}")
        print(f"Sandbox network: {result['plan']['network']}")
    print(f"Events recorded: {len(state.get('events', []))}")
    if state.get("compacted_event_count", 0):
        print(f"Events compacted: {state['compacted_event_count']}")
        print(f"Context summary: {state.get('context_summary', '')}")
    return 0


def handle_runs_resume(args: argparse.Namespace) -> int:
    store = CheckpointStore(args.checkpoint_db)
    row = store.load(args.run_id)
    if row is None:
        store.close()
        print(f"run not found: {args.run_id}", file=sys.stderr)
        return 2
    if row["status"] == "COMPLETED":
        store.close()
        print(f"run already completed: {args.run_id}")
        return 0
    if row["status"] == "WAITING_FOR_APPROVAL":
        store.close()
        approval_id = row["state"].get("approval_id")
        print(f"run is waiting for approval: {approval_id}")
        return 0
    if row["status"] == "BUDGET_EXCEEDED":
        store.close()
        print(f"run budget already exceeded: {args.run_id}")
        return 0
    incident = get_incident(row["incident_id"])
    if incident is None:
        store.close()
        return _not_found(row["incident_id"])
    state = _state_from_checkpoint(incident, row, store)
    state = _run_graph(state)
    return _emit_graph_result(state, args.json, store)


def handle_approvals_approve(args: argparse.Namespace) -> int:
    store = CheckpointStore(args.checkpoint_db)
    row = store.load_by_approval(args.approval_id)
    if row is None:
        store.close()
        print(f"approval not found: {args.approval_id}", file=sys.stderr)
        return 2
    if row["status"] != "WAITING_FOR_APPROVAL":
        store.close()
        print(f"approval is not pending: {args.approval_id}", file=sys.stderr)
        return 2
    state = row["state"]
    events = [
        {
            "kind": "Remediate",
            "message": f"Approved remediation: {state.get('approval_action', '')}",
            "ref_id": args.approval_id,
        }
    ]
    state["status"] = "COMPLETED"
    state["approval_status"] = "APPROVED"
    if args.execute_sandboxed:
        result = execute_remediation(state.get("approval_action", ""))
        state["sandbox_result"] = result.to_dict()
        events.append({
            "kind": "Sandbox",
            "message": result.summary,
            "ref_id": args.approval_id,
        })
    state["events"] = [*state.get("events", []), *events]
    store.save(row["run_id"], row["incident_id"], "COMPLETED", state)
    trace_approval(args.trace_file, row["run_id"], row["incident_id"], args.approval_id, "APPROVED", state.get("sandbox_result"))
    store.close()
    if args.json:
        payload = {"approval_id": args.approval_id, "run_id": row["run_id"], "status": "APPROVED"}
        if args.execute_sandboxed:
            payload["sandbox_result"] = state["sandbox_result"]
        print(json.dumps(payload, indent=2))
        return 0
    print(f"Approved: {args.approval_id}")
    print(f"Run: {row['run_id']}")
    print("Status: COMPLETED")
    if args.execute_sandboxed:
        print(f"Sandbox: {state['sandbox_result']['status']}")
        print(f"Sandbox image: {state['sandbox_result']['plan']['image']}")
        print(f"Sandbox network: {state['sandbox_result']['plan']['network']}")
    return 0


def handle_evaluate_benchmark(args: argparse.Namespace) -> int:
    incident = get_incident("INC-001")
    assert incident is not None
    if args.mode == "scripted":
        investigation = investigate_scripted(incident)
        status = "COMPLETED"
        tool_calls = None
    elif args.mode == "loop":
        investigation = investigate_loop(incident)
        status = "COMPLETED"
        tool_calls = None
    else:
        state = _run_graph(_initial_graph_state(
            incident,
            "eval-checkout-latency",
            None,
            include_kubernetes=args.include_kubernetes,
        ))
        investigation = _investigation_from_graph_state(state)
        status = state["status"]
        tool_calls = state.get("tool_calls_made", 0)
    result = evaluate_investigation(investigation, args.mode, status, tool_calls)
    payload = asdict(result)
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(f"Benchmark: {args.benchmark_id}")
    print(f"Mode: {result.mode}")
    print(f"Status: {result.status}")
    print(f"Passed: {str(result.passed).lower()}")
    print(f"Root cause correct: {str(result.root_cause_correct).lower()}")
    print(f"Required evidence found: {str(result.required_evidence_found).lower()}")
    print(f"Evidence correctness: {result.evidence_correctness:.2f}")
    print(f"Unsupported claims: {result.unsupported_claim_count}")
    print(f"False hypotheses: {result.false_hypothesis_count}")
    print(f"Tool calls: {result.tool_calls}")
    return 0


def _run_graph(state: dict) -> dict:
    try:
        from incident_commander.graph import build_investigation_graph
    except ModuleNotFoundError:
        print("LangGraph is not installed; install project dependencies before using graph runs.", file=sys.stderr)
        raise SystemExit(2)
    graph = build_investigation_graph()
    return graph.invoke(state)


def _initial_graph_state(
    incident,
    run_id: str,
    checkpoint_store: CheckpointStore | None,
    pause_after_steps: int | None = None,
    compact_after_events: int | None = None,
    max_tool_calls: int | None = None,
    require_approval: bool = False,
    include_kubernetes: bool = False,
) -> dict:
    plan = [*DEFAULT_PLAN]
    hypotheses = [
        Hypothesis("H-001", "Checkout deployment reduced the database connection pool and caused request queueing.", 0.20),
        Hypothesis("H-002", "Database CPU saturation caused checkout latency.", 0.20),
    ]
    if include_kubernetes:
        plan.insert(3, KUBERNETES_STEP)
        hypotheses.append(Hypothesis("H-003", "Kubernetes pod crashes or an unhealthy rollout caused checkout latency.", 0.15))
    return {
        "incident": incident,
        "hypotheses": hypotheses,
        "evidence": [],
        "plan": plan,
        "next_index": 0,
        "events": [],
        "status": "CREATED",
        "gateway": build_local_gateway(),
        "run_id": run_id,
        "checkpoint_store": checkpoint_store,
        "pause_after_steps": pause_after_steps,
        "compact_after_events": compact_after_events,
        "context_summary": "",
        "compacted_event_count": 0,
        "max_tool_calls": max_tool_calls,
        "tool_calls_made": 0,
        "require_approval": require_approval,
        "approval_id": None,
        "approval_action": None,
    }


def _state_from_checkpoint(incident, row: dict, store: CheckpointStore) -> dict:
    saved = row["state"]
    return {
        "incident": incident,
        "hypotheses": [_decode_hypothesis(item) for item in saved.get("hypotheses", [])],
        "evidence": [_decode_evidence(item) for item in saved.get("evidence", [])],
        "plan": [tuple(item) for item in saved.get("plan", DEFAULT_PLAN)],
        "next_index": saved.get("next_index", 0),
        "events": saved.get("events", []),
        "status": row["status"],
        "gateway": build_local_gateway(),
        "run_id": row["run_id"],
        "checkpoint_store": store,
        "pause_after_steps": None,
        "compact_after_events": saved.get("compact_after_events"),
        "context_summary": saved.get("context_summary", ""),
        "compacted_event_count": saved.get("compacted_event_count", 0),
        "max_tool_calls": saved.get("max_tool_calls"),
        "tool_calls_made": saved.get("tool_calls_made", 0),
        "require_approval": saved.get("require_approval", False),
        "approval_id": saved.get("approval_id"),
        "approval_action": saved.get("approval_action"),
    }


def _decode_hypothesis(item: dict) -> Hypothesis:
    return Hypothesis(
        item["hypothesis_id"],
        item["statement"],
        item["confidence"],
        HypothesisStatus(item.get("status", "ACTIVE")),
        list(item.get("supporting_evidence_ids", [])),
        list(item.get("contradicting_evidence_ids", [])),
    )


def _decode_evidence(item: dict) -> Evidence:
    return Evidence(
        item["evidence_id"],
        item["source"],
        item["summary"],
        tuple(item.get("supports", [])),
        tuple(item.get("contradicts", [])),
    )


def _emit_graph_result(state: dict, emit_json: bool, checkpoint_store: CheckpointStore | None) -> int:
    if checkpoint_store:
        checkpoint_store.close()
    if emit_json:
        print(json.dumps(_jsonable_graph_state(state), indent=2))
        return 0
    if state.get("context_summary"):
        print("Context summary")
        print(state["context_summary"])
        print()
    for i, event in enumerate(state["events"]):
        ref = f" ({event['ref_id']})" if event["ref_id"] else ""
        print(f"[12:03:{i + 11:02d}] {event['kind']}: {event['message']}{ref}")
    print()
    print(f"Run ID: {state['run_id']}")
    if state["status"] == "PAUSED":
        print("Status: PAUSED")
        print(f"Resume: incident-commander runs resume {state['run_id']} --checkpoint-db <path>")
        return 0
    if state["status"] == "BUDGET_EXCEEDED":
        print("Status: BUDGET_EXCEEDED")
        print(f"Tool calls made: {state.get('tool_calls_made', 0)}")
        print(f"Tool call budget: {state.get('max_tool_calls')}")
        return 0
    if state["status"] == "WAITING_FOR_APPROVAL":
        investigation = _investigation_from_graph_state(state)
        print("Final report")
        print(f"Root cause: {investigation.final_report.root_cause}")
        print(f"Confidence: {investigation.final_report.confidence:.2f}")
        print(f"Evidence: {', '.join(investigation.final_report.evidence_ids)}")
        print(f"Recommended action: {investigation.final_report.recommended_action}")
        print("Status: WAITING_FOR_APPROVAL")
        print(f"Approval: {state.get('approval_id')}")
        print(f"Approve: incident-commander approvals approve {state.get('approval_id')} --checkpoint-db <path>")
        return 0
    investigation = _investigation_from_graph_state(state)
    print("Final report")
    print(f"Root cause: {investigation.final_report.root_cause}")
    print(f"Confidence: {investigation.final_report.confidence:.2f}")
    print(f"Evidence: {', '.join(investigation.final_report.evidence_ids)}")
    print(f"Recommended action: {investigation.final_report.recommended_action}")
    return 0


def _investigation_from_graph_state(state: dict) -> ScriptedInvestigation:
    return ScriptedInvestigation(
        state["incident"],
        tuple(InvestigationEvent(f"12:03:{i + 11:02d}", e["kind"], e["message"], e["ref_id"]) for i, e in enumerate(state["events"])),
        tuple(state["hypotheses"]),
        tuple(state["evidence"]),
        FinalReport(
            "Checkout deployment reduced the database connection pool from 50 to 5, causing connection saturation and request queueing.",
            0.92,
            ("E-001", "E-002", "E-004"),
            "Require human approval, then restore checkout database pool size to 50 and monitor p95 latency plus connection usage.",
        ),
    )


def _jsonable_graph_state(state: dict) -> dict:
    investigation = _investigation_from_graph_state(state)
    payload = asdict(investigation)
    payload["run_id"] = state["run_id"]
    payload["status"] = state["status"]
    payload["next_index"] = state["next_index"]
    payload["context_summary"] = state.get("context_summary", "")
    payload["compacted_event_count"] = state.get("compacted_event_count", 0)
    payload["tool_calls_made"] = state.get("tool_calls_made", 0)
    payload["max_tool_calls"] = state.get("max_tool_calls")
    payload["approval_id"] = state.get("approval_id")
    payload["approval_action"] = state.get("approval_action")
    return payload


def _not_found(incident_id: str) -> int:
    print(f"incident not found: {incident_id}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
