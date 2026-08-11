"""Mock GitHub exposed over MCP.

Stands in for the real GitHub MCP server. Used by the Delivery Agent in the
take-home track to branch, commit, and open a pull request.

Run:  python -m mcp_servers.mock_github
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_servers.store import JsonStore

PORT = 8932
REPO = "contoso/policy-admin"

# Business state lives in JsonStore, so transport sessions add teardown risk
# without adding useful behavior to the workshop mocks.
mcp = FastMCP(
    "mock-github",
    host="127.0.0.1",
    port=PORT,
    stateless_http=True,
    json_response=True,
)
store = JsonStore("github")


@mcp.tool()
def create_branch(branch: str, from_ref: str = "main") -> dict[str, Any]:
    """Create a branch off `from_ref`."""
    with store.edit() as data:
        branches = data.setdefault("branches", {})
        if branch in branches:
            return {"branch": branch, "created": False, "note": "branch already exists"}
        branches[branch] = {"name": branch, "from_ref": from_ref, "files": {}}
    return {"branch": branch, "created": True}


@mcp.tool()
def commit_files(branch: str, message: str, paths: list[str], contents: list[str]) -> dict[str, Any]:
    """Commit files to a branch.

    `paths` and `contents` are parallel lists; entry i of one matches entry i of
    the other. Kept as two flat lists because MCP tool arguments stay simplest
    when they avoid nested objects.
    """
    if len(paths) != len(contents):
        return {"error": f"paths ({len(paths)}) and contents ({len(contents)}) must be the same length"}

    with store.edit() as data:
        branch_record = data.setdefault("branches", {}).get(branch)
        if branch_record is None:
            return {"error": f"branch {branch} not found; call create_branch first"}
        for path, body in zip(paths, contents, strict=True):
            branch_record["files"][path] = body
        commits = data.setdefault("commits", [])
        sha = f"{len(commits) + 1:07d}"
        commits.append({"sha": sha, "branch": branch, "message": message, "paths": paths})
    return {"sha": sha, "branch": branch, "files_committed": len(paths)}


@mcp.tool()
def open_pull_request(branch: str, title: str, body: str, base: str = "main") -> dict[str, Any]:
    """Open a pull request from `branch` into `base`."""
    with store.edit() as data:
        pulls = data.setdefault("pulls", {})
        number = len(pulls) + 1
        key = str(number)
        pulls[key] = {
            "number": number,
            "branch": branch,
            "base": base,
            "title": title,
            "body": body,
            "state": "open",
            "review_comments": [],
            "url": f"https://mock-github.local/{REPO}/pull/{number}",
        }
        url = pulls[key]["url"]
    return {"number": number, "url": url, "state": "open"}


@mcp.tool()
def add_review_comment(pull_number: int, reviewer: str, comment: str) -> dict[str, Any]:
    """Add a review comment to a pull request."""
    with store.edit() as data:
        pull = data.get("pulls", {}).get(str(pull_number))
        if pull is None:
            return {"error": f"pull request {pull_number} not found"}
        pull["review_comments"].append({"reviewer": reviewer, "comment": comment})
        count = len(pull["review_comments"])
    return {"number": pull_number, "review_comments": count}


@mcp.tool()
def get_pull_request(pull_number: int) -> dict[str, Any]:
    """Read a pull request, including its review comments."""
    pull = store.read().get("pulls", {}).get(str(pull_number))
    if pull is None:
        return {"error": f"pull request {pull_number} not found"}
    return pull


@mcp.tool()
def list_pull_requests(state: str = "") -> dict[str, Any]:
    """List pull requests, optionally filtered by state (open, merged)."""
    pulls = list(store.read().get("pulls", {}).values())
    if state:
        pulls = [p for p in pulls if p.get("state") == state]
    return {"count": len(pulls), "pull_requests": pulls}


@mcp.tool()
def merge_pull_request(pull_number: int) -> dict[str, Any]:
    """Merge a pull request. The workshop flow only reaches this after approval."""
    with store.edit() as data:
        pull = data.get("pulls", {}).get(str(pull_number))
        if pull is None:
            return {"error": f"pull request {pull_number} not found"}
        pull["state"] = "merged"
        url = pull["url"]
    return {"number": pull_number, "state": "merged", "url": url}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
