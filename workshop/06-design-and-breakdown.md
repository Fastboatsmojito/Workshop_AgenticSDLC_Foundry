# 06 — Design and Work Breakdown agents (75–100 min)

Two more agents. Both follow the pattern from guide 04, so this moves faster. The
new material is the Work Breakdown Agent writing to a system of record, which
introduces the second flavour of human-in-the-loop.

## Part 1 — The Design Agent

### What changes from the Requirements Agent

Only three things:

| | Requirements Agent | Design Agent |
|---|---|---|
| Retrieval scope | `dor`, `standards` | `architecture`, `design_format` |
| Output artifact | `SystemRequirements` | `DesignArtifact` |
| Input | The initiative | **Approved** requirements |

That is the whole diff. Open `src/agentic_sdlc/agents/design_agent.py` and
confirm it — the shape is identical to guide 04.

### The instruction worth noticing

> *"You receive system requirements that a human has already approved. Treat them
> as settled: your job is to design a solution that satisfies them, not to
> renegotiate scope. If a requirement genuinely cannot be met, say so in the
> risks rather than quietly dropping it."*

Without that last clause, a model that cannot satisfy a requirement tends to
quietly stop mentioning it. Forcing the omission into `risks` makes the gap
visible to the reviewer, which is the only place it can be dealt with.

### Run it

```bash
python -m agentic_sdlc.cli run INIT-1042 --stop-after design
```

Approve at the requirements gate, let Design run, then read it at the design gate.

Look for traceability specifically: **is every requirement covered by a
component?** The architecture standards require it (ARC-12), and the instructions
require unmet requirements to appear as risks. If NFR-01 on auditability has no
home in the design and no risk mentioning it, that is a real finding — reject it
and say so. A rejection here is a better outcome than a rubber stamp.

## Part 2 — The Work Breakdown Agent

This one writes to Jira, which is the first time an agent changes something
outside its own output.

### Tool approval: the other human-in-the-loop

Open `src/agentic_sdlc/agents/workbreakdown_agent.py` and look at the tools:

```python
jira_write = MCPStreamableHTTPTool(
    name="jira_write",
    url=settings.mcp.jira_url,
    allowed_tools=["create_epic", "create_story", "create_test_case"],
    approval_mode="always_require",
)
jira_read = MCPStreamableHTTPTool(
    name="jira_read",
    url=settings.mcp.jira_url,
    allowed_tools=["list_issues", "get_issue"],
    approval_mode="never_require",
)
```

Two tools, same server, different posture. **Writes need a human; reads do not.**
`allowed_tools` is what makes this possible — it is the mechanism for splitting
one MCP server into differently-governed surfaces, and it is worth remembering
when you wire the real Atlassian server later.

This is the framework's own approval interrupt. When the model calls a write, the
run comes back asking for sign-off instead of returning an answer. The loop that
handles it is in `run_structured` in `src/agentic_sdlc/agents/base.py`:

```python
while response.user_input_requests:
    ...
    followup.append(Message("user", [request.to_function_approval_response(approved)]))
    response = await agent.run(followup, options=options)
```

Compare that with the stage gate in the orchestrator. Different mechanism,
different granularity, both human-in-the-loop:

- **Tool approval** — the framework pauses one action mid-run
- **Stage gate** — the orchestrator pauses the whole flow between agents

### Run the full live flow

```bash
python -m agentic_sdlc.cli run INIT-1042
```

Approve at the requirements gate and the design gate. Then the Work Breakdown
Agent starts creating Jira items and **you get an approval prompt per write**.

Approve the epics. Then **reject one story** — pick one and press `n`.

Watch what happens: the agent is told the call was refused. Its instructions say
not to retry the same arguments, and to note the gap in `sequencing_notes`.
Whether it complies is worth observing rather than assuming; you now have a
concrete example of how an agent handles being told no, which is the thing you
actually need to know before letting one near a real backlog.

### Confirm Jira matches the artifact

`scripts/list_jira_issues.py` calls `list_issues` on the mock Jira server and
prints every issue recorded for the initiative:

```bash
python scripts/list_jira_issues.py INIT-1042
```

Compare against `.runs/INIT-1042/work_breakdown.json`. The instructions say the
artifact must match what was actually created. If you rejected a write, does the
artifact honestly reflect that?

This is the check that matters most in production: **the agent's report of what
it did versus what is in the system of record.** Anything an agent tells you
about its own actions is a claim until you verify it against the system.

## What you have now

- Three agents, all the same shape, differing only in scope, input, and output
- Both human-in-the-loop mechanisms working: stage gates and tool approval
- Epics, stories, and test cases in a system of record, created under approval
- A demonstrated answer to "what happens when a human says no"

---

Next: [07 — Orchestrate and observe](07-orchestrate-and-observe.md)
