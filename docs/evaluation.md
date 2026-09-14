# Evaluation Plan

## Goal

Evaluation should answer:

Did this harness design make the agent better at reliable incident investigation?

This project should compare harness designs, not just prompts.

## Benchmark Unit

An evaluation case contains:

- Incident description.
- Simulated environment state.
- Available tools.
- Hidden ground truth.
- Expected evidence categories.
- Allowed remediation actions.

## First Benchmark Case

```text
INC-001: Checkout API latency increased 4x after deployment.
```

Expected root cause:

```text
Checkout deployment reduced the database connection pool size, causing connection saturation and request queueing.
```

Required evidence:

- Latency increased after deployment.
- Database connection pool saturation occurred during the incident.
- The recent deployment or Git diff changed the pool configuration.

Contradicting evidence:

- Database CPU is not saturated.
- Error rate is not the primary signal.

## Metrics

- Root-cause accuracy.
- Evidence correctness.
- Unsupported claim count.
- False hypothesis count.
- Time to resolution.
- Tool calls per investigation.
- Token and cost usage.
- Retry count.
- Recovery success after interruption.
- Remediation success.
- Investigation reliability.

## Harness Experiments

Compare:

- Scripted baseline vs model-driven loop.
- Basic loop vs LangGraph.
- No checkpointing vs checkpointing.
- No compaction vs compaction.
- Single agent vs subagents.
- Different tool-selection strategies.
- Different retry and timeout policies.
- Different termination criteria.

## Evaluation Rule

A final report is not correct just because it names the right service. It must connect symptom, mechanism, and evidence.

Minimum acceptable finding:

```text
The checkout latency regression was likely caused by the deployment that reduced the database connection pool from 50 to 5. Evidence: checkout p95 latency rose after deployment, DB connection usage reached the pool limit, and the Git diff shows the pool-size configuration change.
```

