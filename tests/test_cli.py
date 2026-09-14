from __future__ import annotations

from incident_commander.cli import main


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
