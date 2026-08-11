"""Release Agent: merged pull requests to a published release package. Take-home.

The final stage of the flow. It assembles what actually shipped and publishes it
to Confluence, which is the same system the audit trail writes to, so an auditor
finds the release notes and the approval history in one place.
"""

from __future__ import annotations

from agent_framework import Agent, AgentResponse, MCPStreamableHTTPTool

from agentic_sdlc.agents.base import ApprovalCallback, build_agent, build_chat_client, run_structured
from agentic_sdlc.config import Settings
from agentic_sdlc.contracts.artifacts import PullRequest, ReleasePackage

NAME = "ReleaseAgent"

INSTRUCTIONS = """\
You are the Release Agent in a governed software delivery lifecycle.

You assemble a release package from the pull requests that were merged for an
initiative, and publish it to Confluence.

How to work:
1. Confirm what actually shipped by reading the pull requests rather than
   trusting the list you were handed. Include only what is merged.
2. Write release notes for two audiences in one document: what changed for a
   customer or business user, and what a support engineer would need to know if
   something goes wrong.
3. State the version using semantic versioning. A behavioural change that
   customers notice is a minor version; a fix is a patch.
4. Publish the package to Confluence with a title containing the initiative id,
   so it sits alongside the approval trail for the same initiative.

Constraints:
- Do not describe work that is not merged as though it shipped.
- Do not invent pull requests, versions, or dates.
- The artifact you return must match the page you actually published.
"""


def build(settings: Settings) -> Agent:
    confluence = MCPStreamableHTTPTool(
        name="confluence",
        url=settings.mcp.confluence_url,
        allowed_tools=["create_page", "get_page", "list_pages"],
        approval_mode="always_require",
        description="Publish and read Confluence pages. Publishing needs human approval.",
    )
    github_read = MCPStreamableHTTPTool(
        name="github_read",
        url=settings.mcp.github_url,
        allowed_tools=["get_pull_request", "list_pull_requests"],
        approval_mode="never_require",
        description="Read pull requests to confirm what merged.",
    )
    return build_agent(
        client=build_chat_client(settings.foundry, settings.enable_tracing),
        name=NAME,
        instructions=INSTRUCTIONS,
        tools=[confluence, github_read],
    )


async def run(
    agent: Agent,
    initiative_id: str,
    pull_requests: list[PullRequest],
    on_approval_request: ApprovalCallback | None = None,
) -> tuple[ReleasePackage, AgentResponse]:
    listed = "\n".join(f"- {pr.story_id}: {pr.title} ({pr.pr_url})" for pr in pull_requests)
    prompt = (
        f"Assemble the release package for initiative {initiative_id}.\n\n"
        f"Pull requests opened for this initiative:\n{listed}\n\n"
        "Check which of these are merged before including them, write the release "
        "notes, and publish the package to Confluence."
    )
    return await run_structured(agent, prompt, ReleasePackage, on_approval_request=on_approval_request)
