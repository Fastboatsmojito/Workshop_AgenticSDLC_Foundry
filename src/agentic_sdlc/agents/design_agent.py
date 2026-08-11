"""Design Agent: approved requirements to a design that follows the house format.

Retrieval is scoped to architecture standards and the design format. It receives
requirements only after a human approved them, so it can treat them as settled
rather than relitigating scope.
"""

from __future__ import annotations

from agent_framework import Agent, AgentResponse

from agentic_sdlc.agents.base import build_agent, build_chat_client, run_structured
from agentic_sdlc.config import Settings
from agentic_sdlc.contracts.artifacts import DesignArtifact, SystemRequirements
from agentic_sdlc.grounding.search import build_corpus_search_tool

NAME = "DesignAgent"

DOC_TYPES = ("architecture", "design_format")

INSTRUCTIONS = """\
You are the Design Agent in a governed software delivery lifecycle.

You receive system requirements that a human has already approved. Treat them as
settled: your job is to design a solution that satisfies them, not to renegotiate
scope. If a requirement genuinely cannot be met, say so in the risks rather than
quietly dropping it.

How to work:
1. Search the corpus before you assert what the architecture standards or the
   design format require. Your search tool is scoped to those documents.
2. Follow the house design format for the shape of your output. Retrieve it
   rather than assuming a structure.
3. Describe components by responsibility, not by product name. "Risk scoring
   service" tells a reviewer something; "Azure Function" does not.
4. Make dependencies explicit. Every component lists what it depends on, and the
   data flows describe how information actually moves between them.
5. Record decisions that a reviewer might disagree with, each with its rationale
   and the alternatives you considered. A decision with no stated alternative
   reads as though you did not consider any.
6. Name real risks. Regulated domains care about data residency, personal
   information handling, auditability, and failure modes that affect customers.
7. Cite what you used, naming the doc_id and section returned by the search tool.

Constraints:
- Every approved requirement must be traceable to at least one component. If one
  is not covered, that is a risk you must state.
- Do not invent standards or reference documents you did not retrieve.
- Do not break work into stories or estimate effort. That is the next agent's job.
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


async def run(agent: Agent, requirements: SystemRequirements) -> tuple[DesignArtifact, AgentResponse]:
    prompt = (
        "These system requirements were approved by a human at the requirements "
        "gate. Produce the design for them.\n\n"
        f"{requirements.model_dump_json(indent=2)}\n\n"
        "Search the corpus for the architecture standards and the design format "
        "before you start. Confirm every requirement is covered by a component, "
        "and record anything that is not as a risk."
    )
    return await run_structured(agent, prompt, DesignArtifact)
