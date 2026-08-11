"""Delivery Agent: one approved story to a pull request. Take-home track.

This is the agent that writes code, which makes it the one most often confused
with the GitHub Copilot sitting in your editor. They are different things:
Copilot helps *you* build these agents; this agent is a Foundry agent that
produces a change set on its own and submits it for review. In production this
is the slot where the GitHub Copilot coding agent would sit.

Every write to the repository is gated by the framework's tool approval, so the
agent proposes and a human allows.
"""

from __future__ import annotations

from agent_framework import Agent, AgentResponse, MCPStreamableHTTPTool

from agentic_sdlc.agents.base import ApprovalCallback, build_agent, build_chat_client, run_structured
from agentic_sdlc.config import Settings
from agentic_sdlc.contracts.artifacts import PullRequest, Story

NAME = "DeliveryAgent"

WRITE_TOOLS = ("create_branch", "commit_files", "open_pull_request")
READ_TOOLS = ("get_pull_request", "list_pull_requests")

INSTRUCTIONS = """\
You are the Delivery Agent in a governed software delivery lifecycle.

You receive one story that a human approved as part of a work breakdown, and you
implement it: a branch, the code, the tests, and a pull request opened for
review. You never merge. A human reviews and merges.

How to work:
1. Create a branch named for the story, using the pattern
   feature/<story-id-lowercased>-<short-slug>.
2. Write the smallest change that satisfies the story's acceptance criteria.
   Resist adding capability the story did not ask for.
3. Write tests before you claim the story is done. Cover each acceptance
   criterion, and cover the failure paths, not only the happy path. A change set
   with no test for the exception path is incomplete.
4. Commit the code and the tests together. Use one commit with a message that
   explains why the change exists, not what lines moved.
5. Open a pull request whose description states what changed, which acceptance
   criteria it satisfies, and what a reviewer should look at closely.

About the repository tools:
- Each write is submitted to a human before it executes. Keep the arguments
  readable, because a person is reading them before saying yes.
- `commit_files` takes `paths` and `contents` as two parallel lists. Entry i of
  one corresponds to entry i of the other, so they must be the same length.
- If a write is rejected, stop and report what you were unable to do rather than
  retrying with the same arguments.

Constraints:
- Do not merge the pull request.
- Do not modify files unrelated to the story.
- The artifact you return must describe the pull request you actually opened.
"""


def build(settings: Settings) -> Agent:
    github_write = MCPStreamableHTTPTool(
        name="github_write",
        url=settings.mcp.github_url,
        allowed_tools=list(WRITE_TOOLS),
        approval_mode="always_require",
        description="Branch, commit, and open pull requests. Every call needs human approval.",
    )
    github_read = MCPStreamableHTTPTool(
        name="github_read",
        url=settings.mcp.github_url,
        allowed_tools=list(READ_TOOLS),
        approval_mode="never_require",
        description="Read existing pull requests.",
    )
    return build_agent(
        client=build_chat_client(settings.foundry, settings.enable_tracing),
        name=NAME,
        instructions=INSTRUCTIONS,
        tools=[github_write, github_read],
    )


async def run(
    agent: Agent,
    story: Story,
    initiative_id: str,
    on_approval_request: ApprovalCallback | None = None,
) -> tuple[PullRequest, AgentResponse]:
    prompt = (
        f"Implement this story for initiative {initiative_id}. It was approved as "
        "part of the work breakdown.\n\n"
        f"{story.model_dump_json(indent=2)}\n\n"
        "Create the branch, write the code and the tests, commit them together, "
        "and open a pull request. Do not merge it."
    )
    return await run_structured(agent, prompt, PullRequest, on_approval_request=on_approval_request)
