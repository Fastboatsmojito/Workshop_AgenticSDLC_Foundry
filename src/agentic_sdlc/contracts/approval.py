"""The approval record and the rules that make it binding.

An approval is only meaningful if you can say *what* was approved. Every record
stores the SHA-256 of the exact artifact it covers, so mutating an artifact
after sign-off silently invalidates the approval instead of quietly riding on
it. `ApprovalRegistry.assert_approved` is the check the orchestrator runs before
each handoff.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agentic_sdlc.contracts.artifacts import Artifact

Decision = Literal["approved", "rejected"]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ApprovalRecord(BaseModel):
    """One human decision at one stage boundary."""

    model_config = ConfigDict(extra="forbid")

    audit_id: str = Field(default_factory=lambda: f"aprv_{uuid.uuid4().hex[:12]}")
    initiative_id: str
    stage: str = Field(description="Boundary being crossed, e.g. requirements->design.")
    decision: Decision
    approver: str
    comment: str = ""
    artifact_schema: str = Field(description="e.g. SystemRequirements@v1")
    artifact_hash: str = Field(description="SHA-256 of the approved artifact.")
    model: str = Field(default="", description="Model deployment that produced the artifact.")
    edited: bool = Field(default=False, description="True when the human changed the artifact before approving.")
    timestamp: datetime = Field(default_factory=_utc_now)

    def covers(self, artifact: Artifact) -> bool:
        """True when this record was issued for exactly this artifact content."""
        return (
            self.decision == "approved"
            and self.artifact_schema == artifact.schema_name()
            and self.artifact_hash == artifact.content_hash()
        )

    def to_json_line(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)

    def render(self) -> str:
        icon = "APPROVED" if self.decision == "approved" else "REJECTED"
        edited = " (edited)" if self.edited else ""
        return (
            f"{icon}{edited} by {self.approver} at {self.timestamp.isoformat()}\n"
            f"  stage:    {self.stage}\n"
            f"  artifact: {self.artifact_schema}  hash {self.artifact_hash[:12]}...\n"
            f"  audit id: {self.audit_id}"
        )


class ApprovalDenied(Exception):
    """Raised when a handoff is attempted without a valid approval.

    This is what turns the gate from a printed message into control flow: the
    orchestrator cannot reach the next agent while this is in flight.
    """


class ApprovalRegistry:
    """Append-only store of approval records, backed by a JSONL file.

    Append-only on purpose. A gate you can quietly rewrite is not a gate, and
    participants can `cat` the file to see the trail for themselves.
    """

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: ApprovalRecord) -> ApprovalRecord:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(record.to_json_line() + "\n")
        return record

    def all(self) -> list[ApprovalRecord]:
        if not self.path.exists():
            return []
        records: list[ApprovalRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(ApprovalRecord.model_validate_json(line))
        return records

    def find_approval(self, stage: str, artifact: Artifact) -> ApprovalRecord | None:
        """Most recent approval issued for this exact artifact at this stage."""
        for record in reversed(self.all()):
            if record.stage == stage and record.covers(artifact):
                return record
        return None

    def assert_approved(self, stage: str, artifact: Artifact) -> ApprovalRecord:
        """Gate check run before every handoff.

        Distinguishes the three ways a handoff can be illegitimate: never
        reviewed, explicitly rejected, or approved-then-modified. The third is
        the interesting one, and the reason approvals carry a hash at all.
        """
        record = self.find_approval(stage, artifact)
        if record is not None:
            return record

        prior = [r for r in self.all() if r.stage == stage]
        if not prior:
            raise ApprovalDenied(
                f"No approval recorded for stage '{stage}'. "
                f"The gate has not been run for {artifact.schema_name()}."
            )

        latest = prior[-1]
        if latest.decision == "rejected":
            raise ApprovalDenied(
                f"Stage '{stage}' was rejected by {latest.approver}: "
                f"{latest.comment or 'no reason given'}"
            )

        raise ApprovalDenied(
            f"Approval {latest.audit_id} does not cover the current artifact. "
            f"Approved hash {latest.artifact_hash[:12]}..., "
            f"current hash {artifact.content_hash()[:12]}.... "
            "The artifact changed after it was approved, so the approval no longer applies."
        )
