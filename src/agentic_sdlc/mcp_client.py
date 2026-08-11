"""Thin MCP client used outside the agent loop.

Agents reach MCP servers through `MCPStreamableHTTPTool`. The audit trail and
the verification scripts need to call the same servers directly, without a
model in the middle, which is what this is for.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


@asynccontextmanager
async def _session(url: str) -> AsyncIterator[ClientSession]:
    """Open and initialize one MCP 1.x Streamable HTTP session."""
    async with streamable_http_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


def _unwrap(result: Any) -> Any:
    """Pull a usable Python value out of a CallToolResult.

    Prefers the structured payload when the server provides one and falls back
    to decoding the text block, since tools may return either.
    """
    structured = getattr(result, "structured_content", None) or getattr(result, "structuredContent", None)
    if structured:
        # Servers wrap scalar returns in {"result": ...}; unwrap that one case.
        if isinstance(structured, dict) and set(structured) == {"result"}:
            return structured["result"]
        return structured

    payloads: list[Any] = []
    for content in getattr(result, "content", []) or []:
        text = getattr(content, "text", None)
        if text is None:
            continue
        try:
            payloads.append(json.loads(text))
        except json.JSONDecodeError:
            payloads.append(text)

    if not payloads:
        return None
    return payloads[0] if len(payloads) == 1 else payloads


async def call_tool(url: str, name: str, arguments: dict[str, Any]) -> Any:
    """Call one MCP tool on a server and return its parsed result."""
    async with _session(url) as session:
        result = await session.call_tool(name, arguments)
    return _unwrap(result)


async def list_tools(url: str) -> list[str]:
    """Names of every tool a server exposes. Used by the environment check."""
    async with _session(url) as session:
        result = await session.list_tools()
    return [tool.name for tool in result.tools]
