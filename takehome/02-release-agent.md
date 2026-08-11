# Take-home 2 — The Release Agent (~30 min)

The last stage. Merged pull requests become a release package published to
Confluence — the same system the audit trail writes to, so an auditor finds the
release notes and the approval history for an initiative in one place.

## Step 1 — Merge something first

The Delivery Agent cannot merge, by design. A human does:

```python
import asyncio
from agentic_sdlc.config import load_settings
from agentic_sdlc.mcp_client import call_tool

settings = load_settings()
print(asyncio.run(call_tool(settings.mcp.github_url, "merge_pull_request", {"pull_number": 1})))
```

## Step 2 — The instruction that matters

From `src/agentic_sdlc/agents/release_agent.py`:

> *"Confirm what actually shipped by reading the pull requests rather than
> trusting the list you were handed. Include only what is merged."*

The agent is handed a list of pull requests and told not to believe it. That is
the shape of the lesson: **an agent's claim about the world is a claim until it
is checked against the system of record.** The same principle applies to the
Work Breakdown Agent's report of what it created in Jira.

## Step 3 — Run it

```python
# scratch_release.py
import asyncio

from agentic_sdlc.config import load_settings
from agentic_sdlc.contracts.approval import ApprovalRegistry
from agentic_sdlc.contracts.artifacts import PullRequest
from agentic_sdlc.agents import release_agent
from agentic_sdlc.gate.audit import AuditTrail, ConfluenceSink, JsonlSink
from agentic_sdlc.gate.console import ConsoleGate

async def main():
    settings = load_settings()
    pull_requests = [
        PullRequest(
            initiative_id="INIT-1042", story_id="STORY-001",
            branch="feature/story-001", title="Add eligibility assessment",
            description="", files_changed=[], tests_added=[],
            pr_url="https://mock-github.local/contoso/policy-admin/pull/1",
        )
    ]

    registry = ApprovalRegistry(settings.audit_log_path)
    gate = ConsoleGate(
        audit=AuditTrail(JsonlSink(registry), [ConfluenceSink(settings.mcp.confluence_url)]),
        approver=settings.approver, model=settings.foundry.model,
    )

    agent = release_agent.build(settings)
    async with agent:
        package, _ = await release_agent.run(
            agent, "INIT-1042", pull_requests, on_approval_request=gate.approve_tool
        )

    outcome = await gate.review("INIT-1042", "release->done", package)
    print(f"\napproved: {outcome.approved}  {package.confluence_url}")

asyncio.run(main())
```

## Step 4 — See both records side by side

```python
import asyncio
from agentic_sdlc.config import load_settings
from agentic_sdlc.mcp_client import call_tool

settings = load_settings()
print(asyncio.run(call_tool(settings.mcp.confluence_url, "list_pages", {})))
```

You should see the release page and `audit-init-1042` in the same space. An
auditor asking "what shipped and who approved it" has one place to look, which is
a small thing that matters a lot in a regulated organisation.

## Step 5 — Try to make it lie

Hand it a pull request that was never merged, or one that does not exist. A good
run excludes it. A bad run writes confident release notes about work that never
shipped — which is worse than no release notes, because someone will trust it.

If it includes unmerged work, tighten the instruction and try again. This is the
tuning loop you will spend most of your time in on a real system.

## Exercises

**A. Derive the version.** Have it read merged PR titles and pick major, minor,
or patch by conventional-commit prefix, rather than deciding by feel.

**B. Trace back to requirements.** Include, for each shipped story, the
requirement id it satisfies and the `audit_id` that approved it. You now have
requirement-to-release traceability, which is usually the thing an auditor
actually asks for.

**C. Gate on the notes, not the package.** Right now the gate reviews the
artifact after publishing. Restructure so the human approves the release notes
*before* the page is created. Which order is right, and why?

---

Next: [03 — Clarification and escalation](03-clarification-escalation.md)
