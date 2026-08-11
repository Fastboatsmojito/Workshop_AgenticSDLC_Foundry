# 02 — Deploy your models and configure (12–20 min)

Search is still provisioning. Use this time for the two model deployments, your
`.env`, and the mock servers.

## Step 1 — Deploy a chat model and an embedding model

**bash**

```bash
az cognitiveservices account deployment create \
  --name "aif-agentic-sdlc-$ALIAS" --resource-group $RG \
  --deployment-name gpt-4o-mini \
  --model-name gpt-4o-mini --model-version "2024-07-18" --model-format OpenAI \
  --sku-capacity 30 --sku-name GlobalStandard

az cognitiveservices account deployment create \
  --name "aif-agentic-sdlc-$ALIAS" --resource-group $RG \
  --deployment-name text-embedding-3-small \
  --model-name text-embedding-3-small --model-version "1" --model-format OpenAI \
  --sku-capacity 30 --sku-name Standard
```

**PowerShell**

```powershell
az cognitiveservices account deployment create `
  --name "aif-agentic-sdlc-$ALIAS" --resource-group $RG `
  --deployment-name gpt-4o-mini `
  --model-name gpt-4o-mini --model-version "2024-07-18" --model-format OpenAI `
  --sku-capacity 30 --sku-name GlobalStandard

az cognitiveservices account deployment create `
  --name "aif-agentic-sdlc-$ALIAS" --resource-group $RG `
  --deployment-name text-embedding-3-small `
  --model-name text-embedding-3-small --model-version "1" --model-format OpenAI `
  --sku-capacity 30 --sku-name Standard
```

If the model or version is unavailable in your region — model retirements move
faster than workshop material — list what you can deploy:

```bash
az cognitiveservices account list-models --name "aif-agentic-sdlc-$ALIAS" --resource-group $RG --query "[].{model:name, version:version}" -o table
```

Any generally available chat model that supports structured outputs and tool
calling works; `gpt-4.1-mini` is a good substitute when `gpt-4o-mini` is not
offered. Whatever you deploy, put the **deployment name** in `FOUNDRY_MODEL`.
If you change the embedding model, update `EMBEDDING_DIMENSIONS` in `.env` to
match — `text-embedding-3-small` is 1536.

> **Capacity note:** 30K tokens per minute is comfortable for one person. The
> Requirements Agent sends the retrieved corpus plus the initiative, so a run is
> a few thousand tokens.

## Step 2 — Get the Search key and endpoint

By now Search should be running. Single-line commands, identical in both shells:

```bash
az search service show --name "srch-agentic-sdlc-$ALIAS" --resource-group $RG --query status -o tsv

az search admin-key show --service-name "srch-agentic-sdlc-$ALIAS" --resource-group $RG --query primaryKey -o tsv
```

## Step 3 — Write your `.env`

`cp` works in both shells (PowerShell aliases it to `Copy-Item`):

```bash
cp .env.example .env
```

Fill in five values:

| Variable | Where it comes from |
|---|---|
| `FOUNDRY_PROJECT_ENDPOINT` | Foundry project Overview page, guide 01 |
| `FOUNDRY_OPENAI_ENDPOINT` | `https://aif-agentic-sdlc-<alias>.openai.azure.com` |
| `SEARCH_ENDPOINT` | `https://srch-agentic-sdlc-<alias>.search.windows.net` |
| `SEARCH_API_KEY` | The admin key you just printed |
| `APPROVER_ALIAS` | Your name — it goes into every approval record |

> Two endpoints on one resource is not a mistake. The **project** endpoint
> (`.services.ai.azure.com`) serves agents; the **Azure OpenAI** endpoint
> (`.openai.azure.com`) serves embeddings. Different APIs, same resource.

## Step 4 — Start the mock systems of record

In a **second terminal**, with the virtual environment activated:

```bash
python -m mcp_servers.run_all
```

You should see three servers start on ports 8931, 8932, and 8933. Leave this
running for the rest of the session.

These are real MCP servers, not stubs — the same protocol the agents use to
reach the real Atlassian and GitHub servers. In the take-home you point three
URLs at the real thing and change no agent code.

## Step 5 — Check everything

Back in your first terminal:

```bash
python -m agentic_sdlc.cli check
```

You want a table with your endpoints and three green rows for the mock servers.
A red row means the mock server terminal is not running. Anything else, see
[troubleshooting](troubleshooting.md).

---

Next: [03 — Index the governance corpus](03-index-corpus.md)
