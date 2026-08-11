---
title: 00 - Before you start
description: Prerequisites and local setup for the Agentic SDLC workshop
---

Do this before the session starts. It takes about ten minutes and none of it is
interesting, which is exactly why it should not eat live time.

## What you need

* Use an Azure subscription with rights to create resources. Confirm the active
  subscription with `az account show`.
* Install the Azure CLI and sign in with `az login`. Agents authenticate as you,
  not with a key.
* Install Python 3.11 or newer. Check it with `python --version`.
* Use VS Code with GitHub Copilot. Confirm the Copilot icon is active.
* Install Git. Check it with `git --version`.

You do **not** need a Jira, Confluence, or GitHub account. Those run as mock
servers on your laptop.

## Set up

```bash
git clone https://github.com/Fastboatsmojito/Workshop_AgenticSDLC_Foundry.git
cd Workshop_AgenticSDLC_Foundry

python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
python -m pip check
```

The dependency check must report `No broken requirements found`. The workshop
intentionally uses MCP 1.29 because the current Agent Framework MCP adapter uses
the MCP 1.x API. Installing MCP 2 into this environment is unsupported.

Then sign in and confirm you are on the right subscription:

```bash
az login
az account show --query "{subscription:name, tenant:tenantId}" -o table
```

## Prove the local half works

Nothing here touches Azure, so it should pass right now:

```bash
python -m pytest -q
```

You should see all tests pass. This exercises the typed contracts, the approval
gate, the audit trail, the corpus chunking, and the three mock MCP servers over
real HTTP. If this passes, the only thing that can still go wrong today is Azure
configuration.

## The vocabulary

Six terms carry the whole workshop. You will meet each one in code within the
first hour.

**Agent**: a model deployment plus instructions plus tools, that you can call
and that can call tools back. In code: `Agent(client=FoundryChatClient(...))`.

**Artifact**: the typed output of one stage. A Pydantic model, validated on the
way out. `SystemRequirements`, `DesignArtifact`, `WorkBreakdown`.

**Handoff**: passing an artifact from one agent to the next. Legitimate only
when the artifact validates *and* carries a matching approval.

**Stage gate**: the human approval between two agents. Suspends the run,
records a decision bound to the artifact's hash.

**Tool approval**: a different human-in-the-loop. This is sign-off on one individual
tool call, such as a single write to Jira. Both exist here; do not conflate them.

**Grounding**: retrieval from the governance corpus in Azure AI Search, scoped
per agent so each one can only see the documents it is entitled to reason over.

## What you are building, in one sentence

A business requirement enters, three agents move it through requirements, design,
and work breakdown, a human approves at every boundary, and every decision is
recorded against the hash of exactly what was approved. Changing an artifact
after the fact breaks the chain automatically.

## The two Copilots

GitHub Copilot in your editor helps you write Agent Framework code. The Delivery
Agent (take-home) is a Foundry agent that writes code itself. When a guide says
"Copilot", it means the one in your editor.

---

Next: [01 — Create your resources](01-create-resources.md)
