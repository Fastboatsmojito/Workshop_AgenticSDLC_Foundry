# Cleanup

Everything lives in one resource group, so this is one command. Do it when you
have finished the take-home, not at the end of the live session.

## Delete the Azure resources

If this is a new terminal, `$ALIAS` from guide 01 is gone — set it again first
(bash: `export ALIAS="yourname"`, PowerShell: `$ALIAS = "yourname"`) or just
type the resource group name out. The command itself is identical in both
shells:

```bash
az group delete --name "rg-agentic-sdlc-$ALIAS" --yes --no-wait
```

That removes the Foundry resource, both model deployments, and the Azure AI
Search service. Deletion runs in the background and takes a few minutes.

Confirm it is gone:

```bash
az group exists --name "rg-agentic-sdlc-$ALIAS"
```

## What costs money if you forget

**Azure AI Search Basic — roughly seventy-five dollars a month.** This is the one
that matters. It bills for existing, whether or not you query it.

Model deployments bill per token, so an idle deployment costs nothing. The
Foundry resource itself is free. Deleting the resource group handles all of it
regardless.

## Local cleanup

Nothing here costs anything, but if you want a clean slate:

```bash
# Run artifacts, audit trail, and mock system state
rm -rf .runs                    # PowerShell: Remove-Item -Recurse -Force .runs

# Virtual environment
rm -rf .venv                    # PowerShell: Remove-Item -Recurse -Force .venv
```

`.runs/` holds your audit trail and the artifacts from every run. Keep it if you
want to look back at what your agents produced — it is the most interesting
output of the day and it is gitignored, so it stays local.

## Stop the mock servers

Ctrl+C in the terminal running `python -m mcp_servers.run_all`. If a port stays
held, see [troubleshooting](troubleshooting.md#mock-mcp-servers).

## Keeping it for later

The repository works without any Azure resources for everything except the
agents themselves:

```bash
python -m pytest -q
```

The contracts, the gate, the audit trail, the corpus chunking, and the mock MCP
servers all run offline. If you want to keep experimenting with the governance
model without paying for Search, that is the part to keep.
