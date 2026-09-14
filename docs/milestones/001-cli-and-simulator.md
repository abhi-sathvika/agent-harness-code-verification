# Milestone 1: CLI and Deterministic Simulator

## Problem

Before adding LangGraph or an LLM, the project needs a visible product loop and a concrete incident domain. A deterministic simulator gives us known-good investigation artifacts: events, hypotheses, evidence, and final reports.

This matters because long-running agent harnesses are easier to reason about when the state model is clear before probabilistic model behavior enters the system.

## Architecture

```text
CLI
  -> Scenario Registry
  -> Scripted Investigation
  -> Structured Events
  -> Final Report
```

The scripted investigation is intentionally not intelligent. It is a reference path that shows what the harness should eventually make possible with real model reasoning and MCP tools.

## Implemented Commands

```bash
incident-commander incidents list
incident-commander incidents show INC-001
incident-commander investigate INC-001 --mode scripted
```

## Concepts

- Incident state is separate from investigation run behavior.
- Evidence is explicit and addressable by ID.
- Hypotheses are tracked separately from final conclusions.
- Final reports must cite evidence IDs.
- Tool calls are represented as events before real MCP servers exist.

## Learning Exercise

Manually trace the scripted run:

1. Which event first establishes the user-visible symptom?
2. Which evidence supports the database connection pool hypothesis?
3. Which evidence weakens the CPU saturation hypothesis?
4. Why is the Git diff not sufficient by itself to prove the root cause?
5. What state would need to persist if this run crashed after `E-002`?

