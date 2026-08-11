"""The orchestrator: sequential agents with enforced gates between them.

Written as explicit Python rather than assembled from a workflow builder. That
is deliberate. The control flow *is* the governance model, so it should be
readable line by line: run an agent, gate its output, refuse to continue without
a valid approval, then hand the approved artifact to the next agent.

The enforcement is `registry.assert_approved`, called immediately before every
handoff. Without it the gate would be a printed message; with it the gate is a
hard dependency in the graph.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from agentic_sdlc.agents import design_agent, requirements_agent, workbreakdown_agent
from agentic_sdlc.config import RUNS_DIR, Settings
from agentic_sdlc.contracts.approval import ApprovalRegistry
from agentic_sdlc.contracts.artifacts import (
    Artifact,
    DesignArtifact,
    SystemRequirements,
    WorkBreakdown,
)
from agentic_sdlc.gate.audit import AuditTrail, ConfluenceSink, JsonlSink, TraceSink
from agentic_sdlc.gate.console import ConsoleGate
from agentic_sdlc.initiative import Initiative, find_initiative

REQUIREMENTS_GATE = "requirements->design"
DESIGN_GATE = "design->work_breakdown"
BREAKDOWN_GATE = "work_breakdown->delivery"

STAGE_ORDER = ("requirements", "design", "work_breakdown")


@dataclass
class RunResult:
    initiative: Initiative
    requirements: SystemRequirements | None = None
    design: DesignArtifact | None = None
    work_breakdown: WorkBreakdown | None = None
    stopped_at: str = ""
    stop_reason: str = ""
    artifact_paths: dict[str, Path] = field(default_factory=dict)

    @property
    def completed(self) -> bool:
        return not self.stopped_at


class Orchestrator:
    def __init__(self, settings: Settings, gate: ConsoleGate, registry: ApprovalRegistry) -> None:
        self.settings = settings
        self.gate = gate
        self.registry = registry
        self.console = Console()

    @classmethod
    def build(cls, settings: Settings, auto_decision: str | None = None) -> Orchestrator:
        """Wire the gate, the audit sinks, and the approval registry together."""
        registry = ApprovalRegistry(settings.audit_log_path)
        audit = AuditTrail(
            primary=JsonlSink(registry),
            secondary=[ConfluenceSink(settings.mcp.confluence_url), TraceSink()],
        )
        gate = ConsoleGate(
            audit=audit,
            approver=settings.approver,
            model=settings.foundry.model,
            auto_decision=auto_decision,
        )
        return cls(settings=settings, gate=gate, registry=registry)

    async def run(self, initiative_id: str, stop_after: str = "") -> RunResult:
        initiative = find_initiative(self.settings.initiatives_dir, initiative_id)
        result = RunResult(initiative=initiative)
        run_dir = RUNS_DIR / initiative.id
        run_dir.mkdir(parents=True, exist_ok=True)

        # --- Requirements ---------------------------------------------------
        self._banner("Requirements Agent", "turning the business need into system requirements")
        agent = requirements_agent.build(self.settings)
        async with agent:
            requirements, response = await requirements_agent.run(agent, initiative)
        result.requirements = requirements
        result.artifact_paths["requirements"] = self._save(run_dir, "requirements", requirements)

        outcome = await self.gate.review(
            initiative_id=initiative.id,
            stage=REQUIREMENTS_GATE,
            artifact=requirements,
            notes=self._usage_notes(response),
        )
        requirements = outcome.artifact  # may have been edited at the gate
        result.requirements = requirements
        result.artifact_paths["requirements"] = self._save(run_dir, "requirements", requirements)

        if not self._may_continue(REQUIREMENTS_GATE, requirements, result):
            return result
        if stop_after == "requirements":
            return result

        # --- Design ---------------------------------------------------------
        self._banner("Design Agent", "designing against the approved requirements")
        agent = design_agent.build(self.settings)
        async with agent:
            design, response = await design_agent.run(agent, requirements)
        result.design = design

        outcome = await self.gate.review(
            initiative_id=initiative.id,
            stage=DESIGN_GATE,
            artifact=design,
            notes=self._usage_notes(response),
        )
        design = outcome.artifact
        result.design = design
        result.artifact_paths["design"] = self._save(run_dir, "design", design)

        if not self._may_continue(DESIGN_GATE, design, result):
            return result
        if stop_after == "design":
            return result

        # --- Work breakdown -------------------------------------------------
        self._banner("Work Breakdown Agent", "creating epics, stories, and tests in Jira")
        agent = workbreakdown_agent.build(self.settings)
        async with agent:
            breakdown, response = await workbreakdown_agent.run(
                agent, design, on_approval_request=self.gate.approve_tool
            )
        result.work_breakdown = breakdown

        outcome = await self.gate.review(
            initiative_id=initiative.id,
            stage=BREAKDOWN_GATE,
            artifact=breakdown,
            notes=self._usage_notes(response),
        )
        breakdown = outcome.artifact
        result.work_breakdown = breakdown
        result.artifact_paths["work_breakdown"] = self._save(run_dir, "work_breakdown", breakdown)

        if not self._may_continue(BREAKDOWN_GATE, breakdown, result):
            return result

        self.console.print(
            "\n[bold green]Flow complete.[/bold green] Delivery and Release are the take-home track."
        )
        return result

    def _may_continue(self, stage: str, artifact: Artifact, result: RunResult) -> bool:
        """The enforcement point. No valid approval, no next agent."""
        from agentic_sdlc.contracts.approval import ApprovalDenied

        try:
            record = self.registry.assert_approved(stage, artifact)
        except ApprovalDenied as exc:
            result.stopped_at = stage
            result.stop_reason = str(exc)
            self.console.print(f"\n[bold red]Handoff blocked at {stage}[/bold red]\n{exc}")
            return False

        self.console.print(f"[dim]handoff permitted by {record.audit_id}[/dim]")
        return True

    def _save(self, run_dir: Path, name: str, artifact: Artifact) -> Path:
        """Persist an artifact so it can be inspected, diffed, and tampered with."""
        path = run_dir / f"{name}.json"
        path.write_text(
            json.dumps(artifact.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def _banner(self, title: str, subtitle: str) -> None:
        self.console.print(f"\n[bold blue]▶ {title}[/bold blue] [dim]— {subtitle}[/dim]")

    @staticmethod
    def _usage_notes(response) -> list[str]:
        """Surface token usage at the gate when the provider reports it."""
        usage = getattr(response, "usage_details", None) or getattr(response, "usage", None)
        if usage is None:
            return []
        total = getattr(usage, "total_token_count", None) or getattr(usage, "total_tokens", None)
        return [f"tokens:   {total}"] if total else []
