"""Tests for the gate's behaviour and the audit fan-out."""

from __future__ import annotations

import pytest

from agentic_sdlc.contracts.approval import ApprovalRecord, ApprovalRegistry
from agentic_sdlc.contracts.artifacts import SystemRequirements
from agentic_sdlc.gate.audit import AuditTrail, JsonlSink
from agentic_sdlc.gate.console import ConsoleGate
from agentic_sdlc.gate.summaries import summary_lines

STAGE = "requirements->design"


class ExplodingSink:
    """A secondary sink that always fails, standing in for a stopped server."""

    name = "exploding"

    async def write(self, record: ApprovalRecord) -> None:
        raise ConnectionError("mock server is down")


class RecordingSink:
    name = "recording"

    def __init__(self) -> None:
        self.records: list[ApprovalRecord] = []

    async def write(self, record: ApprovalRecord) -> None:
        self.records.append(record)


def _trail(tmp_path, secondary=None) -> tuple[AuditTrail, ApprovalRegistry]:
    registry = ApprovalRegistry(tmp_path / "audit.jsonl")
    return AuditTrail(primary=JsonlSink(registry), secondary=secondary or []), registry


class TestUnattendedGate:
    async def test_approval_is_recorded_and_permits_the_handoff(
        self, tmp_path, requirements: SystemRequirements
    ) -> None:
        trail, registry = _trail(tmp_path)
        gate = ConsoleGate(audit=trail, approver="tester", auto_decision="approve")

        outcome = await gate.review("INIT-TEST", STAGE, requirements)

        assert outcome.approved
        assert registry.assert_approved(STAGE, requirements).audit_id == outcome.record.audit_id

    async def test_rejection_is_recorded_and_blocks_the_handoff(
        self, tmp_path, requirements: SystemRequirements
    ) -> None:
        from agentic_sdlc.contracts.approval import ApprovalDenied

        trail, registry = _trail(tmp_path)
        gate = ConsoleGate(audit=trail, approver="tester", auto_decision="reject")

        outcome = await gate.review("INIT-TEST", STAGE, requirements)

        assert not outcome.approved
        with pytest.raises(ApprovalDenied):
            registry.assert_approved(STAGE, requirements)

    async def test_unattended_runs_are_labelled_in_the_trail(
        self, tmp_path, requirements: SystemRequirements
    ) -> None:
        """An automated decision must never be mistaken for a human one."""
        trail, registry = _trail(tmp_path)
        gate = ConsoleGate(audit=trail, approver="tester", auto_decision="approve")

        await gate.review("INIT-TEST", STAGE, requirements)

        assert "unattended" in registry.all()[0].approver

    async def test_tool_approval_follows_the_unattended_decision(
        self, tmp_path, requirements: SystemRequirements
    ) -> None:
        trail, _ = _trail(tmp_path)
        assert await ConsoleGate(trail, "tester", auto_decision="approve").approve_tool("create_story", "{}")
        assert not await ConsoleGate(trail, "tester", auto_decision="reject").approve_tool("create_story", "{}")


class TestAuditFanout:
    async def test_every_sink_receives_the_decision(self, tmp_path, requirements: SystemRequirements) -> None:
        recorder = RecordingSink()
        trail, registry = _trail(tmp_path, secondary=[recorder])

        await ConsoleGate(trail, "tester", auto_decision="approve").review("INIT-TEST", STAGE, requirements)

        assert len(recorder.records) == 1
        assert len(registry.all()) == 1

    async def test_a_failing_secondary_sink_does_not_lose_the_decision(
        self, tmp_path, requirements: SystemRequirements
    ) -> None:
        """A stopped mock server should degrade the trail, not halt the workshop."""
        recorder = RecordingSink()
        trail, registry = _trail(tmp_path, secondary=[ExplodingSink(), recorder])

        await ConsoleGate(trail, "tester", auto_decision="approve").review("INIT-TEST", STAGE, requirements)

        assert len(registry.all()) == 1, "the authoritative trail must still hold the decision"
        assert len(recorder.records) == 1, "later sinks must still run after an earlier one fails"


class TestSummaries:
    def test_requirements_summary_surfaces_a_failing_dor_check(
        self, requirements: SystemRequirements
    ) -> None:
        text = " ".join(summary_lines(requirements))
        assert "FAIL" in text
        assert "DoR-06" in text

    def test_design_summary_mentions_components_and_citations(self, design) -> None:
        text = " ".join(summary_lines(design))
        assert "component" in text.lower()
        assert "ARCH-STANDARDS" in text
