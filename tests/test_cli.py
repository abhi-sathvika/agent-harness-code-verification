from __future__ import annotations

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
    result = gateway.invoke("observability.query_database_connections", incident)
    assert result.evidence is not None
    assert result.evidence.evidence_id == "E-002"
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
