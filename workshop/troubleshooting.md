# Troubleshooting

Ordered roughly by how often each one bites.

## Setup and auth

**`Missing required environment variable 'FOUNDRY_PROJECT_ENDPOINT'`**
You have no `.env`, or it is not in the repo root. `cp .env.example .env` and
fill it in. Values must not be wrapped in quotes.

**`DefaultAzureCredential`/`AzureCliCredential` failed to retrieve a token**
Your CLI session expired or you are on the wrong tenant.

**bash**

```bash
az login
az account set --subscription "<name or id>"
az account get-access-token --resource https://ai.azure.com >/dev/null && echo OK
```

**PowerShell**

```powershell
az login
az account set --subscription "<name or id>"
az account get-access-token --resource https://ai.azure.com --output none; if ($?) { "OK" }
```

**`PermissionDenied` or 401 from the Foundry project**
The **Foundry User** assignment from guide 01 step 3 is missing or has not
propagated. Wait two minutes and retry; role assignments are not instant.
Confirm with:

**bash**

```bash
az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv) \
  --resource-group $RG -o table
```

**PowerShell**

```powershell
az role assignment list --assignee (az ad signed-in-user show --query id -o tsv) `
  --resource-group $RG -o table
```

**`DeploymentNotFound`**
`FOUNDRY_MODEL` must match the **deployment** name, not the model name. They are
often the same, which makes the mismatch easy to miss.

```bash
az cognitiveservices account deployment list --name "aif-agentic-sdlc-$ALIAS" --resource-group $RG --query "[].name" -o table
```

## Azure AI Search

**`index` fails: service not found or still provisioning**
Check `status` is `running`:

```bash
az search service show --name "srch-agentic-sdlc-$ALIAS" --resource-group $RG --query status -o tsv
```

**`Unauthorized` from Search**
`SEARCH_API_KEY` must be the **admin** key, not a query key. Query keys cannot
create indexes.

**Search returns nothing at all**
The index exists but is empty, usually because ingestion failed partway:

```bash
python -m agentic_sdlc.cli index --recreate
```

**`The vector field dimensions do not match`**
`EMBEDDING_DIMENSIONS` disagrees with your embedding deployment. Set it to 1536
for `text-embedding-3-small`, 3072 for `text-embedding-3-large`, then
`--recreate` the index. Changing dimensions always requires a rebuild.

## Mock MCP servers

**`check` shows red rows, or `httpx.ConnectError: All connection attempts failed`**
The mock servers are not running. In a second terminal, with the virtual
environment activated:

```bash
python -m mcp_servers.run_all
```

**`[Errno 10048]` (Windows) or `[Errno 98]` (Linux) address already in use**
An old server is still holding the port. Find and stop it:

```bash
# Windows
netstat -ano | findstr "8931 8932 8933"
taskkill /PID <pid> /F

# macOS / Linux
lsof -ti:8931,8932,8933 | xargs kill
```

**Jira has issues from an earlier run**
The mocks are stateful by design. Reset them:

```bash
rm -rf .runs/mock-state        # PowerShell: Remove-Item -Recurse -Force .runs\mock-state
```

## Agents and artifacts

**`ValidationError` after an agent runs**
The model returned something the schema rejects. Usually a field it was never
told about, or a `Literal` it guessed a value for. Read the error — it names the
field. Then either loosen the schema or say more about that field in the
instructions.

**`RequirementsAgent returned no parsable SystemRequirements`**
The model produced prose instead of structured output, most often because it ran
out of tokens mid-object. Check your deployment capacity, or use a larger model.

**The agent invents standards instead of searching**
Confirm the search tool is actually attached and returning results (guide 03,
step 3). If retrieval returns nothing, the model falls back on training data — a
scoped miss looks like confident invention unless you check.

**Every Definition of Ready check passes, on every initiative**
Your instructions lost the honesty clause, or the model is being agreeable. Try
`INIT-1077`: an all-green result on that one is a bug in your prompt.

**`rate limit exceeded` / HTTP 429**
Too little capacity on the deployment. Raise `--sku-capacity`, or wait and retry.
Several people sharing one deployment will hit this.

## Gate and audit

**`No approval recorded for stage ...`**
The gate has not run for this artifact yet. Run the flow rather than calling
`verify` on a fresh checkout.

**`Approval ... does not cover the current artifact`**
Working as designed — the artifact changed after it was approved. If you ran
`tamper`, this is the point. If you did not, something modified the file: re-run
the flow and approve the current content.

**Confluence sink logs a warning but the run continues**
Intentional. The JSONL trail is authoritative; secondary sinks are best-effort so
a stopped mock server degrades the trail instead of halting the workshop.

**Nothing in `.runs/audit.jsonl`**
`AUDIT_LOG_PATH` is pointing somewhere else, or you are running from a different
working directory. All paths are relative to the repo root.

## Tests

**MCP tests skip with "did not start on port"**
Port conflict or a slow machine. Free the ports as above and re-run.

**Tests pass but the flow fails**
Expected, and worth understanding: the tests deliberately cover everything that
does not need Azure. A green suite plus a failing run means the problem is
configuration, not code.

---

Still stuck? Compare against `solutions/` for known-good configuration and
expected output.
