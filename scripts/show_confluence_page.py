"""Read one page from the (mock or real) Confluence MCP server.

    python scripts/show_confluence_page.py audit-init-1042

Guide 05 uses this to show the audit page the gate wrote through MCP.
"""

from __future__ import annotations

import argparse
import asyncio

from agentic_sdlc.config import load_settings
from agentic_sdlc.mcp_client import call_tool


def main() -> int:
    parser = argparse.ArgumentParser(description="Print one Confluence page fetched over MCP.")
    parser.add_argument("page_id", help="Page id, e.g. audit-init-1042")
    args = parser.parse_args()

    settings = load_settings()
    page = asyncio.run(call_tool(settings.mcp.confluence_url, "get_page", {"page_id": args.page_id}))
    if "error" in page:
        print(page["error"])
        return 1
    print(page["body"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
