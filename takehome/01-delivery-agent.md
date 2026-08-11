# Take-home 1 — The Delivery Agent (~45 min)

An agent that takes one approved story and produces a pull request: a branch, the
code, the tests, and a description for a reviewer. It never merges.

## First, the confusion worth clearing up

This is **not** the GitHub Copilot in your editor. Copilot helps *you* write
Foundry code. The Delivery Agent is a Foundry agent that writes application code
on its own and submits it for review. In production this slot is where a GitHub
Copilot coding agent, or a similar autonomous coding agent, would sit.

Two Copilots, two jobs. This exercise is about the second one.

## Step 1 — Read it

`src/agentic_sdlc/agents/delivery_agent.py` is complete. Two things are worth
your attention.

**The write/read split.** Same pattern as the Work Breakdown Agent:
`create_branch`, `commit_files`, and `open_pull_request` require approval;
reading pull requests does not. `merge_pull_request` is not in either list, so
the agent **cannot merge even if it decides it should**. Capability it does not
have is stronger than an instruction it might ignore.

**The parallel-lists argument shape.** `commit_files` takes `paths` and
`contents` as two flat lists rather than a list of objects. MCP tool arguments
are most reliable when they stay flat, and models are noticeably better at
producing two parallel arrays than a nested structure. The mock validates the
lengths match and returns an error if they do not — worth reading in
`mcp_servers/mock_github.py`.

## Step 2 — Run it against one story

```python
# scratch.py
import asyncio

from agentic_sdlc.config import RUNS_DIR, load_settings
from agentic_sdlc.contracts.artifacts import WorkBreakdown
from agentic_sdlc.agents import delivery_agent
from agentic_sdlc.gate.audit import AuditTrail, ConfluenceSink, JsonlSink
from agentic_sdlc.contracts.approval import ApprovalRegistry
from agentic_sdlc.gate.console import ConsoleGate

async def main():
    settings = load_settings()
    breakdown = WorkBreakdown.model_validate_json(
        (RUNS_DIR / "INIT-1042" / "work_breakdown.json").read_text(encoding="utf-8")
    )
    story = breakdown.stories[0]
    print(f"Implementing {story.id}: {story.title}\n")

    registry = ApprovalRegistry(settings.audit_log_path)
    gate = ConsoleGate(
        audit=AuditTrail(JsonlSink(registry), [ConfluenceSink(settings.mcp.confluence_url)]),
        approver=settings.approver,
        model=settings.foundry.model,
    )

    agent = delivery_agent.build(settings)
    async with agent:
        pull_request, _ = await delivery_agent.run(
            agent, story, breakdown.initiative_id, on_approval_request=gate.approve_tool
        )

    outcome = await gate.review(breakdown.initiative_id, "delivery->release", pull_request)
    print(f"\napproved: {outcome.approved}  {pull_request.pr_url}")

asyncio.run(main())
```

```bash
python scratch.py
```

You will approve the branch, the commit, and the pull request individually, then
review the resulting `PullRequest` artifact at a stage gate. Both mechanisms, one
flow.

## Step 3 — Read the code it wrote

```python
import asyncio
from agentic_sdlc.config import load_settings
from agentic_sdlc.mcp_client import call_tool

settings = load_settings()
pull = asyncio.run(call_tool(settings.mcp.github_url, "get_pull_request", {"pull_number": 1}))
print(pull["body"])
```

The committed file contents live in `.runs/mock-state/github.json`. Read them and
judge as a reviewer:

- Does the code satisfy the acceptance criteria, or something adjacent to them?
- **Are there tests for the failure paths, or only the happy path?** This is where
  agent-written code is weakest and where a human reviewer earns their keep.
- Does the PR description say what a reviewer should look at closely, or does it
  just restate the diff?

## Step 4 — Say no and see what happens

Re-run and **reject the commit**. The instructions say not to retry with the same
arguments and to report what it could not do.

Does it comply? Does it try a variation? Does it claim success anyway?

Whatever it does, that behaviour is what you would be signing up for in
production. This is a cheap way to find out before it matters. If the agent
reports a pull request it did not open, your artifact and your system of record
have diverged — which is exactly the failure mode step 3 of the live guide 06
warned about.

## Exercises

**A. Add a review step.** Write a Review Agent that reads the pull request and
posts findings with `add_review_comment`, then gate on it. Should it be able to
approve its own merge? Argue both sides, then decide.

**B. Loop the whole breakdown.** Run the Delivery Agent over every story,
respecting `depends_on` ordering. What happens when a story's dependency was
rejected earlier?

**C. Give it the repository.** Add a read tool exposing the existing files on
`main`, so it writes code that fits what is already there. Notice how much the
output improves, and how much larger the context gets.

---

Next: [02 — The Release Agent](02-release-agent.md)
