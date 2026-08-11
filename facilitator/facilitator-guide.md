# Facilitator guide

For whoever is running the two hours.

## The one thing to get right

**Guide 05, step 6 — the tamper demonstration.** If people leave remembering one
thing, it should be watching an approval stop applying because someone changed
what it approved. Protect the time for it. If you are running late, cut depth
from guide 06 rather than shortening guide 05.

## Timing

| Guide | Clock | Buffer? | Notes |
|---|---|---|---|
| 01 Resources | 0–12 | tight | Search `--no-wait` must go first, minute one |
| 02 Models | 12–20 | some | Runs while Search provisions |
| 03 Index | 20–28 | some | Search must be `running` by now |
| 04 Requirements Agent | 28–50 | **yes, ~7 min** | The pattern guide; let step 5 run long if it is landing |
| 05 Gate and audit | 50–75 | **protect this** | The centre of the workshop |
| 06 Design + Breakdown | 75–100 | **cut here first** | Design is a re-run of a known pattern |
| 07 Orchestrate + observe | 100–115 | flexible | Tracing is optional; drop it freely |
| 08 Wrap up | 115–120 | — | Point at the take-home |

## Before the session

**Two weeks out.** Send [the pre-reading](../docs/pre-reading.md). The live time
assumes it has been read. Confirm every attendee can create a resource group and
an Azure AI Search service in the target subscription — this is the single most
common blocker and it is unfixable on the day.

**One week out.** Ask people to complete [guide 00](../workshop/00-prerequisites.md)
and to send you the output of `python -m pytest -q`. A green suite proves Python,
the virtual environment, the package install, and the mock servers all work. Then
the only thing that can fail live is Azure configuration.

**The day before.** Run the whole workshop yourself against a fresh subscription.
Check quota for your chosen chat model in the region you are recommending —
capacity varies and a region that worked last month may not today.

**Have ready:** a resource group you have pre-provisioned so you can demo from a
working environment if someone's tenant misbehaves, and the answer to "can we
use our own subscription" (usually yes, but role assignment in step 3 of guide 01
is where corporate tenants say no).

`infra/setup.ps1 -Alias demo` (or `infra/setup.sh demo`) provisions everything in
guides 01 and 02 and prints a ready-to-paste `.env`, which is the fastest way to
build that fallback environment. Do not hand it to attendees — creating the
resources by hand is how they learn what exists.

## Where people get stuck

**Guide 01, role assignment.** Many corporate tenants block self-assignment. Know
in advance whether attendees can run `az role assignment create`, and if not, get
the role granted at the resource group level beforehand.

**Guide 02, two endpoints.** `.services.ai.azure.com` for the project and
`.openai.azure.com` for embeddings, on the same resource. This looks like a
mistake and gets "corrected" into a single value. Call it out explicitly.

**Guide 03, empty results.** Almost always the index ran before Search finished
provisioning. `python -m agentic_sdlc.cli index --recreate` fixes it.

**Guide 05, "so what".** Some people do not immediately see why hash-binding
matters. The unlock is asking them: *"your change advisory board approved a
design last Tuesday. How do you prove the thing that shipped is the thing they
approved?"* Then run `tamper`.

**Guide 06, tool approval versus stage gate.** The most common conceptual
confusion in the workshop. Draw the distinction on a whiteboard before running
it: one approves an artifact between agents, the other approves a single write.

## Discussion prompts that work

Use these when a run is executing and you have thirty seconds of dead air.

- *"Which of these gates would your organisation actually staff? What happens to
  the ones nobody has time for?"* — surfaces that a gate nobody attends is worse
  than no gate.
- *"The Requirements Agent cannot see the architecture standards. Where else in
  your architecture are you asking a model not to do something you could make
  impossible?"*
- *"If this agent produced that requirements set and a human approved it in
  forty seconds, was that a gate or a rubber stamp? What would make it real?"*
- *"What is the smallest slice of this you could put in front of a real team next
  quarter?"* — good closer, gets them to a concrete next step.

## Adapting the session

**Shorter (90 min):** Guides 01 to 05 only. Stop after the tamper demonstration
and describe guide 06. The core lesson survives intact.

**Longer (half day):** Add take-home 3 (clarification and escalation) live — it
is the richest discussion — and take-home 5 (evaluation).

**Larger group (>12):** Pair people up. One drives, one reviews at the gate. The
reviewer role is genuinely useful here, and it halves the number of subscriptions
that can go wrong.

**No subscription available:** `python -m pytest -q`, a code read-through, and a
walk through [`solutions/`](../solutions/README.md) still convey the contracts,
the gate, and the audit trail. The reference run even lets you do the tamper
lesson — `tests/test_expected_run.py` runs it against real artifacts and a real
approval trail. You lose the agents, which is a real loss, but the governance
model is the transferable part.

## Cost

One Azure AI Search Basic service per attendee, roughly seventy-five dollars a
month while it exists. Model usage over two hours is cents. **Chase the cleanup**
a week later — this is the cost that lingers, and everything lives in one
resource group precisely so the delete is trivial.
