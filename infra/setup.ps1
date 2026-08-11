# Provision everything guides 01 and 02 create.
#
#   .\infra\setup.ps1 -Alias yourname [-Location canadacentral]
#
# Search provisioning starts first with --no-wait, because it is the long pole.
# The script prints a ready-to-paste .env at the end.
#
# The guides walk through these steps by hand. This exists for facilitators
# preparing a demo environment, and for anyone re-running after cleanup.

param(
    [Parameter(Mandatory = $true)][string]$Alias,
    [string]$Location = "canadacentral"
)

$ErrorActionPreference = "Stop"

$rg              = "rg-agentic-sdlc-$Alias"
$search          = "srch-agentic-sdlc-$Alias"
$foundry         = "aif-agentic-sdlc-$Alias"
$chatDeployment  = "gpt-4o-mini"
$embedDeployment = "text-embedding-3-small"

Write-Host "==> Resource group $rg in $Location"
az group create --name $rg --location $Location --output none

Write-Host "==> Starting Azure AI Search (background; this is the long pole)"
az search service create --name $search --resource-group $rg --sku basic --location $Location --no-wait --output none

Write-Host "==> Foundry (AI Services) resource $foundry"
az cognitiveservices account create --name $foundry --resource-group $rg --location $Location `
    --kind AIServices --sku S0 --custom-domain $foundry --yes --output none

Write-Host "==> Chat deployment $chatDeployment"
az cognitiveservices account deployment create --name $foundry --resource-group $rg `
    --deployment-name $chatDeployment --model-name $chatDeployment `
    --model-version "2024-07-18" --model-format OpenAI `
    --sku-capacity 30 --sku-name GlobalStandard --output none

Write-Host "==> Embedding deployment $embedDeployment"
az cognitiveservices account deployment create --name $foundry --resource-group $rg `
    --deployment-name $embedDeployment --model-name $embedDeployment `
    --model-version "1" --model-format OpenAI `
    --sku-capacity 30 --sku-name Standard --output none

Write-Host "==> Granting yourself Foundry User"
$subscription = az account show --query id -o tsv
$userId       = az ad signed-in-user show --query id -o tsv
$scope        = "/subscriptions/$subscription/resourceGroups/$rg/providers/Microsoft.CognitiveServices/accounts/$foundry"
az role assignment create --assignee $userId --role "Foundry User" --scope $scope --output none
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Role assignment failed or already exists; see guide 01 step 3."
}

Write-Host "==> Waiting for Azure AI Search to finish provisioning"
do {
    Start-Sleep -Seconds 15
    Write-Host "." -NoNewline
    $status = az search service show --name $search --resource-group $rg --query status -o tsv
} while ($status -ne "running")
Write-Host " ready"

$searchKey = az search admin-key show --service-name $search --resource-group $rg --query primaryKey -o tsv

Write-Host @"

============================================================
Done. Create the project in the portal, then paste this into .env

  1. https://ai.azure.com -> Create new -> Project
  2. Use resource: $foundry
  3. Name it: agentic-sdlc
  4. Copy the project endpoint from the Overview page into
     FOUNDRY_PROJECT_ENDPOINT below. Copy it exactly - it can
     include a path such as /api/projects/agentic-sdlc.
============================================================

FOUNDRY_PROJECT_ENDPOINT=https://$foundry.services.ai.azure.com
FOUNDRY_MODEL=$chatDeployment
FOUNDRY_OPENAI_ENDPOINT=https://$foundry.openai.azure.com
EMBEDDING_DEPLOYMENT=$embedDeployment
EMBEDDING_API_VERSION=2024-10-21
EMBEDDING_DIMENSIONS=1536
SEARCH_ENDPOINT=https://$search.search.windows.net
SEARCH_API_KEY=$searchKey
SEARCH_INDEX_NAME=sdlc-corpus
MCP_JIRA_URL=http://127.0.0.1:8931/mcp
MCP_GITHUB_URL=http://127.0.0.1:8932/mcp
MCP_CONFLUENCE_URL=http://127.0.0.1:8933/mcp
APPROVER_ALIAS=$Alias
ENABLE_TRACING=false

Clean up with:  az group delete --name $rg --yes --no-wait
"@
