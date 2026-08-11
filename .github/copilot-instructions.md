---
title: Copilot instructions for this repository
description: Repository-specific Agent Framework and MCP compatibility rules for GitHub Copilot
---

This repo targets the **2026 Microsoft Agent Framework**, which reorganised the
Python surface. Copilot's training data contains a great deal of the older API,
so without these notes it will confidently suggest imports that no longer exist.

## The API actually in use

```python
from agent_framework import Agent, Message, MCPStreamableHTTPTool, tool
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential
```

Use these substitutions:

- Import `FoundryChatClient` from `agent_framework.foundry`, not
  `AzureAIAgentClient` from `agent_framework.azure`.
- Construct `Agent(client=...)`; do not import the removed `ChatAgent`.
- Use `FoundryChatClient.get_mcp_tool(...)` for hosted MCP or
  `MCPStreamableHTTPTool` for local MCP; do not use `HostedMCPTool`.
- Import `HandoffBuilder` from `agent_framework.orchestrations`, not from
  `agent_framework`. This repository does not use that separate package.
- Call `agent.run(..., stream=True)`, not `agent.run_stream(...)`.
- Pass the deployment through `model=`, not `model_id=` or
  `deployment_name=`.
- Decorate function tools with `@tool`, not `@ai_function`.

## Patterns to follow

**Building an agent:**

```python
agent = Agent(
    client=FoundryChatClient(project_endpoint=..., model=..., credential=AzureCliCredential()),
    name="SomeAgent",
    instructions=INSTRUCTIONS,
    tools=[search_tool],
)
```

**Structured output**: `response_format` goes in `options`, and `response.value`
is the parsed model:

```python
response = await agent.run(prompt, options={"response_format": SystemRequirements})
artifact = response.value
```

**Function tools:**

```python
@tool(name="search_corpus", description="...")
def search_corpus(query: Annotated[str, "What to look for."]) -> str: ...
```

**Tool approval**: use `approval_mode="always_require"`, then handle
`response.user_input_requests` and reply with
`request.to_function_approval_response(bool)`.

**MCP tools** run local via `MCPStreamableHTTPTool(name=..., url=...)`, with
`allowed_tools` to split one server into differently-governed surfaces.

**MCP SDK compatibility** is intentionally pinned to 1.x. Agent Framework 1.13
uses the MCP 1.x `ClientSession` and transport APIs internally. Mock servers use
`mcp.server.fastmcp.FastMCP`; direct workshop calls use `ClientSession` with
`streamable_http_client`. Do not upgrade this repository to MCP 2 until Agent
Framework publishes support for it and both surfaces migrate together.

**Agents with MCP tools** must be used as async context managers:
`async with agent:`.

## Repository conventions

- Artifacts subclass `Artifact` (in `contracts/artifacts.py`) so they inherit
  canonical JSON and content hashing.
- **No artifact field is optional and none has a default.** Strict structured
  output requires every field present; use an empty list or empty string.
- Approvals are always bound to `artifact.content_hash()`. Never record an
  approval against only a stage name.
- Every handoff calls `registry.assert_approved(stage, artifact)` first.
- Retrieval is scoped per agent through `doc_types` on
  `build_corpus_search_tool`, never by asking the model to filter itself.
- MCP write tools use `approval_mode="always_require"`; read tools use
  `"never_require"`.

## Style

- Comments explain constraints and trade-offs, never what the next line does.
- Agent instructions constrain rather than encourage: say what the agent must not
  do, and prefer making something structurally impossible over asking for it.
- Errors name the fix. `"Missing FOUNDRY_PROJECT_ENDPOINT. Copy .env.example to
  .env"` beats `"config error"`.
- Tests are named as specifications, e.g.
  `test_editing_after_approval_invalidates_it`.

## Versions

`agent-framework-foundry` 1.10+, `agent-framework-core` 1.13+, `mcp` 1.29.x
(`FastMCP`, `ClientSession`, and `streamable_http_client`; **not** MCP 2's
`MCPServer` or `Client`),
`azure-search-documents` 11.6+, Pydantic 2, Python 3.11+.
