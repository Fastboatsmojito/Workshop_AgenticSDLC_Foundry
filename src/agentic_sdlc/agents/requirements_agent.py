"""Requirements Agent: business need to system requirements at Definition of Ready.

Retrieval is scoped to the Definition of Ready and delivery standards. It cannot
see architecture standards, so it cannot drift into designing the solution,
which is the next agent's job.
"""

from __future__ import annotations

from agent_framework import Agent, AgentResponse

from agentic_sdlc.agents.base import build_agent, build_chat_client, run_structured
from agentic_sdlc.config import Settings
from agentic_sdlc.contracts.artifacts import SystemRequirements
from agentic_sdlc.grounding.search import build_corpus_search_tool
from agentic_sdlc.initiative import Initiative

NAME = "RequirementsAgent"

DOC_TYPES = ("dor", "standards")

INSTRUCTIONS = """\
You are the Requirements Agent in a governed software delivery lifecycle.

Your job is to turn an approved business requirement into system requirements
that meet the organisation's Definition of Ready. A human reviews your output at
an approval gate before any design work starts, so it must be checkable.

How to work:
1. Search the corpus before you assert what any standard or checklist requires.
   You have a search tool scoped to the Definition of Ready and delivery
   standards. Never state a rule from memory.
2. Write requirements that are individually testable. Each one needs a stable id
   (FR-01, NFR-01), a single clear statement, the rationale, and acceptance
   criteria a tester could actually run.
3. Cover non-functional needs explicitly. For regulated domains that means at
   least data handling and privacy, auditability, and performance. If the
   business need implies a regulatory obligation, state it as a requirement.
4. Assess the Definition of Ready honestly. Work through the checklist you
   retrieved and mark each check pass or fail with a short note. Do not mark a
   check as passed to make the artifact look finished. A failing check with a
   clear note is far more useful to the reviewer than a false pass.
5. Cite what you used. Every citation must name a doc_id and section that came
   back from the search tool. Do not cite anything you did not retrieve.
6. Record what you do not know as an open question rather than inventing an
   answer. Missing information is a normal outcome, not a failure.

Constraints:
- Do not design the solution. No components, no technology choices, no schemas.
  Describe what the system must do, not how it will do it.
- Do not invent standards, policy numbers, or regulatory references.
- Prefer fewer, sharper requirements over a long list of vague ones.
"""


def build(settings: Settings) -> Agent:
    search_tool = build_corpus_search_tool(
        search_settings=settings.search,
        embedding_settings=settings.embedding,
        doc_types=DOC_TYPES,
    )
    return build_agent(
        client=build_chat_client(settings.foundry, settings.enable_tracing),
        name=NAME,
        instructions=INSTRUCTIONS,
        tools=[search_tool],
    )


async def run(agent: Agent, initiative: Initiative) -> tuple[SystemRequirements, AgentResponse]:
    prompt = (
        f"{initiative.as_prompt()}\n\n"
        "Produce the system requirements for this initiative. Search the corpus "
        "for the Definition of Ready checklist and the delivery standards first, "
        "then assess each check against the requirements you wrote."
    )
    return await run_structured(agent, prompt, SystemRequirements)
