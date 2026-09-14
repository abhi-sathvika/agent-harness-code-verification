from __future__ import annotations

from incident_commander.domain import Evidence, Incident, ToolResult


def run_tool(tool_name: str, incident: Incident) -> ToolResult:
    """Small in-process tool boundary used before MCP is introduced."""
    if incident.scenario_id != "checkout-db-pool-regression":
        return ToolResult(tool_name, error=f"unsupported scenario: {incident.scenario_id}")

    evidence_by_tool = {
        "query_checkout_latency": Evidence(
            "E-001", "metrics.checkout.latency",
            "Checkout p95 latency rose from 250ms to 1000ms after deployment 2026.09.14-17.",
            supports=("H-001",),
        ),
        "query_database_connections": Evidence(
            "E-002", "metrics.database.connections",
            "Database connection usage reached 97% of the checkout pool limit during the incident.",
            supports=("H-001",),
        ),
        "query_database_cpu": Evidence(
            "E-003", "metrics.database.cpu",
            "Database CPU remained below 45%, weakening the database CPU saturation hypothesis.",
            contradicts=("H-002",),
        ),
        "inspect_checkout_diff": Evidence(
            "E-004", "git.diff.checkout",
            "Recent deployment changed checkout database pool size from 50 to 5.",
            supports=("H-001",),
        ),
    }
    evidence = evidence_by_tool.get(tool_name)
    if evidence is None:
        return ToolResult(tool_name, error=f"unknown tool: {tool_name}")
    return ToolResult(tool_name, evidence=evidence)
