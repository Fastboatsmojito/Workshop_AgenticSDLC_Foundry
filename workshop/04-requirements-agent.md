# 04 — Build the Requirements Agent (28–50 min)

This is the guide where you learn the pattern. The next two agents are the same
shape with different scope and different output, so slow down here and the rest
goes quickly.

## The pattern, in one picture

Every agent in this workshop is four decisions:

1. **Which model and client** — `Agent(client=FoundryChatClient(...))`
2. **What it may retrieve** — a search tool scoped to specific `doc_type`s
3. **What it must produce** — a Pydantic artifact passed as `response_format`
4. **What it must not do** — instructions that constrain, not just encourage

## Step 1 — Read the artifact before the agent

Open `src/agentic_sdlc/contracts/artifacts.py` and find `SystemRequirements`.

The output shape is the contract, so it comes first. Notice three things:

**No field is optional and none has a default.** Strict structured output
requires every field to be present in the response. "Nothing here" is an empty
list or an empty string, never a missing key. This constrains schema design in a
way that surprises people, so meet it now rather than at 90 minutes.

**`definition_of_ready` is structured, not prose.** A list of checks, each with
`passed` and a `note`. A model asked to "assess the DoR" in free text will write
something reassuring. A model asked to fill this shape has to commit to a boolean
per check, and a reviewer can scan the false ones in a second.

**`citations` is part of the artifact.** Not a footnote and not something logged
separately — grounding is data the next stage carries.

Now look at the base class:

```python
def content_hash(self) -> str:
    return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()
```

`canonical_json` sorts keys and strips whitespace, so the same content always
hashes the same regardless of field order. Everything in guide 05 rests on this.

## Step 2 — Read the instructions

Open `src/agentic_sdlc/agents/requirements_agent.py` and read `INSTRUCTIONS`.

Three lines are doing real work, and they are worth arguing about:

> *"Search the corpus before you assert what any standard or checklist requires.
> Never state a rule from memory."*

The model has seen thousands of Definitions of Ready in training. Left alone it
will produce a plausible generic one. This forbids that.

> *"Do not mark a check as passed to make the artifact look finished. A failing
> check with a clear note is far more useful to the reviewer than a false pass."*

Models are agreeable. Without this, the DoR comes back all green every time and
the gate becomes theatre.

> *"Do not design the solution. No components, no technology choices."*

Note that this is belt-and-braces. The real enforcement is that the agent's
search tool cannot reach the architecture standards. **Where you can make
something structurally impossible, do that instead of asking.**

## Step 3 — Build and run it

```bash
python -m agentic_sdlc.cli run INIT-1042 --stop-after requirements
```

The initiative in `data/initiatives/INIT-1042.json` is straight-through
processing for low-risk auto claims — a real-shaped problem with genuine gaps in
it.

You will see the agent call `search_corpus` a few times, then the gate appears.
**Approve it for now** (press `a`, accept your alias, leave the comment empty).
Guide 05 is where the gate gets interesting.

## Step 4 — Read what it produced

```bash
cat .runs/INIT-1042/requirements.json
```

Assess it as a reviewer, not as an author. Specifically:

- **Are the acceptance criteria testable?** Could someone who was not in the room
  execute them and get a pass or fail?
- **Did it find the non-obvious obligations?** The initiative never says
  "explainability", but the standards say automated decisions affecting customers
  carry one. A good run raises it.
- **Are the citations real?** Pick one, open `data/corpus/`, and check the section
  exists and says what the agent claims. Do this at least once. Verifying a
  citation by hand is the fastest way to build or destroy trust in a grounded
  agent.
- **Did any DoR check fail?** A run where all eight pass on this initiative is
  suspicious — it has real gaps.

## Step 5 — Change something and watch it matter

Pick one and try it. This is the most valuable ten minutes of the guide.

**Remove the honesty instruction.** Delete the "do not mark a check as passed"
paragraph and re-run. Watch how much greener the DoR gets.

**Widen the retrieval scope.** Change `DOC_TYPES` to include `"architecture"` and
re-run. Watch requirements start describing components. This is scope drift
arriving through retrieval rather than through instructions, which is why
scoping matters.

**Break the schema.** Add a required field to `SystemRequirements` that the
instructions never mention. See what the model does with it, and what
`ValidationError` you get if it guesses badly.

Put back whichever you changed before moving on.

## Is your output any good?

Compare against [`solutions/expected-run/requirements.json`](../solutions/README.md).
Do not expect a match — models vary, and two analysts would not write the same
requirements either. Look for the same *shape*: acceptance criteria as
given-when-then, thresholds instead of "fast", an honest Definition of Ready
assessment, and the unknown eligibility figure sitting in `open_questions`
rather than quietly invented.

## What you have now

- One agent, complete: scoped retrieval, typed output, constraining instructions
- A validated `SystemRequirements` on disk with a stable content hash
- A feel for which lever — instructions, scope, or schema — moves behaviour

## The pattern, restated

```python
agent = Agent(
    client=FoundryChatClient(project_endpoint=..., model=..., credential=AzureCliCredential()),
    name="RequirementsAgent",
    instructions=INSTRUCTIONS,        # constrain, do not just encourage
    tools=[scoped_search_tool],       # what it may see
)
response = await agent.run(prompt, options={"response_format": SystemRequirements})
artifact = response.value             # validated, or ValidationError
```

Guide 06 builds two more agents from this exact shape.

---

Next: [05 — Build the gate and the audit trail](05-gate-and-audit.md)
