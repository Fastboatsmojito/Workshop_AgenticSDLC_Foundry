# Take-home 4 — Swap the mocks for the real systems (~60 min)

The payoff for using MCP throughout. Three URLs change. No agent code changes.

## Why this works

The agents never knew they were talking to mocks. They hold an
`MCPStreamableHTTPTool` pointed at a URL from `.env`:

```python
MCPStreamableHTTPTool(
    name="jira_write",
    url=settings.mcp.jira_url,          # <- the only thing that changes
    allowed_tools=["create_epic", "create_story", "create_test_case"],
    approval_mode="always_require",
)
```

Point it at the Atlassian MCP server and the same code writes to real Jira. This
is why we built mocks that speak the actual protocol instead of stubbing the
functions — a stub would have proven nothing about this step.

## What actually changes

| | Mock | Real |
|---|---|---|
| Transport | Streamable HTTP | Streamable HTTP |
| Auth | none | OAuth bearer token |
| Tool names | `create_story` | Whatever the vendor calls it |
| Arguments | Flat | Often nested, with required project fields |
| Failure | Returns `{"error": ...}` | HTTP errors, rate limits, permissions |

Transport is identical. Everything else needs attention, and the tool names are
the part that catches people out.

## Step 1 — Get a real MCP endpoint

Atlassian and GitHub both publish remote MCP servers; check their current
documentation for the endpoint and the OAuth flow, since both have moved during
2026. You will need a token with permission to create issues in a scratch
project. **Use a scratch project.** These agents create real issues.

## Step 2 — Add authentication

The mocks needed none. Real servers need a bearer token, supplied through
`header_provider`:

```python
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

jira_write = MCPStreamableHTTPTool(
    name="jira_write",
    url=settings.mcp.jira_url,
    allowed_tools=[...],
    approval_mode="always_require",
    header_provider=lambda _: {"Authorization": f"Bearer {get_jira_token()}"},
)
```

Fetch the token from Key Vault or a credential provider, not from `.env`. The
`.env` pattern was a workshop shortcut and this is the point where it stops being
acceptable.

## Step 3 — Reconcile the tool names

The real server will not call things what our mocks call them. Find out:

```python
import asyncio
from agentic_sdlc.mcp_client import list_tools

print(asyncio.run(list_tools("https://real-mcp-endpoint/mcp")))
```

Then update `allowed_tools` and the tool guidance in the agent's instructions to
match. **Keep the write/read split** — that separation is the governance
boundary, and it is easy to lose while you are busy fixing names.

If argument shapes differ significantly, use `MCPStreamableHTTPTool`'s
`parse_tool_results` or wrap the server behind your own adapter rather than
teaching the agent a second dialect.

## Step 4 — Run one write, and watch it

```bash
python -m agentic_sdlc.cli run INIT-1042
```

At the first Jira write, **read the arguments before approving**. This is the
moment the workshop was building toward: an agent proposing a real change to a
real system, and a human deciding.

Approve one. Then go and look at it in Jira.

## Step 5 — Break it on purpose

Real systems fail in ways mocks do not. Try each:

- **Revoke the token mid-run.** Does the agent report the failure honestly, or
  claim success?
- **Point at a project you cannot write to.** Does the permission error surface,
  or get swallowed into a plausible summary?
- **Trigger a rate limit** by running the breakdown for a large design. Does it
  back off, or hammer?

The answers determine how much autonomy this deserves in production. Find them
now, on a scratch project.

## Step 6 — Keep the mocks

Do not delete them. They are how you test without touching a real system:

```bash
python -m pytest -q                 # runs entirely against mocks
```

Keeping a mock MCP server per integration is a genuinely good pattern well
beyond this workshop. It is the only practical way to regression-test an agent
that writes to systems of record.

## Exercises

**A. Environment-switch by config.** `MCP_ENV=mock|real` selecting URL and auth
together, so nobody points production credentials at a test run by editing one
line.

**B. Record and replay.** Capture real MCP responses and replay them in tests, so
your fixtures match reality without needing the network.

**C. Contract tests.** Assert that the real server still exposes the tool names
and argument shapes you depend on. Run it nightly. You will find out about vendor
changes before your agents do.

---

Next: [05 — Evaluation in CI](05-evaluation.md)
