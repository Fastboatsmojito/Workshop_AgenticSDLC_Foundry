"""Shared plumbing for building and running the SDLC agents.

Every agent is `Agent(client=FoundryChatClient(...))` rather than a
service-managed `FoundryAgent`. That choice matters: this path owns instructions
and tools locally, which is what lets each agent carry a different retrieval
scope and return a different typed artifact. A `FoundryAgent` takes its
definition from the portal and ignores tools passed in code.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from agent_framework import Agent, AgentResponse, Message
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential
from pydantic import BaseModel

from agentic_sdlc.config import FoundrySettings

T = TypeVar("T", bound=BaseModel)

#: Called when a tool invocation needs sign-off. Returns True to allow it.
ApprovalCallback = Callable[[str, str], Awaitable[bool]]


def build_chat_client(settings: FoundrySettings, enable_tracing: bool = False) -> FoundryChatClient:
    """Foundry project client authenticated with your `az login` identity."""
    client = FoundryChatClient(
        project_endpoint=settings.project_endpoint,
        model=settings.model,
        credential=AzureCliCredential(),
    )
    if enable_tracing:
        from agentic_sdlc.observability import enable_tracing as _enable

        _enable(client)
    return client


def build_agent(
    client: FoundryChatClient,
    name: str,
    instructions: str,
    tools: list | None = None,
) -> Agent:
    return Agent(client=client, name=name, instructions=instructions, tools=tools or [])


async def run_structured(
    agent: Agent,
    prompt: str,
    response_format: type[T],
    on_approval_request: ApprovalCallback | None = None,
) -> tuple[T, AgentResponse]:
    """Run an agent and return its artifact, already parsed and validated.

    Handles tool-approval interrupts along the way: when a tool is marked
    `approval_mode="always_require"`, the run comes back asking for sign-off
    instead of a final answer, and we resume it with the decision. This is the
    framework's own human-in-the-loop primitive, distinct from the stage gate
    the orchestrator runs between agents.

    Raises ValueError when the model returns something the schema rejects,
    rather than passing an unvalidated object downstream.
    """
    options = {"response_format": response_format}
    response: AgentResponse = await agent.run(prompt, options=options)

    while getattr(response, "user_input_requests", None):
        followup: list = [prompt]
        for request in response.user_input_requests:
            call = getattr(request, "function_call", None)
            if call is None:
                continue
            approved = True
            if on_approval_request is not None:
                approved = await on_approval_request(call.name, str(call.arguments))
            followup.append(Message("assistant", [request]))
            followup.append(Message("user", [request.to_function_approval_response(approved)]))
        response = await agent.run(followup, options=options)

    artifact = response.value
    if artifact is None:
        raise ValueError(
            f"{agent.name} returned no parsable {response_format.__name__}. "
            f"Raw text was: {response.text[:400]!r}"
        )
    if not isinstance(artifact, response_format):
        raise ValueError(
            f"{agent.name} returned {type(artifact).__name__}, expected {response_format.__name__}."
        )
    return artifact, response
