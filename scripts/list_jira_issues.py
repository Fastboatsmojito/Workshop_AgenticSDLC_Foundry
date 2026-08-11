"""List the issues the Work Breakdown Agent created in (mock or real) Jira.

    python scripts/list_jira_issues.py INIT-1042

Guide 06 uses this to compare the Jira state against work_breakdown.json.
"""

from __future__ import annotations

import argparse
import asyncio

from agentic_sdlc.config import load_settings
from agentic_sdlc.mcp_client import call_tool


def main() -> int:
    parser = argparse.ArgumentParser(description="List Jira issues for one initiative over MCP.")
    parser.add_argument("initiative_id", help="e.g. INIT-1042")
    args = parser.parse_args()

    settings = load_settings()
    result = asyncio.run(call_tool(settings.mcp.jira_url, "list_issues", {"initiative_id": args.initiative_id}))
    issues = result.get("issues", [])
    if not issues:
        print(f"No issues recorded for {args.initiative_id}.")
        return 0
    for issue in issues:
        title = issue.get("title", issue.get("given_when_then", ""))
        print(f"{issue['key']:12} {issue.get('type', ''):6} {title[:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
