"""Work Breakdown Agent: approved design to epics, stories, and test cases.

This is the first agent that writes to a system of record, so it is where the
second flavour of human-in-the-loop shows up. The stage gate approves an
artifact between agents; here the framework's own tool approval sits in front of
each individual Jira write. Reads are unrestricted, writes are not.
"""

from __future__ import annotations

from agent_framework import Agent, AgentResponse, MCPStreamableHTTPTool

from agentic_sdlc.agents.base import ApprovalCallback, build_agent, build_chat_client, run_structured
from agentic_sdlc.config import Settings
from agentic_sdlc.contracts.artifacts import DesignArtifact, WorkBreakdown

NAME = "WorkBreakdownAgent"

WRITE_TOOLS = ("create_epic", "create_story", "create_test_case")
READ_TOOLS = ("list_issues", "get_issue")

INSTRUCTIONS = """\
You are the Work Breakdown Agent in a governed software delivery lifecycle.

You receive a design that a human has already approved, and you turn it into a
work breakdown: epics, stories, dependencies, and test cases. You also write
those items into Jira using the tools provided.

How to work:
1. Derive the breakdown from the design. Every component and data flow in the
   design should be traceable to at least one story. Do not invent scope that
   the design does not call for.
2. Write vertically sliced stories that deliver observable value, not layer-by
   -layer tasks. "Score a claim for risk" is a story; "add a database table" is
   not.
3. Give every story acceptance criteria a tester could run, and an estimate in
   points. Estimate relative complexity, not hours.
4. Make sequencing explicit through `depends_on`. If two stories can proceed in
   parallel, leave the dependencies empty rather than inventing an order.
5. Write at least one test case per story, and cover the risky paths rather than
   only the happy one. Use given/when/then phrasing.
6. Create the epics first, then the stories under them, then the test cases.
   You need the epic key before you can create a story under it.

About the Jira tools:
- Each write is submitted to a human for approval before it executes. This is
  expected. Make one call per item and keep the arguments readable, because a
  person is reading them before saying yes.
- If a write is rejected, do not retry it with the same arguments. Leave that
  item out of your final artifact and note the gap in the sequencing notes.

Constraints:
- Do not redesign the solution or add components.
- The artifact you return must match what you actually created in Jira.
"""


def build(settings: Settings) -> Agent:
    jira_write = MCPStreamableHTTPTool(
        name="jira_write",
        url=settings.mcp.jira_url,
        allowed_tools=list(WRITE_TOOLS),
        approval_mode="always_require",
        description="Create epics, stories, and test cases in Jira. Every call needs human approval.",
    )
    jira_read = MCPStreamableHTTPTool(
        name="jira_read",
        url=settings.mcp.jira_url,
        allowed_tools=list(READ_TOOLS),
        approval_mode="never_require",
        description="Read existing Jira issues.",
    )
    return build_agent(
        client=build_chat_client(settings.foundry, settings.enable_tracing),
        name=NAME,
        instructions=INSTRUCTIONS,
        tools=[jira_write, jira_read],
    )


async def run(
    agent: Agent,
    design: DesignArtifact,
    on_approval_request: ApprovalCallback | None = None,
) -> tuple[WorkBreakdown, AgentResponse]:
    prompt = (
        "This design was approved by a human at the design gate. Break it down "
        "into epics, stories, and test cases, and create them in Jira.\n\n"
        f"{design.model_dump_json(indent=2)}\n\n"
        "Create the epics first so you have their keys, then the stories, then "
        "the test cases. Return the breakdown you actually created."
    )
    return await run_structured(agent, prompt, WorkBreakdown, on_approval_request=on_approval_request)
