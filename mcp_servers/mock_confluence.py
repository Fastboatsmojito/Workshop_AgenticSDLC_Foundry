"""Mock Confluence exposed over MCP.

Two jobs in this workshop:
  1. the audit sink the human gate writes every approval decision to, and
  2. where the Release Agent publishes the release package (take-home).

Stands in for the real Atlassian MCP server.

Run:  python -m mcp_servers.mock_confluence
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_servers.store import JsonStore

PORT = 8933
BASE_URL = "https://mock-confluence.local/wiki/SDLC"

# Business state lives in JsonStore, so transport sessions add teardown risk
# without adding useful behavior to the workshop mocks.
mcp = FastMCP(
    "mock-confluence",
    host="127.0.0.1",
    port=PORT,
    stateless_http=True,
    json_response=True,
)
store = JsonStore("confluence")


def _slug(title: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in title.lower()).strip("-")


def _now() -> str:
    return datetime.now(UTC).isoformat()


@mcp.tool()
def create_page(title: str, body: str, space: str = "SDLC") -> dict[str, Any]:
    """Create a page. Returns its id and URL."""
    with store.edit() as data:
        pages = data.setdefault("pages", {})
        page_id = _slug(title)
        pages[page_id] = {
            "id": page_id,
            "space": space,
            "title": title,
            "body": body,
            "created_at": _now(),
            "updated_at": _now(),
            "url": f"{BASE_URL}/{page_id}",
        }
        url = pages[page_id]["url"]
    return {"id": page_id, "url": url}


@mcp.tool()
def append_to_page(page_id: str, body: str, create_if_missing: bool = True) -> dict[str, Any]:
    """Append to a page, creating it when absent.

    The audit trail uses this so decisions accumulate on one page per initiative
    rather than overwriting each other.
    """
    with store.edit() as data:
        pages = data.setdefault("pages", {})
        page = pages.get(page_id)
        if page is None:
            if not create_if_missing:
                return {"error": f"page {page_id} not found"}
            page = {
                "id": page_id,
                "space": "SDLC",
                "title": page_id,
                "body": "",
                "created_at": _now(),
                "url": f"{BASE_URL}/{page_id}",
            }
            pages[page_id] = page
        page["body"] = (page["body"] + "\n" + body).strip()
        page["updated_at"] = _now()
        url = page["url"]
    return {"id": page_id, "url": url, "appended": True}


@mcp.tool()
def get_page(page_id: str) -> dict[str, Any]:
    """Read a page by id."""
    page = store.read().get("pages", {}).get(page_id)
    if page is None:
        return {"error": f"page {page_id} not found"}
    return page


@mcp.tool()
def list_pages(space: str = "") -> dict[str, Any]:
    """List pages, optionally filtered by space."""
    pages = list(store.read().get("pages", {}).values())
    if space:
        pages = [p for p in pages if p.get("space") == space]
    summary = [{"id": p["id"], "title": p["title"], "url": p["url"]} for p in pages]
    return {"count": len(summary), "pages": summary}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
