# 08 — Wrap up (115–120 min)

## What you built

From nothing, in two hours:

- A **hybrid vector index** over a governance corpus, with per-agent retrieval
  scoping enforced by a filter rather than by instructions
- **Three agents** — Requirements, Design, Work Breakdown — each with its own
  scope, its own typed artifact, and instructions written to constrain
- **A human approval gate** at every handoff, recording hash-bound decisions to
  three sinks from one code path
- **Tool approval** on every write to a system of record, separate from the stage
  gate and operating at a different granularity
- **An orchestrator** that refuses to advance without a valid approval, proven by
  watching a tampered artifact break its own approval
- **Tests** that hold the governance properties with no Azure resources at all

## The five things worth remembering

**1. An approval is about content, not about a stage.** Hash-binding turns "this
was approved" into "this exact thing was approved", and it costs one line of
code. Everything else in the gate is user interface.

**2. Make it structurally impossible before you ask nicely.** The Requirements
Agent does not design solutions because it cannot retrieve the architecture
standards. The instruction saying so is a backup, not the mechanism.

**3. Typed artifacts turn handoffs into checks.** A Pydantic model as
`response_format` means the next agent either gets something valid or the run
stops. Prose between agents gives you neither guarantee nor a place to attach a
hash.

**4. There are two human-in-the-loop mechanisms and they are not the same.** The
stage gate approves an artifact between agents; tool approval approves one
individual action. You need both, at different granularities.

**5. Watch how agents behave on bad input.** INIT-1042 makes any agent look
competent. INIT-1077 tells you whether it will admit what it does not know —
which is the only property that matters in production, where most inputs are
weak.

## Where this maps to your delivery model

| Your lifecycle stage | What runs | Human decision |
|---|---|---|
| Intake → requirements | Requirements Agent, grounded on the DoR | Approve, reject, or edit at the gate |
| Requirements → design | Design Agent, grounded on architecture standards | Approve, reject, or edit at the gate |
| Design → backlog | Work Breakdown Agent, writing to Jira | Approve at the gate, plus per-write approval |
| Backlog → code | Delivery Agent (take-home) | Pull request review, per-write approval |
| Code → release | Release Agent (take-home) | Approve the release package |

The agents do the drafting. Humans keep every decision that carries
accountability. Nothing reaches a system of record without someone saying yes.

## Take it further

[Track B](../takehome/README.md), self-paced:

1. [The Delivery Agent](../takehome/01-delivery-agent.md) — a story becomes a pull request
2. [The Release Agent](../takehome/02-release-agent.md) — merged PRs become a published package
3. [Clarification and escalation](../takehome/03-clarification-escalation.md) — an agent that asks instead of guessing
4. [Swap the mocks for the real systems](../takehome/04-swap-the-mocks.md) — three URLs, no agent code
5. [Evaluation in CI](../takehome/05-evaluation.md) — score the agents on every change

## Before you go

Leave your resources running until you have finished the take-home. When you are
done: [cleanup](cleanup.md) — one resource group delete.

## A closing note on scope

This is a workshop, not a reference architecture. Keys sit in a `.env`, agents run
as you, gates block on a console prompt, and the corpus is fictional. What it
does faithfully reproduce is the *shape* of the governance problem: typed
handoffs, content-bound approvals, enforced sequencing, and an audit trail you
can hand to someone who was not there.

`infra/reference-architecture.md` describes what changes on the way to
production.
