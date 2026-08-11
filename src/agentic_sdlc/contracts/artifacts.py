"""Typed handoff artifacts for the agentic SDLC flow.

Every agent returns one of these models. The orchestrator refuses to advance on
anything that does not validate, so a handoff is a schema check rather than a
hope that the previous agent produced sensible prose.

Schema design note: these models are passed to the model as `response_format`.
Strict structured output requires every field to be present in the payload, so
none of these fields carry defaults or use `| None`. Use an empty string or an
empty list to mean "nothing here".
"""

from __future__ import annotations

import hashlib
import json
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

Stage = Literal[
    "intake",
    "requirements",
    "design",
    "work_breakdown",
    "delivery",
    "release",
]


class Artifact(BaseModel):
    """Base class giving every handoff artifact a stable identity and hash."""

    model_config = ConfigDict(extra="forbid")

    schema_version: ClassVar[str] = "v1"

    @classmethod
    def schema_name(cls) -> str:
        """Identifier recorded on approvals, e.g. ``SystemRequirements@v1``."""
        return f"{cls.__name__}@{cls.schema_version}"

    def canonical_json(self) -> str:
        """Key-sorted, whitespace-free JSON so the hash is reproducible."""
        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def content_hash(self) -> str:
        """SHA-256 of the canonical form. Approvals are bound to this value."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class Citation(Artifact):
    """A grounding hit from the corpus, carried so claims stay traceable."""

    doc_id: str
    title: str
    section: str
    doc_type: Literal["dor", "standards", "architecture", "design_format"]


class Requirement(Artifact):
    id: str = Field(description="Stable id, e.g. FR-01 or NFR-03.")
    statement: str = Field(description="One testable requirement.")
    rationale: str
    acceptance_criteria: list[str]
    priority: Literal["must", "should", "could"]


class DoRCheck(Artifact):
    """One line of the Definition of Ready checklist."""

    name: str
    passed: bool
    note: str


class DoRChecklist(Artifact):
    checks: list[DoRCheck]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def summary(self) -> str:
        passed = sum(1 for check in self.checks if check.passed)
        return f"{passed}/{len(self.checks)}"


class SystemRequirements(Artifact):
    """Output of the Requirements Agent. Gated before Design may run."""

    initiative_id: str
    title: str
    functional: list[Requirement]
    non_functional: list[Requirement]
    definition_of_ready: DoRChecklist
    citations: list[Citation]
    open_questions: list[str]


class DesignComponent(Artifact):
    name: str
    responsibility: str
    depends_on: list[str]


class DesignDecision(Artifact):
    """A decision worth defending later, in the spirit of a lightweight ADR."""

    decision: str
    rationale: str
    alternatives_considered: list[str]


class DesignArtifact(Artifact):
    """Output of the Design Agent. Gated before Work Breakdown may run."""

    initiative_id: str
    overview: str
    components: list[DesignComponent]
    data_flows: list[str]
    decisions: list[DesignDecision]
    risks: list[str]
    citations: list[Citation]


class TestCase(Artifact):
    id: str
    story_id: str
    given_when_then: str
    kind: Literal["unit", "integration", "e2e"]


class Story(Artifact):
    id: str
    epic_id: str
    title: str
    description: str
    acceptance_criteria: list[str]
    estimate_points: int
    depends_on: list[str]


class Epic(Artifact):
    id: str
    title: str
    outcome: str


class WorkBreakdown(Artifact):
    """Output of the Work Breakdown Agent. Written to Jira via MCP."""

    initiative_id: str
    epics: list[Epic]
    stories: list[Story]
    test_cases: list[TestCase]
    sequencing_notes: list[str]


class PullRequest(Artifact):
    """Output of the Delivery Agent (take-home)."""

    initiative_id: str
    story_id: str
    branch: str
    title: str
    description: str
    files_changed: list[str]
    tests_added: list[str]
    pr_url: str


class ReleasePackage(Artifact):
    """Output of the Release Agent (take-home)."""

    initiative_id: str
    version: str
    included_pr_urls: list[str]
    release_notes: str
    confluence_url: str


class NeedsClarification(Artifact):
    """Escalation path: an agent asks rather than guesses.

    Returned instead of a stage artifact when the agent cannot proceed on the
    evidence available. The orchestrator surfaces the question to a human.
    """

    initiative_id: str
    stage: Stage
    question: str
    why_it_blocks: str
    options_considered: list[str]


#: Which artifact each stage is contractually required to produce.
STAGE_ARTIFACTS: dict[Stage, type[Artifact]] = {
    "requirements": SystemRequirements,
    "design": DesignArtifact,
    "work_breakdown": WorkBreakdown,
    "delivery": PullRequest,
    "release": ReleasePackage,
}
