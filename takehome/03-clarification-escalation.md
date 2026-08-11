# Take-home 3 — Clarification and escalation (~45 min)

**Do this one.** Agents that guess confidently are the main way these systems
fail in production, and this is the fix.

Everything so far assumes the agent can complete its stage. Sometimes it cannot,
and the useful behaviour is to stop and ask rather than to produce something
plausible. `NeedsClarification` exists in the contracts; nothing returns it yet.
That is your job.

## The problem, made concrete

Create a deliberately under-specified initiative:

```json
{
  "id": "INIT-9001",
  "title": "Improve the claims experience",
  "business_need": "Customers are unhappy with how claims are handled. We want to make it better.",
  "requester": "Someone in the business",
  "constraints": [],
  "success_measures": []
}
```

Save it as `data/initiatives/INIT-9001.json` and run:

```bash
python -m agentic_sdlc.cli run INIT-9001 --stop-after requirements
```

Watch what happens. The agent will almost certainly produce a full, confident set
of requirements — inventing a scope nobody asked for, complete with citations
that are individually real and collectively beside the point.

**This is the failure mode that matters.** It does not look like a failure. It
looks like good work, and it is only wrong if you happen to know what was
actually wanted.

## Step 1 — Let the agent return either shape

The clean approach is a union response format:

```python
from typing import Union
from pydantic import BaseModel

class RequirementsOutcome(BaseModel):
    """Either the requirements, or an honest statement that they cannot be written."""
    result: Union[SystemRequirements, NeedsClarification]
```

Then in `requirements_agent.run`, use `RequirementsOutcome` as the
`response_format` and branch on what comes back.

Watch for two things. Strict structured output needs every field present, so
check how the union serialises for your model — you may need a discriminator
field such as `kind: Literal["requirements", "clarification"]` to make the
choice explicit rather than inferred. And a model given an easy way out will
sometimes take it, so the instructions must be clear that clarification is for
genuine blockers, not for difficulty.

## Step 2 — Say when to escalate

Add to `INSTRUCTIONS`. Be specific — vague criteria produce either constant
escalation or none:

```text
When you cannot proceed:

Return a clarification instead of requirements when the business need does not
say what outcome is wanted, when it could reasonably be read two incompatible
ways, or when a regulatory obligation applies and you cannot tell which.

Do not return a clarification because the work is large or the need is broad.
Breadth is normal; ambiguity about intent is not.

Ask one question: the single thing that unblocks the most work. State why it
blocks you and what you already considered, so the person answering does not
repeat your reasoning.
```

## Step 3 — Handle it in the orchestrator

`_may_continue` handles rejection. Clarification is a third outcome, and it is
not a failure:

```python
if isinstance(artifact, NeedsClarification):
    self.console.print(f"[yellow]{artifact.question}[/yellow]")
    answer = await self.gate._ask("answer (or blank to abandon) > ")
    if not answer:
        result.stopped_at = "requirements"
        result.stop_reason = f"unanswered clarification: {artifact.question}"
        return result
    # re-run the stage with the answer appended to the prompt
```

Decide two things while you are in here:

- **Does a clarification belong in the audit trail?** It is not an approval, but
  "the agent asked and a human answered X" is exactly the kind of thing someone
  reconstructing a decision six months later would want. Consider a
  `ClarificationRecord` alongside `ApprovalRecord`.
- **How many rounds before you give up?** An agent that asks three times in a row
  is not converging, and an unbounded loop in a governed flow is its own risk.

## Step 4 — Check both directions

Run `INIT-9001` — it should now ask rather than invent. Then run `INIT-1042`,
which is well specified, and confirm it does **not** ask.

Both matter. An agent that escalates everything is as useless as one that
escalates nothing, and it is easy to over-correct into the first after seeing the
second.

## Exercises

**A. Route by question type.** A regulatory question goes to compliance; a scope
question goes to the requester. Add `route_to` to `NeedsClarification` and let
the agent choose.

**B. Escalate from Design.** The Design Agent hits a requirement it cannot satisfy
within the architecture standards. Should it escalate, or record a risk and
continue? Argue it, then implement your answer.

**C. Answer from the corpus first.** Before escalating to a human, have the agent
search for an answer. Escalate only if retrieval finds nothing. Measure how often
this avoids a human round-trip — that ratio is the business case for the pattern.

---

Next: [04 — Swap the mocks for real systems](04-swap-the-mocks.md)
