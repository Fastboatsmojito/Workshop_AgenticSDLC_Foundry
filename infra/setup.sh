#!/usr/bin/env bash
# Provision everything guides 01 and 02 create.
#
#   ./infra/setup.sh yourname [location]
#
# Search provisioning starts first with --no-wait, because it is the long pole.
# The script prints a ready-to-paste .env at the end.
#
# The guides walk through these steps by hand. This exists for facilitators
# preparing a demo environment, and for anyone re-running after cleanup.

set -euo pipefail

ALIAS="${1:?usage: setup.sh <alias> [location]}"
LOCATION="${2:-canadacentral}"

RG="rg-agentic-sdlc-${ALIAS}"
SEARCH="srch-agentic-sdlc-${ALIAS}"
FOUNDRY="aif-agentic-sdlc-${ALIAS}"
CHAT_DEPLOYMENT="gpt-4o-mini"
EMBED_DEPLOYMENT="text-embedding-3-small"

echo "==> Resource group ${RG} in ${LOCATION}"
az group create --name "$RG" --location "$LOCATION" --output none

echo "==> Starting Azure AI Search (background; this is the long pole)"
az search service create \
  --name "$SEARCH" --resource-group "$RG" \
  --sku basic --location "$LOCATION" --no-wait --output none

echo "==> Foundry (AI Services) resource ${FOUNDRY}"
az cognitiveservices account create \
  --name "$FOUNDRY" --resource-group "$RG" --location "$LOCATION" \
  --kind AIServices --sku S0 --custom-domain "$FOUNDRY" --yes --output none

echo "==> Chat deployment ${CHAT_DEPLOYMENT}"
az cognitiveservices account deployment create \
  --name "$FOUNDRY" --resource-group "$RG" \
  --deployment-name "$CHAT_DEPLOYMENT" \
  --model-name "$CHAT_DEPLOYMENT" --model-version "2024-07-18" --model-format OpenAI \
  --sku-capacity 30 --sku-name GlobalStandard --output none

echo "==> Embedding deployment ${EMBED_DEPLOYMENT}"
az cognitiveservices account deployment create \
  --name "$FOUNDRY" --resource-group "$RG" \
  --deployment-name "$EMBED_DEPLOYMENT" \
  --model-name "$EMBED_DEPLOYMENT" --model-version "1" --model-format OpenAI \
  --sku-capacity 30 --sku-name Standard --output none

echo "==> Granting yourself Foundry User"
SUBSCRIPTION=$(az account show --query id -o tsv)
USER_ID=$(az ad signed-in-user show --query id -o tsv)
az role assignment create \
  --assignee "$USER_ID" --role "Foundry User" \
  --scope "/subscriptions/${SUBSCRIPTION}/resourceGroups/${RG}/providers/Microsoft.CognitiveServices/accounts/${FOUNDRY}" \
  --output none || echo "    (role assignment failed or already exists; see guide 01 step 3)"

echo "==> Waiting for Azure AI Search to finish provisioning"
until [ "$(az search service show --name "$SEARCH" --resource-group "$RG" --query status -o tsv)" = "running" ]; do
  printf '.' ; sleep 15
done
echo " ready"

SEARCH_KEY=$(az search admin-key show --service-name "$SEARCH" --resource-group "$RG" --query primaryKey -o tsv)

cat <<EOF

============================================================
Done. Create the project in the portal, then paste this into .env

  1. https://ai.azure.com -> Create new -> Project
  2. Use resource: ${FOUNDRY}
  3. Name it: agentic-sdlc
  4. Copy the project endpoint from the Overview page into
     FOUNDRY_PROJECT_ENDPOINT below. Copy it exactly - it can
     include a path such as /api/projects/agentic-sdlc.
============================================================

FOUNDRY_PROJECT_ENDPOINT=https://${FOUNDRY}.services.ai.azure.com
FOUNDRY_MODEL=${CHAT_DEPLOYMENT}
FOUNDRY_OPENAI_ENDPOINT=https://${FOUNDRY}.openai.azure.com
EMBEDDING_DEPLOYMENT=${EMBED_DEPLOYMENT}
EMBEDDING_API_VERSION=2024-10-21
EMBEDDING_DIMENSIONS=1536
SEARCH_ENDPOINT=https://${SEARCH}.search.windows.net
SEARCH_API_KEY=${SEARCH_KEY}
SEARCH_INDEX_NAME=sdlc-corpus
MCP_JIRA_URL=http://127.0.0.1:8931/mcp
MCP_GITHUB_URL=http://127.0.0.1:8932/mcp
MCP_CONFLUENCE_URL=http://127.0.0.1:8933/mcp
APPROVER_ALIAS=${ALIAS}
ENABLE_TRACING=false

Clean up with:  az group delete --name ${RG} --yes --no-wait
EOF
