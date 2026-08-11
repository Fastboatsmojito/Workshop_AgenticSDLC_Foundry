# 07 — Orchestrate and observe (100–115 min)

You have three agents and two gates. This guide is about the thing holding them
together, and about seeing inside a run when it goes wrong.

## Part 1 — Why the orchestrator is hand-written

Open `src/agentic_sdlc/orchestrator.py`. It is ordinary Python: run an agent,
gate its output, check the approval, run the next agent.

The Agent Framework ships orchestration builders — `SequentialBuilder`,
`HandoffBuilder`, `GroupChatBuilder`, in the separate
`agent-framework-orchestrations` package — and for many multi-agent systems you
should use them. We did not here, for one reason:

**In a governed lifecycle, the control flow is the governance model.** An auditor
asking "what stops requirements reaching design without approval?" deserves a
line of code, not a builder configuration. This is the line:

```python
record = self.registry.assert_approved(stage, artifact)
```

Explicit orchestration is worth it where the sequence is fixed, short, and
regulated. Where routing is dynamic and the agent population changes, use the
builders. This flow is the first kind.

### The subtle bit worth reading twice

```python
outcome = await self.gate.review(...)
requirements = outcome.artifact   # the edited version, if the reviewer edited
```

The orchestrator carries forward what the gate returned, not what it passed in.
Get this wrong and you approve one artifact then hand a different one onward —
the exact failure the hash is designed to catch. Here the hash catches your own
bug, which is a decent argument for the design.

## Part 2 — Run the whole thing

```bash
python -m agentic_sdlc.cli run INIT-1042
```

Approve at all three gates, approve the Jira writes, and watch a business
requirement become a backlog. Then:

```bash
python -m agentic_sdlc.cli audit INIT-1042
python -m agentic_sdlc.cli verify INIT-1042
```

`verify` re-checks every saved artifact against the trail. Green across the board
means each one is covered by an approval for its exact content.

## Part 3 — Try the second initiative

`INIT-1077` is deliberately thinner: fewer constraints, vaguer measures, no
mention of who may see what.

```bash
python -m agentic_sdlc.cli run INIT-1077 --stop-after requirements
```

Compare its Definition of Ready against `INIT-1042`. A well-behaved run fails
several checks and raises open questions instead of inventing answers. **This is
the more important test of the two.** Any agent looks good on a well-specified
input. What you need to know is whether it tells you when the input is not good
enough — because in production, most inputs are not.

If it produces a confident, all-green assessment of INIT-1077, that is a finding
about your instructions, not about the initiative.

## Part 4 — Turn on tracing

Optional, and worth it if you have five minutes.

In the Foundry portal, connect an Application Insights resource to your project
(**Management centre** → **Connected resources**). Then flip the flag in `.env`:

```text
ENABLE_TRACING=true
```

Install the exporter and run a short flow:

```bash
python -m pip install azure-monitor-opentelemetry
python -m agentic_sdlc.cli run INIT-1042 --stop-after design
```

In the portal, open **Tracing**. You get a span per agent run, a child span per
tool call, and — because of `TraceSink` — the approval decisions as span events
inline with the model steps. The human decision sits in the same timeline as the
model calls rather than in a separate system, which is what makes a trace
answerable to "what happened on this run".

Note the trade-off in `observability.py`: `enable_sensitive_data=True` puts
prompts and responses in the trace. That is what makes it useful for debugging
and unacceptable against real customer data. Fictional corpus here; make a
deliberate decision in production.

## Part 5 — What you would add next

Four things stand between this and production, and it is worth naming them while
the code is fresh:

**Evaluation.** Right now a human judges quality at the gate. You would add
scored evaluation — does the DoR assessment match a human's on a labelled set,
are citations real, are requirements testable — and run it in CI on every change
to instructions. `agent_framework.foundry` ships `FoundryEvals` and
`evaluate_traces` for this.

**Checkpointing.** Today the run lives in memory and a gate is a blocking prompt.
Real gates take days. You would persist run state and resume from an approval
arriving by email or a Jira transition, which is a bigger change to the
orchestrator than it first appears.

**Identity.** Agents run as you. In production each agent gets its own workload
identity with least-privilege access to Jira, GitHub, and Confluence, so the
audit trail records which *agent* acted, not which human was logged in.

**Content safety and prompt-injection defence.** The corpus is trusted here. When
requirements come from an intake form a customer can write into, retrieved
content becomes untrusted input.

## What you have now

- The full live flow: three agents, three gates, one audit trail
- Two initiatives, one of which exposes how the agents behave on a weak input
- Optional tracing showing model steps and human decisions in one timeline
- A named list of what production still needs

---

Next: [08 — Wrap up](08-wrap-up.md)
