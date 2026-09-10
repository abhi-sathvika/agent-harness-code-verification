# Code Review Agent Harness

                         Pull Request
                              │
                              ▼
                    ┌──────────────────┐
                    │ Review Orchestrator│
                    └─────────┬────────┘
                              │
                 ┌────────────┼────────────┐
                 ▼            ▼            ▼
          Repository      Dependency    PR / Git
          Explorer        Analyzer      Context
                 │            │            │
                 └────────────┼────────────┘
                              ▼
                       Agent Loop
                              │
                 ┌────────────┼────────────┐
                 ▼            ▼            ▼
              MCP Tools    Code Search   Knowledge
                                           Graph
                 │            │            │
                 └────────────┼────────────┘
                              ▼
                       Hypothesis
                              │
                              ▼
                       Code Execution
                              │
                       ┌──────┴──────┐
                       ▼             ▼
                     Tests       Static Analysis
                       │             │
                       └──────┬──────┘
                              ▼
                         Verification
                              │
                       ┌──────┴──────┐
                       │             │
                    Confirm       Reject
                       │             │
                       ▼             ▼
                  Review Finding   Continue
                       │
                       ▼
                  Human Reviewer


# Feature: Agent-to-Agent Review



