# 01 — Create your resources (0–12 min)

> **Do step 1 first and do not wait for it.** Azure AI Search takes five to
> fifteen minutes to provision. Start it now and it will be ready by the time
> guide 03 needs it. Everything else in guides 01 and 02 happens while it builds.

Do this by hand. It is twelve minutes, and knowing which resources exist and why
matters when something misbehaves later. `infra/setup.ps1` and `infra/setup.sh`
do all of guides 01 and 02 in one command, and exist for facilitators preparing
a demo environment or for anyone rebuilding after cleanup — not for your first
time through.

## Step 1 — Start Azure AI Search provisioning (do this first)

Pick a unique name. Search service names are globally unique, lowercase, and
allow hyphens.

Set three variables once; the rest of the guides reuse them. Use the block for
your shell — the `az` commands themselves are the same in both.

**bash**

```bash
export ALIAS="yourname"
export LOCATION="canadacentral"
export RG="rg-agentic-sdlc-$ALIAS"

az group create --name $RG --location $LOCATION

az search service create \
  --name "srch-agentic-sdlc-$ALIAS" \
  --resource-group $RG \
  --sku basic \
  --location $LOCATION \
  --no-wait
```

**PowerShell**

```powershell
$ALIAS = "yourname"
$LOCATION = "canadacentral"
$RG = "rg-agentic-sdlc-$ALIAS"

az group create --name $RG --location $LOCATION

az search service create `
  --name "srch-agentic-sdlc-$ALIAS" `
  --resource-group $RG `
  --sku basic `
  --location $LOCATION `
  --no-wait
```

`--no-wait` is the important flag. The command returns immediately and Azure
keeps building in the background.

> **Why Basic and not Free?** The Free tier is limited to three indexes and no
> guaranteed capacity, and it cannot be created if your subscription already has
> one. Basic is roughly seventy-five dollars a month, and you delete it at the
> end of the take-home.

## Step 2 — Create the Foundry resource and project

While Search provisions:

**bash**

```bash
az cognitiveservices account create \
  --name "aif-agentic-sdlc-$ALIAS" \
  --resource-group $RG \
  --location $LOCATION \
  --kind AIServices \
  --sku S0 \
  --custom-domain "aif-agentic-sdlc-$ALIAS" \
  --yes
```

**PowerShell**

```powershell
az cognitiveservices account create `
  --name "aif-agentic-sdlc-$ALIAS" `
  --resource-group $RG `
  --location $LOCATION `
  --kind AIServices `
  --sku S0 `
  --custom-domain "aif-agentic-sdlc-$ALIAS" `
  --yes
```

The custom domain matters: it is what gives you the
`https://<name>.openai.azure.com` endpoint used for embeddings later.

Now create the project in the portal, which is quicker than the CLI for this one
step:

1. Go to [ai.azure.com](https://ai.azure.com) and sign in.
2. Select **Create new** → **Project**.
3. Choose the resource `aif-agentic-sdlc-<alias>` you just created.
4. Name the project `agentic-sdlc`.
5. Select **Create**.

On the project **Overview** page, copy the **Azure AI Foundry project endpoint**.
It looks like `https://aif-agentic-sdlc-<alias>.services.ai.azure.com`, and it
can include a project path such as `/api/projects/agentic-sdlc` — copy it
exactly as shown and do not shorten it. You need it in guide 02.

## Step 3 — Give yourself access

Your `az login` identity is what the agents authenticate as, so it needs the
**Foundry User** role on the Foundry resource. (Some tenants still display the
former name **Azure AI User** while the rename rolls out; it is the same role.)

**bash**

```bash
SUBSCRIPTION=$(az account show --query id -o tsv)
USER_ID=$(az ad signed-in-user show --query id -o tsv)

az role assignment create \
  --assignee $USER_ID \
  --role "Foundry User" \
  --scope "/subscriptions/$SUBSCRIPTION/resourceGroups/$RG/providers/Microsoft.CognitiveServices/accounts/aif-agentic-sdlc-$ALIAS"
```

**PowerShell**

```powershell
$SUBSCRIPTION = az account show --query id -o tsv
$USER_ID = az ad signed-in-user show --query id -o tsv

az role assignment create `
  --assignee $USER_ID `
  --role "Foundry User" `
  --scope "/subscriptions/$SUBSCRIPTION/resourceGroups/$RG/providers/Microsoft.CognitiveServices/accounts/aif-agentic-sdlc-$ALIAS"
```

If this fails because you lack permission to assign roles, ask your facilitator —
in many tenants the role is already granted at the resource group level. Role
assignments can take a minute or two to take effect.

## Step 4 — Check on Search

This one is a single line, so it is identical in both shells:

```bash
az search service show --name "srch-agentic-sdlc-$ALIAS" --resource-group $RG --query "{name:name, status:status, sku:sku.name}" -o table
```

`status` becomes `running` when it is ready. If it still says `provisioning`,
carry on to guide 02 — you do not need it until guide 03.

## What you have now

- A resource group holding everything, so cleanup is one delete
- A Foundry resource and project, with your identity able to call it
- An Azure AI Search service, provisioning in the background

---

Next: [02 — Deploy your models](02-deploy-models.md)
