"""Regenerate the reference run in `solutions/expected-run/`.

The artifacts here are hand-written rather than model-generated, so the reference
does not drift when a model version changes. They are built through the real
contract classes and hashed with the real hashing code, which means the sample
`audit.jsonl` genuinely covers the sample artifacts — `tests/test_expected_run.py`
checks exactly that.

    python solutions/make_expected_run.py

Edit the artifacts below and re-run; the hashes follow.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from agentic_sdlc.contracts.approval import ApprovalRecord
from agentic_sdlc.contracts.artifacts import (
    Artifact,
    Citation,
    DesignArtifact,
    DesignComponent,
    DesignDecision,
    DoRCheck,
    DoRChecklist,
    Epic,
    Requirement,
    Story,
    SystemRequirements,
    TestCase,
    WorkBreakdown,
)

OUT = Path(__file__).parent / "expected-run"
APPROVER = "reference"
MODEL = "gpt-4o-mini"

DOR = Citation(doc_id="DOR-CHECKLIST", title="Definition of Ready", section="", doc_type="dor")
STANDARDS = Citation(
    doc_id="DELIVERY-STANDARDS", title="Delivery Standards", section="", doc_type="standards"
)
ARCH = Citation(
    doc_id="ARCH-STANDARDS", title="Architecture Standards", section="", doc_type="architecture"
)
FORMAT = Citation(
    doc_id="DESIGN-FORMAT", title="Design Format", section="", doc_type="design_format"
)


def cite(base: Citation, section: str) -> Citation:
    return base.model_copy(update={"section": section})


REQUIREMENTS = SystemRequirements(
    initiative_id="INIT-1042",
    title="Straight-through processing for low-risk auto claims",
    functional=[
        Requirement(
            id="FR-01",
            statement=(
                "The system evaluates every incoming auto claim against a published "
                "eligibility rule set and records an eligible or not-eligible outcome "
                "with the identifier and version of the rule set applied."
            ),
            rationale=(
                "Straight-through processing only applies to a defined subset of claims, "
                "and which subset must be reconstructable after the fact."
            ),
            acceptance_criteria=[
                "Given a claim meeting every eligibility condition, when it is evaluated, then the outcome is eligible and the rule set version is recorded.",
                "Given a claim failing any single condition, when it is evaluated, then the outcome is not-eligible and the failing condition is named.",
                "Given a rule set version change, when a previously evaluated claim is re-examined, then the original evaluation retains the version applied at the time.",
            ],
            priority="must",
        ),
        Requirement(
            id="FR-02",
            statement=(
                "An eligible claim is settled without adjuster involvement by instructing "
                "the existing payments service, and the claim is closed in the intake "
                "system of record."
            ),
            rationale=(
                "The measured outcome is settlement time, which is only reduced when the "
                "path completes end to end without a manual step."
            ),
            acceptance_criteria=[
                "Given an eligible claim, when automated settlement runs, then a payment instruction is issued to the payments service and no adjuster task is created.",
                "Given a successful payment instruction, when it is acknowledged, then the claim is closed in the intake system with the settlement amount and timestamp.",
                "Given a payment instruction that fails or is not acknowledged, when the retry allowance is exhausted, then the claim is routed to an adjuster and remains open.",
            ],
            priority="must",
        ),
        Requirement(
            id="FR-03",
            statement=(
                "A claim that is not eligible, or whose automated assessment cannot be "
                "completed, is routed to the existing adjuster queue with the reason "
                "attached."
            ),
            rationale=(
                "The initiative removes routine work from the queue; it must not remove "
                "claims from the queue that still need judgement."
            ),
            acceptance_criteria=[
                "Given a not-eligible claim, when routing runs, then it appears in the adjuster queue with the failing condition visible.",
                "Given an assessment that errors, when routing runs, then the claim is queued for an adjuster rather than retried indefinitely or dropped.",
            ],
            priority="must",
        ),
        Requirement(
            id="FR-04",
            statement=(
                "An adjuster can review any automated settlement decision and override it, "
                "and the override is recorded with the adjuster identity, timestamp, and "
                "stated reason."
            ),
            rationale=(
                "Named constraint from the requester, and the control that makes automated "
                "settlement acceptable to operations."
            ),
            acceptance_criteria=[
                "Given a settled claim, when an adjuster opens it, then the decision, the inputs used, and the rule set version are visible.",
                "Given an adjuster override, when it is submitted, then the original decision is retained alongside the override rather than replaced.",
                "Given an override with no stated reason, when it is submitted, then it is rejected.",
            ],
            priority="must",
        ),
        Requirement(
            id="FR-05",
            statement=(
                "Every automated decision produces a customer-facing explanation naming the "
                "factors that determined the outcome."
            ),
            rationale=(
                "DoR-06 requires automated decisions affecting a customer outcome to carry "
                "an explainability obligation stated as a requirement."
            ),
            acceptance_criteria=[
                "Given an automated settlement, when the explanation is generated, then it names each factor that determined the outcome in non-technical language.",
                "Given an explanation, when it is retrieved for a closed claim, then it matches the decision as originally made.",
            ],
            priority="must",
        ),
    ],
    non_functional=[
        Requirement(
            id="NFR-01",
            statement=(
                "Claims data and customer personal information are stored and processed "
                "only in the country of operation, including backups and logs."
            ),
            rationale="Named constraint from the requester; DoR-05 data handling.",
            acceptance_criteria=[
                "Given every service and store in the solution, when their regions are inspected, then all are in-country.",
                "Given diagnostic logs, when inspected, then they contain no customer personal information.",
            ],
            priority="must",
        ),
        Requirement(
            id="NFR-02",
            statement=(
                "Each automated decision retains its inputs, the rule set version, the "
                "outcome, and the explanation for the statutory retention period, in a form "
                "that cannot be altered after the fact."
            ),
            rationale="DoR-05 auditability; a decision that cannot be reconstructed cannot be defended.",
            acceptance_criteria=[
                "Given a decision recorded 24 months ago, when it is retrieved, then inputs, rule set version, outcome, and explanation are all present.",
                "Given an attempt to modify a recorded decision, when it is made, then it is rejected and the attempt is logged.",
            ],
            priority="must",
        ),
        Requirement(
            id="NFR-03",
            statement=(
                "Eligibility assessment completes within 5 seconds at the 95th percentile "
                "for the expected daily volume."
            ),
            rationale="DoR-04 requires a threshold; a settlement path with no latency bound cannot be tested.",
            acceptance_criteria=[
                "Given expected peak daily volume, when load is applied, then p95 assessment latency is at or below 5 seconds.",
            ],
            priority="should",
        ),
        Requirement(
            id="NFR-04",
            statement=(
                "When the eligibility service or the payments service is unavailable, claims "
                "are routed to adjusters and no claim is left in an indeterminate state."
            ),
            rationale="DoR-05 degradation behaviour; the safe failure mode is the path that exists today.",
            acceptance_criteria=[
                "Given the payments service is unavailable, when claims arrive, then they are queued for adjusters and remain open.",
                "Given recovery, when the service returns, then no claim has been both queued and settled.",
            ],
            priority="must",
        ),
        Requirement(
            id="NFR-05",
            statement=(
                "Only holders of the adjuster role may override an automated decision, and "
                "only holders of the rules administrator role may change the rule set."
            ),
            rationale="DoR-05 access control; the rule set is the control surface for the whole capability.",
            acceptance_criteria=[
                "Given a user without the adjuster role, when they attempt an override, then it is denied and logged.",
                "Given a rule set change, when it is submitted, then the submitting identity and the prior version are recorded.",
            ],
            priority="must",
        ),
    ],
    definition_of_ready=DoRChecklist(
        checks=[
            DoRCheck(
                name="DoR-01 Business outcome is stated",
                passed=True,
                note="Outcome stated as faster settlement on simple claims and fewer routine items in the adjuster queue, not as a proposed solution.",
            ),
            DoRCheck(
                name="DoR-02 Success is measurable",
                passed=True,
                note="Median settlement time 6 days to under 1 day; 40 percent straight-through within two quarters; no increase in reopened settlements. All have direction and baseline.",
            ),
            DoRCheck(
                name="DoR-03 Scope boundaries are explicit",
                passed=False,
                note="In scope is clear. Exclusions are not stated: whether claim types beyond auto, and whether partial settlements, are excluded is unrecorded. Owner: VP Claims Operations.",
            ),
            DoRCheck(
                name="DoR-04 Every requirement is individually testable",
                passed=True,
                note="Each requirement carries given-when-then acceptance criteria; the latency requirement carries a threshold rather than 'fast'.",
            ),
            DoRCheck(
                name="DoR-05 Non-functional requirements are covered",
                passed=True,
                note="Data handling NFR-01, auditability NFR-02, performance NFR-03, availability NFR-04, access control NFR-05.",
            ),
            DoRCheck(
                name="DoR-06 Regulatory and compliance obligations are identified",
                passed=True,
                note="Automated decisions affect a customer outcome, so the explainability obligation is stated as FR-05 rather than left as context. Data residency stated as NFR-01.",
            ),
            DoRCheck(
                name="DoR-07 Dependencies and assumptions are recorded",
                passed=True,
                note="Depends on the claims intake system as system of record and the existing payments service, both named as constraints. Assumes the current adjuster queue is reusable.",
            ),
            DoRCheck(
                name="DoR-08 Open questions are listed, not resolved by assumption",
                passed=False,
                note="The eligibility threshold is unknown and is recorded as an open question rather than assumed, but the retention period is also unconfirmed and needs an owner named.",
            ),
        ]
    ),
    citations=[
        cite(DOR, "DoR-04 Every requirement is individually testable"),
        cite(DOR, "DoR-05 Non-functional requirements are covered"),
        cite(DOR, "DoR-06 Regulatory and compliance obligations are identified"),
        cite(STANDARDS, "STD-04 Acceptance criteria"),
        cite(STANDARDS, "STD-06 Automated decisions"),
        cite(STANDARDS, "STD-08 Audit records"),
    ],
    open_questions=[
        "What claim value and complexity define 'low risk'? The requester says 'below a modest value' without a figure, and the eligibility rule set cannot be written without it. Owner: VP Claims Operations.",
        "What is the statutory retention period for automated decision records in the country of operation? NFR-02 states the obligation but not the duration. Owner: Compliance.",
        "Are partial settlements in scope, or only claims settled in full? Affects FR-02 and the payments integration.",
        "Does an automated settlement require customer acceptance before payment is issued, or is notification sufficient?",
    ],
)

DESIGN = DesignArtifact(
    initiative_id="INIT-1042",
    overview=(
        "Claims arrive in the existing intake system, which remains the system of record. "
        "An eligibility service subscribes to claim-received events, evaluates the claim "
        "against a versioned rule set, and emits an assessment. Eligible claims go to a "
        "settlement service that instructs the existing payments service and writes the "
        "closure back to intake. Anything not eligible, and anything that errors, is routed "
        "to the adjuster queue that exists today. Every assessment and settlement is written "
        "to an append-only decision store that also serves the adjuster review and override "
        "path. No component replaces an existing system; the design adds an automated lane "
        "beside the manual one and falls back to it."
    ),
    components=[
        DesignComponent(
            name="Eligibility Service",
            responsibility=(
                "Evaluates a claim against the active rule set version and emits an "
                "assessment with the outcome, the factors that determined it, and the "
                "rule set version applied. Stateless; the rule set is loaded from the "
                "rule set store."
            ),
            depends_on=["Claims Intake (existing)", "Rule Set Store", "Decision Store"],
        ),
        DesignComponent(
            name="Rule Set Store",
            responsibility=(
                "Holds versioned, immutable eligibility rule sets. A change publishes a new "
                "version rather than mutating the active one, so historical assessments stay "
                "reconstructable."
            ),
            depends_on=[],
        ),
        DesignComponent(
            name="Settlement Orchestrator",
            responsibility=(
                "Drives an eligible claim to closure: instructs the payments service, waits "
                "for acknowledgement, writes closure back to intake, and routes to the "
                "adjuster queue when any step fails. Owns the idempotency key so a retry "
                "cannot double-pay."
            ),
            depends_on=[
                "Payments Service (existing)",
                "Claims Intake (existing)",
                "Decision Store",
                "Adjuster Queue (existing)",
            ],
        ),
        DesignComponent(
            name="Decision Store",
            responsibility=(
                "Append-only record of every assessment, settlement, explanation, and "
                "override. Written once, never updated. Serves the adjuster review view and "
                "the retention obligation."
            ),
            depends_on=[],
        ),
        DesignComponent(
            name="Explanation Generator",
            responsibility=(
                "Renders the factors from an assessment into customer-facing language. "
                "Deterministic template over the recorded factors, so the explanation cannot "
                "drift from the decision it describes."
            ),
            depends_on=["Decision Store"],
        ),
        DesignComponent(
            name="Adjuster Review View",
            responsibility=(
                "Shows an adjuster the decision, its inputs, the rule set version, and the "
                "explanation, and accepts an override with a mandatory reason. Writes the "
                "override as a new decision record rather than editing the original."
            ),
            depends_on=["Decision Store", "Claims Intake (existing)"],
        ),
    ],
    data_flows=[
        "Claims Intake emits claim-received; Eligibility Service consumes it, evaluates against the active rule set, writes the assessment to the Decision Store, and emits assessment-completed.",
        "Settlement Orchestrator consumes assessment-completed where the outcome is eligible, calls the Payments Service with an idempotency key derived from the claim id and assessment id, and on acknowledgement writes closure to Claims Intake and a settlement record to the Decision Store.",
        "Assessments that are not eligible, and settlement attempts that exhaust their retry allowance, are published to the existing Adjuster Queue with the failing condition or failure reason attached.",
        "Adjuster Review View reads from the Decision Store; an override writes a new decision record referencing the original and updates the claim in Claims Intake.",
        "All personal information stays within in-country stores; events carry claim identifiers rather than claimant detail.",
    ],
    decisions=[
        DesignDecision(
            decision=(
                "Evaluate eligibility with an explicit versioned rule set rather than a "
                "learned model."
            ),
            rationale=(
                "FR-05 and DoR-06 require an explanation naming the factors that determined "
                "the outcome, and NFR-02 requires the decision to be reconstructable years "
                "later. A rule set gives both by construction. It also gives operations a "
                "control surface they can reason about when tuning the eligible share "
                "towards the 40 percent measure."
            ),
            alternatives_considered=[
                "Trained classifier with feature attribution: better ceiling on eligible volume, but explanation quality becomes a modelling problem and retraining breaks reconstructability.",
                "Adjuster-defined heuristics held in the intake system: no new component, but no versioning and no decision record.",
            ],
        ),
        DesignDecision(
            decision=(
                "Add an automated lane alongside the existing manual path rather than "
                "modifying the intake system."
            ),
            rationale=(
                "The requester named intake as the unchangeable system of record. Keeping "
                "the manual path intact also makes the failure mode trivial: when anything "
                "in the automated lane is unavailable, claims follow the path they follow "
                "today, satisfying NFR-04."
            ),
            alternatives_considered=[
                "Extend the intake system directly: fewer moving parts, but violates a stated constraint and couples release cadence to the system of record.",
            ],
        ),
        DesignDecision(
            decision=(
                "Make the Decision Store append-only, with overrides recorded as new entries "
                "referencing the original."
            ),
            rationale=(
                "NFR-02 requires records that cannot be altered after the fact, and FR-04 "
                "requires the original decision to survive an override. One property gives "
                "both, and it removes the question of who may edit history."
            ),
            alternatives_considered=[
                "Mutable records with an audit column: familiar, but the audit trail then depends on application code being correct forever.",
            ],
        ),
        DesignDecision(
            decision=(
                "Derive the payments idempotency key from claim id plus assessment id and "
                "own it in the Settlement Orchestrator."
            ),
            rationale=(
                "The only unrecoverable failure in this design is paying twice. Binding the "
                "key to the assessment means a retry of the same decision is idempotent while "
                "a genuinely new assessment is not."
            ),
            alternatives_considered=[
                "Rely on the payments service to deduplicate: outside our control and untestable from here.",
            ],
        ),
    ],
    risks=[
        "The eligibility threshold is still an open question from requirements. The rule set store and its schema can be built without it, but the initial rule set cannot be authored, and the 40 percent measure cannot be forecast.",
        "The retry allowance in the Settlement Orchestrator trades settlement latency against adjuster queue volume; the value needs an operational decision before load testing means anything.",
        "The existing payments service acknowledgement semantics are assumed to be synchronous. If acknowledgement is asynchronous, the Settlement Orchestrator needs a reconciliation path and this design understates its complexity.",
        "Explanation quality is only as good as the factor names in the rule set. Poorly named conditions produce technically correct explanations that no customer can act on.",
    ],
    citations=[
        cite(ARCH, "ARC-03 Data residency"),
        cite(ARCH, "ARC-05 Auditability of automated decisions"),
        cite(ARCH, "ARC-06 Integration style"),
        cite(ARCH, "ARC-07 Degradation"),
        cite(FORMAT, "FMT-04 Decisions"),
    ],
)

BREAKDOWN = WorkBreakdown(
    initiative_id="INIT-1042",
    epics=[
        Epic(
            id="EPIC-001",
            title="Eligibility assessment",
            outcome="Every incoming auto claim receives a recorded, versioned eligibility outcome.",
        ),
        Epic(
            id="EPIC-002",
            title="Automated settlement",
            outcome="Eligible claims settle through the existing payments service and close in intake without an adjuster.",
        ),
        Epic(
            id="EPIC-003",
            title="Decision record, explanation, and adjuster override",
            outcome="Every automated decision is explainable, reconstructable, and reversible by an adjuster.",
        ),
    ],
    stories=[
        Story(
            id="STORY-001",
            epic_id="EPIC-001",
            title="Versioned rule set store",
            description="Persist eligibility rule sets as immutable versions, with the active version selectable and prior versions retrievable by id.",
            acceptance_criteria=[
                "Publishing a rule set creates a new version and leaves prior versions unchanged.",
                "The active version is resolvable at assessment time.",
                "A prior version is retrievable by id for reconstruction.",
            ],
            estimate_points=5,
            depends_on=[],
        ),
        Story(
            id="STORY-002",
            epic_id="EPIC-001",
            title="Evaluate a claim against the active rule set",
            description="Consume claim-received, evaluate against the active rule set, and emit an assessment carrying the outcome, the determining factors, and the rule set version.",
            acceptance_criteria=[
                "A claim meeting all conditions is assessed eligible with the rule set version recorded.",
                "A claim failing a condition is assessed not-eligible with the failing condition named.",
                "The assessment is written to the decision store before the event is emitted.",
            ],
            estimate_points=8,
            depends_on=["STORY-001", "STORY-005"],
        ),
        Story(
            id="STORY-003",
            epic_id="EPIC-002",
            title="Instruct payment for an eligible claim",
            description="Call the existing payments service with an idempotency key derived from claim id and assessment id, and record the instruction.",
            acceptance_criteria=[
                "An eligible assessment produces exactly one payment instruction.",
                "Replaying the same assessment produces no second instruction.",
                "The instruction and its acknowledgement are recorded in the decision store.",
            ],
            estimate_points=8,
            depends_on=["STORY-002"],
        ),
        Story(
            id="STORY-004",
            epic_id="EPIC-002",
            title="Close the claim in intake, or route to an adjuster",
            description="On acknowledgement, write closure back to the intake system. On exhausted retries or an error, route the claim to the existing adjuster queue with the reason attached.",
            acceptance_criteria=[
                "An acknowledged payment closes the claim in intake with amount and timestamp.",
                "An exhausted retry allowance queues the claim for an adjuster and leaves it open.",
                "No claim is both queued and settled.",
            ],
            estimate_points=5,
            depends_on=["STORY-003"],
        ),
        Story(
            id="STORY-005",
            epic_id="EPIC-003",
            title="Append-only decision store",
            description="Write-once store for assessments, settlements, explanations, and overrides, with retrieval by claim id.",
            acceptance_criteria=[
                "A written record cannot be updated or deleted; attempts are rejected and logged.",
                "All records for a claim are retrievable in order.",
                "Records carry the rule set version and the identity that produced them.",
            ],
            estimate_points=8,
            depends_on=[],
        ),
        Story(
            id="STORY-006",
            epic_id="EPIC-003",
            title="Customer-facing explanation",
            description="Render the determining factors from an assessment into non-technical language using a deterministic template.",
            acceptance_criteria=[
                "Every automated decision has an explanation naming each determining factor.",
                "The explanation for a closed claim matches the decision as originally made.",
            ],
            estimate_points=3,
            depends_on=["STORY-002", "STORY-005"],
        ),
        Story(
            id="STORY-007",
            epic_id="EPIC-003",
            title="Adjuster review and override",
            description="Show the decision, inputs, rule set version, and explanation to an adjuster, and accept an override with a mandatory reason recorded as a new decision record.",
            acceptance_criteria=[
                "An adjuster can see the inputs and rule set version behind any automated decision.",
                "An override without a reason is rejected.",
                "An override is written as a new record and the original is retained.",
                "A user without the adjuster role cannot override, and the attempt is logged.",
            ],
            estimate_points=8,
            depends_on=["STORY-005", "STORY-006"],
        ),
    ],
    test_cases=[
        TestCase(
            id="TEST-001",
            story_id="STORY-001",
            given_when_then="Given an active rule set v3, when v4 is published, then v3 remains retrievable by id and unchanged.",
            kind="unit",
        ),
        TestCase(
            id="TEST-002",
            story_id="STORY-002",
            given_when_then="Given a claim below threshold with no injury flag, when it is evaluated, then the outcome is eligible and the rule set version is recorded on the assessment.",
            kind="integration",
        ),
        TestCase(
            id="TEST-003",
            story_id="STORY-002",
            given_when_then="Given a claim with an injury flag, when it is evaluated, then the outcome is not-eligible and the injury condition is named as the failing condition.",
            kind="unit",
        ),
        TestCase(
            id="TEST-004",
            story_id="STORY-003",
            given_when_then="Given an assessment already settled, when the same assessment is replayed, then no second payment instruction is issued.",
            kind="integration",
        ),
        TestCase(
            id="TEST-005",
            story_id="STORY-004",
            given_when_then="Given the payments service is unavailable, when settlement is attempted until retries are exhausted, then the claim appears in the adjuster queue and remains open.",
            kind="integration",
        ),
        TestCase(
            id="TEST-006",
            story_id="STORY-005",
            given_when_then="Given a written decision record, when an update is attempted, then it is rejected and the attempt is logged.",
            kind="unit",
        ),
        TestCase(
            id="TEST-007",
            story_id="STORY-007",
            given_when_then="Given a settled claim, when an adjuster overrides with a reason, then a new record is written, the original is retained, and the claim reflects the override.",
            kind="e2e",
        ),
        TestCase(
            id="TEST-008",
            story_id="STORY-007",
            given_when_then="Given a user without the adjuster role, when they attempt an override, then it is denied and the attempt is logged.",
            kind="integration",
        ),
    ],
    sequencing_notes=[
        "STORY-001 and STORY-005 have no dependencies and unblock everything else; start both.",
        "STORY-002 needs the decision store before it can record an assessment, so it follows STORY-005 rather than running beside it.",
        "STORY-003 and STORY-004 are the only stories that touch money; keep them in one pair's hands and review them together.",
        "STORY-007 is last because it needs real records to review, and it is the story most likely to change after adjusters see it.",
        "The initial rule set content is blocked on the eligibility threshold open question. Every story above is buildable without it; only the authored rules are blocked.",
    ],
)

STAGES: list[tuple[str, Artifact, str]] = [
    ("requirements->design", REQUIREMENTS, "Two DoR failures accepted knowingly; thresholds tracked as open questions rather than assumed."),
    ("design->work_breakdown", DESIGN, "Fallback to the manual path is the right failure mode. Confirm payments acknowledgement semantics before build."),
    ("work_breakdown->delivery", BREAKDOWN, "Sequencing holds. Rule authoring stays blocked on the threshold question."),
]

FILENAMES = {
    "requirements->design": "requirements.json",
    "design->work_breakdown": "design.json",
    "work_breakdown->delivery": "work_breakdown.json",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = datetime(2026, 3, 4, 15, 12, 0, tzinfo=UTC)
    lines: list[str] = []

    for index, (stage, artifact, comment) in enumerate(STAGES):
        path = OUT / FILENAMES[stage]
        path.write_text(
            json.dumps(artifact.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        record = ApprovalRecord(
            audit_id=f"aprv_ref{index + 1:09d}",
            initiative_id="INIT-1042",
            stage=stage,
            decision="approved",
            approver=APPROVER,
            comment=comment,
            artifact_schema=artifact.schema_name(),
            artifact_hash=artifact.content_hash(),
            model=MODEL,
            edited=False,
            timestamp=base.replace(minute=base.minute + index * 9),
        )
        lines.append(record.to_json_line())
        print(f"{path.name:22} {artifact.schema_name():24} {artifact.content_hash()[:12]}...")

    (OUT / "audit.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{'audit.jsonl':22} {len(lines)} approval records")


if __name__ == "__main__":
    main()
