from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from incident_commander.domain import Incident, ToolResult
from incident_commander.tools import run_tool
from incident_commander.kubernetes import inspect_checkout_workload

ToolHandler = Callable[[Incident], ToolResult]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    server: str
    handler: ToolHandler


class MCPServer:
    """In-process stand-in for an MCP server's discover/invoke surface."""

    def __init__(self, name: str, tools: tuple[ToolSpec, ...]):
        self.name = name
        self._tools = {tool.name: tool for tool in tools}

    def list_tools(self) -> tuple[ToolSpec, ...]:
        return tuple(self._tools.values())

    def invoke(self, tool_name: str, incident: Incident) -> ToolResult:
        tool = self._tools.get(tool_name)
        if tool is None:
            return ToolResult(tool_name, error=f"tool not found on server {self.name}: {tool_name}")
        return tool.handler(incident)


class MCPGateway:
    """Routes requests without allowing the agent direct server access."""

    def __init__(self, servers: tuple[MCPServer, ...]):
        self._servers = {server.name: server for server in servers}

    def discover(self) -> tuple[ToolSpec, ...]:
        return tuple(tool for server in self._servers.values() for tool in server.list_tools())

    def invoke(self, qualified_name: str, incident: Incident) -> ToolResult:
        try:
            server_name, tool_name = qualified_name.split(".", 1)
        except ValueError:
            return ToolResult(qualified_name, error="tool name must use server.tool format")
        server = self._servers.get(server_name)
        if server is None:
            return ToolResult(qualified_name, error=f"MCP server not found: {server_name}")
        return server.invoke(tool_name, incident)


def build_local_gateway() -> MCPGateway:
    observability = MCPServer("observability", tuple(
        ToolSpec(name, f"Query simulated {name.replace('_', ' ')}", "observability", lambda incident, n=name: run_tool(n, incident))
        for name in ("query_checkout_latency", "query_database_connections", "query_database_cpu")
    ))
    git = MCPServer("git", (
        ToolSpec("inspect_checkout_diff", "Inspect the checkout deployment diff", "git", lambda incident: run_tool("inspect_checkout_diff", incident)),
    ))
    kubernetes = MCPServer("kubernetes", (
        ToolSpec("inspect_checkout_workload", "Inspect simulated checkout Kubernetes workload health", "kubernetes", inspect_checkout_workload),
    ))
    return MCPGateway((observability, git, kubernetes))
