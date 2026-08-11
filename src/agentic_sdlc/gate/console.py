"""The human approval gate.

The run suspends here. A person reads the artifact, then approves, rejects, or
edits it. Whatever they decide is written to the audit trail bound to the hash
of the exact content they saw, so the record answers "what was approved", not
just "was something approved".

Editing goes through full schema re-validation, which means the gate is
structurally incapable of passing a malformed artifact to the next agent.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from agentic_sdlc.contracts.approval import ApprovalRecord
from agentic_sdlc.contracts.artifacts import Artifact
from agentic_sdlc.gate.audit import AuditTrail
from agentic_sdlc.gate.summaries import summary_lines


@dataclass
class GateOutcome:
    """What the gate decided, plus the artifact as approved.

    `artifact` is the edited version when the reviewer changed something, which
    is why callers must carry it forward rather than reusing what they passed in.
    """

    artifact: Artifact
    record: ApprovalRecord

    @property
    def approved(self) -> bool:
        return self.record.decision == "approved"


class ConsoleGate:
    def __init__(
        self,
        audit: AuditTrail,
        approver: str,
        model: str = "",
        auto_decision: str | None = None,
    ) -> None:
        """`auto_decision` ("approve"/"reject") skips the prompt for automated
        runs and tests. The audit trail is written either way, and the record
        names the approver, so an unattended run is never mistaken for a human one."""
        self.audit = audit
        self.approver = approver
        self.model = model
        self.auto_decision = auto_decision
        self.console = Console()

    async def review(self, initiative_id: str, stage: str, artifact: Artifact, notes: list[str] | None = None) -> GateOutcome:
        self._render(initiative_id, stage, artifact, notes or [])

        if self.auto_decision:
            return await self._auto(initiative_id, stage, artifact)

        edited = False
        while True:
            choice = (await self._ask("decision [a]pprove [r]eject [e]dit [v]iew [q]uit > ")).strip().lower()

            if choice in {"a", "approve"}:
                return await self._decide(initiative_id, stage, artifact, "approved", edited)

            if choice in {"r", "reject"}:
                return await self._decide(initiative_id, stage, artifact, "rejected", edited)

            if choice in {"v", "view"}:
                self._render_full(artifact)

            elif choice in {"e", "edit"}:
                updated = await self._edit(artifact)
                if updated is not None:
                    artifact = updated
                    edited = True
                    self.console.print("[green]Artifact updated. The hash changed, so any earlier approval no longer applies.[/green]")
                    self._render(initiative_id, stage, artifact, notes or [])

            elif choice in {"q", "quit"}:
                raise KeyboardInterrupt("Gate abandoned by reviewer")

            else:
                self.console.print("[yellow]Choose a, r, e, v, or q.[/yellow]")

    def _render(self, initiative_id: str, stage: str, artifact: Artifact, notes: list[str]) -> None:
        body = [f"  • {line}" for line in summary_lines(artifact)]
        body.append("")
        body.append(f"  schema:   {artifact.schema_name()}")
        body.append(f"  hash:     {artifact.content_hash()}")
        if self.model:
            body.append(f"  model:    {self.model}")
        for note in notes:
            body.append(f"  {note}")

        self.console.print(
            Panel(
                "\n".join(body),
                title=f"[bold yellow]HUMAN APPROVAL REQUIRED[/bold yellow]  ·  {stage}",
                subtitle=f"initiative {initiative_id}",
                border_style="yellow",
            )
        )

    def _render_full(self, artifact: Artifact) -> None:
        payload = json.dumps(artifact.model_dump(mode="json"), indent=2, ensure_ascii=False)
        self.console.print(Syntax(payload, "json", theme="ansi_dark", word_wrap=True))

    async def _edit(self, artifact: Artifact) -> Artifact | None:
        """Replace one top-level field, then re-validate the whole artifact."""
        fields = ", ".join(type(artifact).model_fields)
        self.console.print(f"[dim]editable fields: {fields}[/dim]")

        field = (await self._ask("field to edit > ")).strip()
        if field not in type(artifact).model_fields:
            self.console.print(f"[red]'{field}' is not a field on {type(artifact).__name__}.[/red]")
            return None

        current = json.dumps(artifact.model_dump(mode="json")[field], ensure_ascii=False)
        self.console.print(f"[dim]current value: {current}[/dim]")

        raw = await self._ask("new value (JSON) > ")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            self.console.print(f"[red]Not valid JSON: {exc}. Strings need quotes, e.g. \"text\".[/red]")
            return None

        payload = artifact.model_dump(mode="json")
        payload[field] = value
        try:
            return type(artifact).model_validate(payload)
        except ValidationError as exc:
            self.console.print(f"[red]Rejected by the schema, so the edit was not applied:[/red]\n{exc}")
            return None

    async def _decide(self, initiative_id: str, stage: str, artifact: Artifact, decision: str, edited: bool) -> GateOutcome:
        approver = (await self._ask(f"your alias [{self.approver}] > ")).strip() or self.approver
        prompt = "reason for rejection > " if decision == "rejected" else "comment (optional) > "
        comment = (await self._ask(prompt)).strip()

        record = ApprovalRecord(
            initiative_id=initiative_id,
            stage=stage,
            decision=decision,  # type: ignore[arg-type]
            approver=approver,
            comment=comment,
            artifact_schema=artifact.schema_name(),
            artifact_hash=artifact.content_hash(),
            model=self.model,
            edited=edited,
        )
        await self.audit.record(record)

        colour = "green" if decision == "approved" else "red"
        self.console.print(f"[{colour}]{record.render()}[/{colour}]")
        self.console.print(f"[dim]written to: {', '.join(self.audit.sink_names)}[/dim]")
        return GateOutcome(artifact=artifact, record=record)

    async def _auto(self, initiative_id: str, stage: str, artifact: Artifact) -> GateOutcome:
        decision = "approved" if self.auto_decision == "approve" else "rejected"
        record = ApprovalRecord(
            initiative_id=initiative_id,
            stage=stage,
            decision=decision,  # type: ignore[arg-type]
            approver=f"{self.approver} (unattended)",
            comment=f"auto-{decision} via auto_decision",
            artifact_schema=artifact.schema_name(),
            artifact_hash=artifact.content_hash(),
            model=self.model,
        )
        await self.audit.record(record)
        self.console.print(f"[dim]{record.render()}[/dim]")
        return GateOutcome(artifact=artifact, record=record)

    async def approve_tool(self, tool_name: str, arguments: str) -> bool:
        """Sign off on a single tool call before the framework executes it.

        This is the framework's tool-approval interrupt, not the stage gate. It
        guards individual writes to a system of record; the stage gate guards
        the handoff between agents. Both are human-in-the-loop, and conflating
        them is the most common misreading of this workshop.
        """
        if self.auto_decision:
            return self.auto_decision == "approve"

        preview = arguments if len(arguments) <= 600 else arguments[:600] + " ...(truncated)"
        self.console.print(
            Panel(
                f"[bold]{tool_name}[/bold]\n\n{preview}",
                title="[bold cyan]TOOL CALL NEEDS APPROVAL[/bold cyan]",
                border_style="cyan",
            )
        )
        answer = (await self._ask("allow this call? [y/n] > ")).strip().lower()
        allowed = answer in {"y", "yes"}
        self.console.print("[green]allowed[/green]" if allowed else "[red]blocked[/red]")
        return allowed

    @staticmethod
    async def _ask(prompt: str) -> str:
        """Read stdin without blocking the event loop."""
        return await asyncio.to_thread(input, prompt)
