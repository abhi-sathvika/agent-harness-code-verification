# Milestone 4: MCP Tool Boundary

The LangGraph path now requests qualified capabilities through a gateway such as `observability.query_database_connections` or `git.inspect_checkout_diff`. The local gateway models discovery, server ownership, qualified names, and invocation errors.

This is not yet networked MCP. The protocol and transport come after we understand the boundary they must preserve.

## Learning checkpoint

Explain why the gateway is a security and reliability boundary, not just a wrapper. Which layer should enforce authorization, timeouts, and audit events before a real MCP server is called?
