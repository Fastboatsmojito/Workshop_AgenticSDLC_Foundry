# 05 — The gate and the audit trail (50–75 min)

This is the centre of the workshop. An approval that you cannot tie to specific
content is not governance, it is paperwork. By the end of this guide you will
have watched an approval stop applying because someone changed the thing it
approved — with no extra check written to catch it.

## The two human-in-the-loop mechanisms

They get conflated constantly, so name them once and keep them apart:

| | Stage gate | Tool approval |
|---|---|---|
| Approves | An **artifact** between two agents | One individual **tool call** |
| Runs in | The orchestrator | The Agent Framework |
| Example | "These requirements may go to Design" | "You may create this Jira story" |
| Built in | This guide | Guide 06 |

## Step 1 — Read what a decision records

Open `src/agentic_sdlc/contracts/approval.py`.

```python
class ApprovalRecord(BaseModel):
    audit_id: str
    stage: str                # "requirements->design"
    decision: Literal["approved", "rejected"]
    approver: str
    artifact_schema: str      # "SystemRequirements@v1"
    artifact_hash: str        # sha256 of the exact artifact approved
    edited: bool
    timestamp: datetime
```

`artifact_hash` is the whole idea. Without it a record says "someone approved
something at this stage". With it, the record says "this person approved exactly
this content", and that claim is checkable forever.

Then read `covers()` and `assert_approved()`. `assert_approved` distinguishes
three different failures, and the third is the interesting one:

- **never reviewed** — no record for this stage
- **rejected** — a decision exists and it was no
- **approved, then modified** — a record exists, but its hash does not match what
  is in front of us

## Step 2 — Where the gate is actually enforced

Open `src/agentic_sdlc/orchestrator.py` and find `_may_continue`. It is called
immediately before every handoff, and the whole design turns on it:

```python
record = self.registry.assert_approved(stage, artifact)
```

If that raises, the next agent is never constructed and never runs. That single
line is what separates a gate from a print statement. Everything else — the
panel, the prompt, the colours — is user interface.

Notice too that the orchestrator carries `outcome.artifact` forward rather than
the artifact it passed in. If the reviewer edited at the gate, the edited version
is what continues, and it is what got hashed.

## Step 3 — Approve, and find the decision in three places

```bash
python -m agentic_sdlc.cli run INIT-1042 --stop-after requirements
```

Approve it. Add a comment — something a colleague would find useful in six
months, not "ok".

Now go find that decision three ways.

**The append-only log:**

```bash
cat .runs/audit.jsonl
```

One JSON object per line, never rewritten. You can read it without any tooling,
which matters when an auditor asks.

**The pretty view:**

```bash
python -m agentic_sdlc.cli audit INIT-1042
```

**The Confluence page** the gate wrote through MCP — `scripts/show_confluence_page.py`
calls `get_page` on the mock Confluence server and prints the body:

```bash
python scripts/show_confluence_page.py audit-init-1042
```

Three sinks, one code path — look at `AuditTrail.record` in
`src/agentic_sdlc/gate/audit.py`. In the take-home you change the Confluence URL
to the real Atlassian MCP server and this same code writes to a real page.

Note which sink is authoritative. `JsonlSink` is primary and a failure there
fails the gate; the others are best-effort so a stopped mock server degrades the
trail instead of halting your workshop. That is a deliberate trade-off, and in
production you would likely make Confluence primary too.

## Step 4 — Reject, and watch the flow stop

```bash
python -m agentic_sdlc.cli run INIT-1042
```

This time press `r` and give a real reason — for example that the scope
exclusions DoR-03 requires are still unstated.

The run stops. The Design Agent is never built. The rejection sits in the trail
with your reason attached, which is the part that makes a rejection useful later.

## Step 5 — Edit at the gate, and watch the schema hold

Run again. This time press `e`, choose `open_questions`, and enter a JSON list:

```json
["Who owns confirming the explainability obligation?"]
```

The artifact is re-validated and the hash changes on screen. Approve it, and note
that the record carries `edited: true` — a reviewer who rewrote the artifact
before approving is a materially different fact from one who accepted it as-is.

Now try an edit the schema will not accept. Press `e`, choose `functional`, and
enter:

```json
"not a list"
```

It is refused and the edit is not applied. **The gate is structurally incapable
of handing a malformed artifact to the next agent.** A reviewer under time
pressure cannot break the contract by accident.

## Step 6 — The tamper demonstration

This is the one to watch closely.

Run the flow and approve at the requirements gate:

```bash
python -m agentic_sdlc.cli run INIT-1042 --stop-after requirements
```

Confirm the approval is currently valid:

```bash
python -m agentic_sdlc.cli verify INIT-1042
```

Green. The saved artifact is covered by an approval for its exact content.

Now change the approved artifact, as though someone quietly adjusted it after
sign-off:

```bash
python -m agentic_sdlc.cli tamper INIT-1042
```

That appends one line to `open_questions` in `.runs/INIT-1042/requirements.json`.
It is a small, legal, schema-valid edit — exactly the kind that would slide
through a review. Open the file and see for yourself.

Verify again:

```bash
python -m agentic_sdlc.cli verify INIT-1042
```

```
Approval aprv_... does not cover the current artifact.
Approved hash 9f2c1a4b8e07..., current hash 41d0e7c2ba95....
The artifact changed after it was approved, so the approval no longer applies.
```

Nobody wrote a tamper check. The approval stopped applying because it was never
about the stage in the first place — it was about the content. Re-run the flow
from here and the handoff to Design is refused.

To recover, re-approve the current content. That is the correct outcome: a human
looks at what it says *now* and decides again.

## Step 7 — Prove it holds, without Azure

```bash
python -m pytest tests/test_approval_gate.py -v
```

Read the test names. They are the specification: an approval permits the handoff,
a missing one blocks it, a rejection blocks it with its reason, editing after
approval invalidates it, approvals do not leak across stages, and the trail is
append-only.

These run in a CI pipeline with no Azure resources at all, which is the practical
answer to "how do you regression-test governance".

## What you have now

- A gate that suspends the run and records a hash-bound decision
- An audit trail in three places, written by one code path
- Direct evidence that editing an approved artifact breaks its approval
- Tests that hold the property without needing a subscription

---

Next: [06 — Design and Work Breakdown agents](06-design-and-breakdown.md)
