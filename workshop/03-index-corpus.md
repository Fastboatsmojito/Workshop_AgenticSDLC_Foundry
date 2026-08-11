# 03 — Index the governance corpus (20–28 min)

Agents that assert what a standard requires, from memory, are worse than useless
in a regulated setting — they are confidently wrong in a way nobody can trace.
So the corpus goes into Azure AI Search, agents retrieve from it, and every claim
they make carries a citation.

## What is in the corpus

Four fictional but realistic documents in `data/corpus/`:

| Document | `doc_type` | Who may retrieve it |
|---|---|---|
| Definition of Ready | `dor` | Requirements Agent |
| Delivery Standards | `standards` | Requirements Agent, Work Breakdown Agent |
| Architecture Standards | `architecture` | Design Agent |
| Design Format | `design_format` | Design Agent |

One index, one filterable `doc_type` field, and each agent gets a search tool
scoped to its own slice. The Requirements Agent literally cannot retrieve the
architecture standards, so it cannot drift into designing the solution.

**That scoping is a design decision, not an instruction.** Telling a model "do
not design the solution" is a hope. Not giving it the architecture standards is a
constraint.

## Step 1 — Build the index and load the corpus

```bash
python -m agentic_sdlc.cli index
```

This creates the index and then chunks, embeds, and uploads the corpus. Expect
roughly forty to sixty chunks and about thirty seconds.

If the command reports the service is still provisioning, wait a minute and run
it again. If you need to start over: `python -m agentic_sdlc.cli index --recreate`.

## Step 2 — Look at what you just built

Open `src/agentic_sdlc/grounding/index.py`. Three things are worth your
attention as an architect:

**The vector field.** `content_vector` carries 1536 dimensions with an HNSW
profile. This is what makes paraphrased questions work.

**The filterable `doc_type`.** This single field is what makes per-agent scoping
possible without a separate index per agent — cheaper to build, and one place to
reason about retrieval.

**The semantic configuration.** Defined but not used by default. It is there so
you can turn on semantic ranking later without rebuilding the index.

Then open `src/agentic_sdlc/grounding/ingest.py`. Chunking splits on level-2
headings and only falls back to paragraph splitting when a section runs long.
That is deliberate: heading-aligned chunks mean a citation can name a real
section like `DoR-06`, which a human can go and check. Chunking on a fixed
character count would give you citations nobody can verify.

## Step 3 — See hybrid retrieval work

`scripts/try_search.py` builds a search tool scoped to the Definition of Ready
(`doc_types=["dor"]`) — the same scope the Requirements Agent gets — and runs
one query through it. The question deliberately does not reuse the wording in
the document:

```bash
python scripts/try_search.py "what happens if we are unsure whether a rule applies to us?"
```

You should get `DoR-06` and `DoR-08` back, even though your question shares
almost no vocabulary with them. That is the vector half of the hybrid query. The
keyword half is what catches an exact search for "DoR-06".

Now try the scoping, with the same DoR-only tool:

```bash
python scripts/try_search.py "what are the data residency requirements?"
```

Data residency lives in the architecture standards, which this tool cannot see.
You get the honest "no matching passages" response instead of a confident answer
assembled from the wrong document. Worth watching, because this is what scoping
buys you.

## What you have now

- A hybrid vector index over four governance documents
- A search tool factory that scopes retrieval per agent
- Evidence that scoping works, and that a scoped miss fails loudly

---

Next: [04 — Build the Requirements Agent](04-requirements-agent.md)
