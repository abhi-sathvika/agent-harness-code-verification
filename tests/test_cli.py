from __future__ import annotations

import json

from incident_commander.cli import main
from incident_commander.mcp_gateway import build_local_gateway
from incident_commander.scenarios import get_incident
from incident_commander.checkpoints import CheckpointStore


def test_incidents_list(capsys):
    exit_code = main(["incidents", "list"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "INC-001" in captured.out
    assert "checkout" in captured.out


def test_incidents_show(capsys):
    exit_code = main(["incidents", "show", "INC-001"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Checkout API latency increased 4x" in captured.out
    assert "checkout p95 latency increased" in captured.out


def test_scripted_investigation_contains_evidence_backed_root_cause(capsys):
    exit_code = main(["investigate", "INC-001"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Hypothesis:" in captured.out
    assert "Evidence:" in captured.out
    assert "Root cause:" in captured.out
    assert "E-001, E-002, E-004" in captured.out
    assert "connection pool from 50 to 5" in captured.out


def test_unknown_incident_returns_error(capsys):
    exit_code = main(["incidents", "show", "INC-404"])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "incident not found: INC-404" in captured.err


def test_loop_investigation_updates_hypotheses_and_evidence(capsys):
    exit_code = main(["investigate", "INC-001", "--mode", "loop"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "local -> query_database_connections()" in captured.out
    assert "Top hypothesis has three independent supporting observations" in captured.out
    assert "connection pool from 50 to 5" in captured.out


def test_graph_investigation_preserves_event_trace(capsys):
    exit_code = main(["investigate", "INC-001", "--mode", "graph"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "langgraph -> query_checkout_latency()" in captured.out
    assert "langgraph -> inspect_checkout_diff()" in captured.out
    assert "E-001, E-002, E-004" in captured.out


def test_mcp_gateway_discovers_and_routes_tools():
    gateway = build_local_gateway()
    incident = get_incident("INC-001")
    assert incident is not None
    names = {tool.server + "." + tool.name for tool in gateway.discover()}
    assert "observability.query_database_connections" in names
    assert "kubernetes.inspect_checkout_workload" in names
    result = gateway.invoke("observability.query_database_connections", incident)
    assert result.evidence is not None
    assert result.evidence.evidence_id == "E-002"
    kube = gateway.invoke("kubernetes.inspect_checkout_workload", incident)
    assert kube.evidence is not None
    assert kube.evidence.evidence_id == "E-005"
    assert "2/2 ready replicas" in kube.evidence.summary
    assert gateway.invoke("unknown.query", incident).error == "MCP server not found: unknown"


def test_checkpoint_store_round_trips_state(tmp_path):
    store = CheckpointStore(str(tmp_path / "runs.db"))
    store.save("run-1", "INC-001", "RUNNING", {"next_index": 2, "events": []})
    loaded = store.load("run-1")
    store.close()

    assert loaded == {"run_id": "run-1", "incident_id": "INC-001", "status": "RUNNING", "state": {"next_index": 2, "events": []}}


def test_graph_writes_node_boundary_checkpoint(tmp_path, capsys):
    db = str(tmp_path / "runs.db")
    assert main(["investigate", "INC-001", "--mode", "graph", "--checkpoint-db", db]) == 0
    store = CheckpointStore(db)
    rows = store.connection.execute("select status from checkpoints").fetchall()
    store.close()
    capsys.readouterr()
    assert rows == [("COMPLETED",)]


def test_graph_run_can_pause_and_resume_from_checkpoint(tmp_path, capsys):
    db = str(tmp_path / "runs.db")
    run_id = "run-test-resume"

    assert main([
        "investigate", "INC-001", "--mode", "graph", "--checkpoint-db", db,
        "--run-id", run_id, "--pause-after-steps", "2",
    ]) == 0
    paused = capsys.readouterr()
    assert "Status: PAUSED" in paused.out

    assert main(["runs", "state", run_id, "--checkpoint-db", db]) == 0
    state = capsys.readouterr()
    assert "Status: PAUSED" in state.out
    assert "Next step: 2 of 4" in state.out
    assert "Evidence recorded: 2" in state.out

    assert main(["runs", "resume", run_id, "--checkpoint-db", db]) == 0
    resumed = capsys.readouterr()
    assert "Root cause:" in resumed.out
    assert "E-001, E-002, E-004" in resumed.out

    store = CheckpointStore(db)
    loaded = store.load(run_id)
    store.close()
    assert loaded is not None
    assert loaded["status"] == "COMPLETED"


def test_graph_checkpoint_compacts_context_for_resume(tmp_path, capsys):
    db = str(tmp_path / "runs.db")
    run_id = "run-test-compact"

    assert main([
        "investigate", "INC-001", "--mode", "graph", "--checkpoint-db", db,
        "--run-id", run_id, "--pause-after-steps", "2", "--compact-after-events", "3",
    ]) == 0
    capsys.readouterr()

    store = CheckpointStore(db)
    loaded = store.load(run_id)
    store.close()
    assert loaded is not None
    state = loaded["state"]
    assert loaded["status"] == "PAUSED"
    assert len(state["events"]) == 3
    assert state["compacted_event_count"] == 5
    assert "Compacted 5 earlier events" in state["context_summary"]
    assert [item["evidence_id"] for item in state["evidence"]] == ["E-001", "E-002"]

    assert main(["runs", "state", run_id, "--checkpoint-db", db]) == 0
    inspected = capsys.readouterr()
    assert "Events recorded: 3" in inspected.out
    assert "Events compacted: 5" in inspected.out

    assert main(["runs", "resume", run_id, "--checkpoint-db", db]) == 0
    resumed = capsys.readouterr()
    assert "Context summary" in resumed.out
    assert "Root cause:" in resumed.out


def test_graph_stops_before_exceeding_tool_call_budget(tmp_path, capsys):
    db = str(tmp_path / "runs.db")
    run_id = "run-test-budget"

    assert main([
        "investigate", "INC-001", "--mode", "graph", "--checkpoint-db", db,
        "--run-id", run_id, "--max-tool-calls", "2",
    ]) == 0
    captured = capsys.readouterr()
    assert "Status: BUDGET_EXCEEDED" in captured.out
    assert "Tool calls made: 2" in captured.out
    assert "Root cause:" not in captured.out

    store = CheckpointStore(db)
    loaded = store.load(run_id)
    store.close()
    assert loaded is not None
    assert loaded["status"] == "BUDGET_EXCEEDED"
    assert loaded["state"]["tool_calls_made"] == 2
    assert loaded["state"]["next_index"] == 2

    assert main(["runs", "state", run_id, "--checkpoint-db", db]) == 0
    inspected = capsys.readouterr()
    assert "Status: BUDGET_EXCEEDED" in inspected.out
    assert "Tool calls made: 2" in inspected.out
    assert "Tool call budget: 2" in inspected.out


def test_graph_requires_human_approval_before_remediation(tmp_path, capsys):
    db = str(tmp_path / "runs.db")
    run_id = "run-test-approval"
    approval_id = f"approval-{run_id}"

    assert main([
        "investigate", "INC-001", "--mode", "graph", "--checkpoint-db", db,
        "--run-id", run_id, "--require-approval",
    ]) == 0
    waiting = capsys.readouterr()
    assert "Status: WAITING_FOR_APPROVAL" in waiting.out
    assert f"Approval: {approval_id}" in waiting.out
    assert "Approve:" in waiting.out

    store = CheckpointStore(db)
    loaded = store.load(run_id)
    by_approval = store.load_by_approval(approval_id)
    store.close()
    assert loaded is not None
    assert by_approval is not None
    assert loaded["status"] == "WAITING_FOR_APPROVAL"
    assert loaded["state"]["approval_action"].startswith("Restore checkout database pool size")

    assert main(["runs", "state", run_id, "--checkpoint-db", db]) == 0
    state = capsys.readouterr()
    assert "Status: WAITING_FOR_APPROVAL" in state.out
    assert f"Approval: {approval_id}" in state.out

    assert main(["approvals", "approve", approval_id, "--checkpoint-db", db]) == 0
    approved = capsys.readouterr()
    assert f"Approved: {approval_id}" in approved.out
    assert "Status: COMPLETED" in approved.out

    store = CheckpointStore(db)
    completed = store.load(run_id)
    store.close()
    assert completed is not None
    assert completed["status"] == "COMPLETED"
    assert completed["state"]["approval_status"] == "APPROVED"
    assert completed["state"]["events"][-1]["kind"] == "Remediate"


def test_approved_remediation_can_execute_through_sandbox_boundary(tmp_path, capsys):
    db = str(tmp_path / "runs.db")
    run_id = "run-test-sandbox"
    approval_id = f"approval-{run_id}"

    assert main([
        "investigate", "INC-001", "--mode", "graph", "--checkpoint-db", db,
        "--run-id", run_id, "--require-approval",
    ]) == 0
    capsys.readouterr()

    assert main([
        "approvals", "approve", approval_id, "--checkpoint-db", db, "--execute-sandboxed",
    ]) == 0
    approved = capsys.readouterr()
    assert "Sandbox: SUCCEEDED" in approved.out
    assert "Sandbox network: none" in approved.out

    store = CheckpointStore(db)
    completed = store.load(run_id)
    store.close()
    assert completed is not None
    result = completed["state"]["sandbox_result"]
    assert result["status"] == "SUCCEEDED"
    assert result["plan"]["network"] == "none"
    assert result["plan"]["read_only_rootfs"] is True
    assert result["plan"]["drop_capabilities"] == ["ALL"]
    assert completed["state"]["events"][-1]["kind"] == "Sandbox"

    assert main(["runs", "state", run_id, "--checkpoint-db", db]) == 0
    state = capsys.readouterr()
    assert "Sandbox: SUCCEEDED" in state.out
    assert "Sandbox image: incident-commander/remediation-runner:local" in state.out


def test_graph_can_inspect_simulated_kubernetes_workload(capsys):
    assert main(["investigate", "INC-001", "--mode", "graph", "--include-kubernetes"]) == 0
    captured = capsys.readouterr()
    assert "langgraph -> inspect_checkout_workload()" in captured.out
    assert "2/2 ready replicas" in captured.out
    assert "E-001, E-002, E-004" in captured.out


def test_parallel_investigation_merges_subagent_evidence(capsys):
    assert main(["investigate", "INC-001", "--mode", "parallel"]) == 0
    captured = capsys.readouterr()
    assert "Merged findings from metrics-agent" in captured.out
    assert "Merged findings from change-agent" in captured.out
    assert "Merged findings from platform-agent" in captured.out
    assert "metrics-agent -> query_database_connections()" in captured.out
    assert "platform-agent -> inspect_checkout_workload()" in captured.out
    assert "E-001, E-002, E-004" in captured.out


def test_graph_writes_local_trace_records(tmp_path, capsys):
    trace_file = tmp_path / "trace.jsonl"

    assert main([
        "investigate", "INC-001", "--mode", "graph", "--include-kubernetes",
        "--run-id", "run-test-trace", "--trace-file", str(trace_file),
    ]) == 0
    capsys.readouterr()

    records = [json.loads(line) for line in trace_file.read_text().splitlines()]
    event_types = [record["event_type"] for record in records]
    assert event_types[0] == "run.finished"
    assert "event.tool" in event_types
    assert "event.evidence" in event_types
    assert records[0]["run_id"] == "run-test-trace"
    assert records[0]["attributes"]["status"] == "COMPLETED"
    assert records[0]["attributes"]["tool_calls_made"] == 5
    assert any(record["attributes"].get("ref_id") == "kubernetes.inspect_checkout_workload" for record in records)


def test_approval_writes_trace_record_with_sandbox_attributes(tmp_path, capsys):
    db = str(tmp_path / "runs.db")
    trace_file = tmp_path / "approval-trace.jsonl"
    run_id = "run-test-approval-trace"
    approval_id = f"approval-{run_id}"

    assert main([
        "investigate", "INC-001", "--mode", "graph", "--checkpoint-db", db,
        "--run-id", run_id, "--require-approval",
    ]) == 0
    capsys.readouterr()

    assert main([
        "approvals", "approve", approval_id, "--checkpoint-db", db,
        "--execute-sandboxed", "--trace-file", str(trace_file),
    ]) == 0
    capsys.readouterr()

    records = [json.loads(line) for line in trace_file.read_text().splitlines()]
    assert records == [{
        "timestamp": records[0]["timestamp"],
        "run_id": run_id,
        "incident_id": "INC-001",
        "event_type": "approval.completed",
        "attributes": {
            "approval_id": approval_id,
            "sandbox_network": "none",
            "sandbox_status": "SUCCEEDED",
            "status": "APPROVED",
        },
    }]


def test_evaluate_benchmark_scores_graph_harness(capsys):
    assert main(["evaluate", "benchmark", "checkout-latency", "--mode", "graph"]) == 0
    captured = capsys.readouterr()
    assert "Benchmark: checkout-latency" in captured.out
    assert "Mode: graph" in captured.out
    assert "Passed: true" in captured.out
    assert "Evidence correctness: 1.00" in captured.out
    assert "Tool calls: 4" in captured.out


def test_evaluate_benchmark_json_includes_kubernetes_experiment(capsys):
    assert main([
        "evaluate", "benchmark", "checkout-latency", "--mode", "graph",
        "--include-kubernetes", "--json",
    ]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["passed"] is True
    assert payload["root_cause_correct"] is True
    assert payload["required_evidence_found"] is True
    assert payload["tool_calls"] == 5


def test_evaluate_benchmark_scores_parallel_harness(capsys):
    assert main(["evaluate", "benchmark", "checkout-latency", "--mode", "parallel", "--json"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["passed"] is True
    assert payload["mode"] == "parallel"
    assert payload["tool_calls"] == 5


def test_evaluate_compare_reports_all_harness_modes(capsys):
    assert main(["evaluate", "compare", "checkout-latency"]) == 0
    captured = capsys.readouterr()
    assert "Mode              Passed" in captured.out
    assert "scripted" in captured.out
    assert "loop" in captured.out
    assert "graph" in captured.out
    assert "graph+kubernetes" in captured.out
    assert "parallel" in captured.out


def test_evaluate_compare_json_includes_experiment_rows(capsys):
    assert main(["evaluate", "compare", "checkout-latency", "--json"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    modes = [row["mode"] for row in payload]
    assert modes == ["scripted", "loop", "graph", "graph+kubernetes", "parallel"]
    assert all(row["passed"] for row in payload)
    assert payload[3]["tool_calls"] == 5
