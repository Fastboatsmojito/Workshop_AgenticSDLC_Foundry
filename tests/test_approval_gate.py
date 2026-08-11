"""Tests for the property the whole gate rests on: approvals are bound to content.

If these pass, "approved" means "approved this exact artifact" and nothing else.
"""

from __future__ import annotations

import pytest

from agentic_sdlc.contracts.approval import (
    ApprovalDenied,
    ApprovalRecord,
    ApprovalRegistry,
)
from agentic_sdlc.contracts.artifacts import SystemRequirements

STAGE = "requirements->design"


def _record(artifact: SystemRequirements, decision: str = "approved", **kwargs) -> ApprovalRecord:
    return ApprovalRecord(
        initiative_id=artifact.initiative_id,
        stage=STAGE,
        decision=decision,  # type: ignore[arg-type]
        approver="tester",
        artifact_schema=artifact.schema_name(),
        artifact_hash=artifact.content_hash(),
        **kwargs,
    )


class TestHashing:
    def test_hash_is_stable_across_instances(self, requirements: SystemRequirements) -> None:
        clone = SystemRequirements.model_validate(requirements.model_dump())
        assert clone.content_hash() == requirements.content_hash()

    def test_hash_changes_when_any_field_changes(self, requirements: SystemRequirements) -> None:
        before = requirements.content_hash()
        mutated = requirements.model_copy(update={"open_questions": ["something else"]})
        assert mutated.content_hash() != before

    def test_hash_ignores_key_order(self, requirements: SystemRequirements) -> None:
        payload = requirements.model_dump(mode="json")
        reordered = dict(reversed(list(payload.items())))
        assert SystemRequirements.model_validate(reordered).content_hash() == requirements.content_hash()

    def test_schema_name_carries_a_version(self, requirements: SystemRequirements) -> None:
        assert requirements.schema_name() == "SystemRequirements@v1"


class TestRegistry:
    def test_approval_permits_the_handoff(self, tmp_path, requirements: SystemRequirements) -> None:
        registry = ApprovalRegistry(tmp_path / "audit.jsonl")
        registry.append(_record(requirements))

        record = registry.assert_approved(STAGE, requirements)
        assert record.decision == "approved"

    def test_missing_approval_blocks_the_handoff(self, tmp_path, requirements: SystemRequirements) -> None:
        registry = ApprovalRegistry(tmp_path / "audit.jsonl")

        with pytest.raises(ApprovalDenied, match="has not been run"):
            registry.assert_approved(STAGE, requirements)

    def test_rejection_blocks_the_handoff_and_reports_the_reason(
        self, tmp_path, requirements: SystemRequirements
    ) -> None:
        registry = ApprovalRegistry(tmp_path / "audit.jsonl")
        registry.append(_record(requirements, decision="rejected", comment="DoR-06 unresolved"))

        with pytest.raises(ApprovalDenied, match="DoR-06 unresolved"):
            registry.assert_approved(STAGE, requirements)

    def test_editing_after_approval_invalidates_it(self, tmp_path, requirements: SystemRequirements) -> None:
        """The tamper case. This is why approvals carry a hash at all."""
        registry = ApprovalRegistry(tmp_path / "audit.jsonl")
        registry.append(_record(requirements))

        tampered = requirements.model_copy(update={"open_questions": ["quietly added later"]})

        with pytest.raises(ApprovalDenied, match="changed after it was approved"):
            registry.assert_approved(STAGE, tampered)

    def test_approval_does_not_leak_across_stages(self, tmp_path, requirements: SystemRequirements) -> None:
        registry = ApprovalRegistry(tmp_path / "audit.jsonl")
        registry.append(_record(requirements))

        with pytest.raises(ApprovalDenied):
            registry.assert_approved("design->work_breakdown", requirements)

    def test_reapproving_the_edited_artifact_restores_the_handoff(
        self, tmp_path, requirements: SystemRequirements
    ) -> None:
        registry = ApprovalRegistry(tmp_path / "audit.jsonl")
        registry.append(_record(requirements))
        edited = requirements.model_copy(update={"open_questions": ["reviewed and reworded"]})

        with pytest.raises(ApprovalDenied):
            registry.assert_approved(STAGE, edited)

        registry.append(_record(edited, edited=True))
        assert registry.assert_approved(STAGE, edited).edited is True

    def test_trail_is_append_only(self, tmp_path, requirements: SystemRequirements) -> None:
        registry = ApprovalRegistry(tmp_path / "audit.jsonl")
        registry.append(_record(requirements, decision="rejected", comment="first pass"))
        registry.append(_record(requirements))

        decisions = [record.decision for record in registry.all()]
        assert decisions == ["rejected", "approved"], "earlier decisions must survive later ones"


class TestCovers:
    def test_covers_requires_matching_schema(self, requirements: SystemRequirements, design) -> None:
        record = _record(requirements)
        assert record.covers(requirements)
        assert not record.covers(design)

    def test_rejected_records_never_cover(self, requirements: SystemRequirements) -> None:
        assert not _record(requirements, decision="rejected").covers(requirements)
