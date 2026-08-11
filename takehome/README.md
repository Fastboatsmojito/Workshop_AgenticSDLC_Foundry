# Track B — Finish the lifecycle

Self-paced, after the live session. The live track stopped at the backlog. This
track takes it to shipped code and a published release, then replaces every mock
with the real system.

## Before you start

Your Azure resources from the live session need to still exist, the mock servers
need to be running, and the live flow needs to work end to end:

```bash
python -m mcp_servers.run_all          # second terminal
python -m agentic_sdlc.cli check
python -m agentic_sdlc.cli run INIT-1042
```

## The exercises

| # | Exercise | Time | What you learn |
|---|---|---|---|
| 1 | [The Delivery Agent](01-delivery-agent.md) | 45 min | An agent that writes code, under per-write approval |
| 2 | [The Release Agent](02-release-agent.md) | 30 min | Closing the loop; verifying claims against the system of record |
| 3 | [Clarification and escalation](03-clarification-escalation.md) | 45 min | An agent that asks instead of guessing — **the most valuable one** |
| 4 | [Swap the mocks for real systems](04-swap-the-mocks.md) | 60 min | Three URLs, no agent code, real OAuth |
| 5 | [Evaluation in CI](05-evaluation.md) | 60 min | Scoring agent quality on every change |

Exercises 1 and 2 ship as working reference code, so they are mostly reading and
running. Exercises 3, 4, and 5 are genuine builds.

If you only do one, do **exercise 3**. Agents that guess confidently are the
main way these systems fail in production, and the escalation path is the fix.

## What is already written for you

`src/agentic_sdlc/agents/delivery_agent.py` and `release_agent.py` are complete
and tested. `NeedsClarification` exists in `contracts/artifacts.py` but nothing
returns it yet — exercise 3 is where you wire it up.

## Reference

- [Architecture spec](../docs/architecture-spec.md) — the design and its reasoning
- [Reference architecture](../infra/reference-architecture.md) — what changes for production
- [Troubleshooting](../workshop/troubleshooting.md)

When you finish, [delete the resource group](../workshop/cleanup.md). Azure AI
Search Basic bills whether you use it or not.
