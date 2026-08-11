"""Mock Jira exposed over MCP.

Stands in for the real Atlassian MCP server during the live session. The tool
names and shapes are deliberately close to the real thing so that swapping
`MCP_JIRA_URL` for the Atlassian endpoint is the only change needed.

Run:  python -m mcp_servers.mock_jira
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_servers.store import JsonStore

PORT = 8931
BASE_URL = "https://mock-jira.local/browse"

# Business state lives in JsonStore, so transport sessions add teardown risk
# without adding useful behavior to the workshop mocks.
mcp = FastMCP(
    "mock-jira",
    host="127.0.0.1",
    port=PORT,
    stateless_http=True,
    json_response=True,
)
store = JsonStore("jira")


def _issue_url(key: str) -> str:
    return f"{BASE_URL}/{key}"


@mcp.tool()
def create_epic(initiative_id: str, title: str, outcome: str) -> dict[str, Any]:
    """Create an epic. Returns the issue key and URL."""
    with store.edit() as data:
        key = store.next_id(data, "issues", "EPIC")
        data["issues"][key] = {
            "key": key,
            "type": "epic",
            "initiative_id": initiative_id,
            "title": title,
            "outcome": outcome,
            "status": "To Do",
        }
    return {"key": key, "url": _issue_url(key)}


@mcp.tool()
def create_story(
    initiative_id: str,
    epic_key: str,
    title: str,
    description: str,
    acceptance_criteria: list[str],
    estimate_points: int,
) -> dict[str, Any]:
    """Create a story under an epic. Returns the issue key and URL."""
    with store.edit() as data:
        key = store.next_id(data, "issues", "STORY")
        data["issues"][key] = {
            "key": key,
            "type": "story",
            "initiative_id": initiative_id,
            "epic_key": epic_key,
            "title": title,
            "description": description,
            "acceptance_criteria": acceptance_criteria,
            "estimate_points": estimate_points,
            "status": "To Do",
        }
    return {"key": key, "url": _issue_url(key)}


@mcp.tool()
def create_test_case(story_key: str, given_when_then: str, kind: str) -> dict[str, Any]:
    """Attach a test case to a story. `kind` is unit, integration, or e2e."""
    with store.edit() as data:
        key = store.next_id(data, "issues", "TEST")
        data["issues"][key] = {
            "key": key,
            "type": "test",
            "story_key": story_key,
            "given_when_then": given_when_then,
            "kind": kind,
            "status": "To Do",
        }
    return {"key": key, "url": _issue_url(key)}


@mcp.tool()
def get_issue(key: str) -> dict[str, Any]:
    """Read a single issue by key."""
    issue = store.read().get("issues", {}).get(key)
    if issue is None:
        return {"error": f"issue {key} not found"}
    return issue


@mcp.tool()
def list_issues(initiative_id: str = "") -> dict[str, Any]:
    """List issues, optionally filtered to one initiative."""
    issues = list(store.read().get("issues", {}).values())
    if initiative_id:
        issues = [i for i in issues if i.get("initiative_id") == initiative_id]
    return {"count": len(issues), "issues": issues}


@mcp.tool()
def transition_issue(key: str, status: str) -> dict[str, Any]:
    """Move an issue to a new status, e.g. In Progress or Done."""
    with store.edit() as data:
        issue = data.get("issues", {}).get(key)
        if issue is None:
            return {"error": f"issue {key} not found"}
        issue["status"] = status
    return {"key": key, "status": status}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
