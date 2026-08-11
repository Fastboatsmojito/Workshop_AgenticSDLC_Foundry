---
title: Reference run
description: What good output looks like at each gate, and how to check your own against it
audience: Participants comparing their run, and facilitators preparing a demo
estimated_reading_time: 6
---

# Reference run

`expected-run/` holds one complete pass of INIT-1042 through the three live
stages. Use it to answer "is my output roughly right?" without waiting for the
facilitator.

| File | Artifact | Produced by |
|---|---|---|
| `requirements.json` | `SystemRequirements@v1` | Requirements Agent, [guide 04](../workshop/04-requirements-agent.md) |
| `design.json` | `DesignArtifact@v1` | Design Agent, [guide 06](../workshop/06-design-and-breakdown.md) |
| `work_breakdown.json` | `WorkBreakdown@v1` | Work Breakdown Agent, [guide 06](../workshop/06-design-and-breakdown.md) |
| `audit.jsonl` | three `ApprovalRecord`s | The gate, [guide 05](../workshop/05-gate-and-audit.md) |

Your output will not match this word for word and is not supposed to. Models
vary run to run, and two competent analysts would not write the same
requirements either. What should match is the *shape*: the same kinds of fields
populated, citations that resolve, a DoR assessment that engages with the
initiative rather than rubber-stamping it, and open questions instead of
invented facts.

> These artifacts are hand-written rather than model-generated, so the reference
> does not drift when a model version changes. They are built through the real
> contract classes and hashed with the real code, so `audit.jsonl` genuinely
> covers them — `tests/test_expected_run.py` proves it, and the tamper test
> there is the same lesson as guide 05 in miniature.

## What to look for in your own output

**Requirements.** The reference finds five functional and five non-functional
requirements, and fails two Definition of Ready checks. Two failures is a good
sign, not a bad one: INIT-1042 genuinely does not state its scope exclusions or
name an owner for the retention period, and an agent that passes all eight
checks on this initiative is telling you what you want to hear. Look for
acceptance criteria written as given-when-then, a latency requirement with an
actual threshold rather than "fast", and the eligibility figure sitting in
`open_questions` rather than quietly invented.

**Design.** The reference keeps the intake system untouched and adds an
automated lane beside the manual path, because the initiative names intake as an
unchangeable system of record. Check that your design respects the stated
constraints, that each decision names alternatives it rejected, and that the
risks include the requirements-stage open questions still hanging over the
design. A design with no risks is not a confident design, it is an incurious one.

**Work breakdown.** Seven stories, forty-five points, dependencies recorded, and
sequencing notes that explain the ordering. Watch for stories that are really
tasks ("create the database table"), which is the most common failure here, and
for test cases that restate acceptance criteria instead of testing them.

## Comparing

```bash
python -m agentic_sdlc.cli run INIT-1042
```

Artifacts land in `.runs/INIT-1042/`. Diff any stage against the reference:

```bash
# macOS / Linux
diff <(jq -S . .runs/INIT-1042/requirements.json) <(jq -S . solutions/expected-run/requirements.json)

# PowerShell
code --diff .runs\INIT-1042\requirements.json solutions\expected-run\requirements.json
```

The diff will be large and that is fine. Read it for missing *categories* — no
data-handling requirement, no open questions, no citations — rather than for
different wording.

## Reading the audit trail

```bash
python -m agentic_sdlc.cli audit INIT-1042
```

Each line of `audit.jsonl` is one decision, bound to the hash of exactly what
the reviewer saw:

```json
{"artifact_hash":"2e84ddf9bfbe...","artifact_schema":"SystemRequirements@v1","audit_id":"aprv_ref000000001","stage":"requirements->design","decision":"approved","approver":"reference","edited":false}
```

The hash is the whole point. Change one character in `requirements.json` and the
approval stops covering it, with no separate check to remember to run:

```bash
python -m agentic_sdlc.cli tamper INIT-1042
python -m agentic_sdlc.cli verify INIT-1042
```

You do this live in [guide 05](../workshop/05-gate-and-audit.md).

## What a gate looks like

The console renders a summary, not raw JSON, because a reviewer facing a wall of
JSON rubber-stamps it. Full content is one keystroke away with `v`.

```text
╭──── HUMAN APPROVAL REQUIRED  ·  requirements->design ────╮
│   • 5 functional requirements                            │
│   • 5 non-functional requirements                        │
│   • Definition of Ready: FAIL (6/8 checks)               │
│   • Failing checks: DoR-03 Scope boundaries are          │
│     explicit, DoR-08 Open questions are listed, not      │
│     resolved by assumption                               │
│   • 4 open questions                                     │
│   • Grounded in: DOR-CHECKLIST §DoR-04 ...  [6 citations]│
│                                                          │
│   schema:   SystemRequirements@v1                        │
│   hash:     2e84ddf9bfbe...                              │
│   model:    gpt-4o-mini                                  │
╰──────────────────────────── initiative INIT-1042 ────────╯
decision [a]pprove [r]eject [e]dit [v]iew [q]uit >
```

Approving records the decision against that hash. Editing first re-validates
against the schema and changes the hash, and the record carries `edited: true`
so the trail distinguishes "the human agreed" from "the human fixed it" — which
is the more useful signal when you later ask whether an agent is good enough to
trust with less supervision.

## Regenerating

If you change a contract in `src/agentic_sdlc/contracts/`, the reference
artifacts may no longer validate. Rebuild them:

```bash
python solutions/make_expected_run.py
python -m pytest tests/test_expected_run.py -q
```

Edit the artifacts in `make_expected_run.py` rather than the JSON directly; the
hashes and `audit.jsonl` are derived, and hand-editing the JSON is exactly the
tampering the tests are there to catch.
