"""Command line entry point for the workshop.

    python -m agentic_sdlc.cli check
    python -m agentic_sdlc.cli index
    python -m agentic_sdlc.cli run INIT-1042
    python -m agentic_sdlc.cli verify INIT-1042
    python -m agentic_sdlc.cli audit
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from rich.console import Console
from rich.table import Table

from agentic_sdlc.config import RUNS_DIR, ConfigError, Settings, load_settings
from agentic_sdlc.contracts.approval import ApprovalDenied, ApprovalRegistry
from agentic_sdlc.contracts.artifacts import Artifact, DesignArtifact, SystemRequirements, WorkBreakdown
from agentic_sdlc.orchestrator import BREAKDOWN_GATE, DESIGN_GATE, REQUIREMENTS_GATE, Orchestrator

console = Console()

#: Saved artifact file -> (gate it must be approved at, schema to rebuild it with)
VERIFIABLE: dict[str, tuple[str, type[Artifact]]] = {
    "requirements": (REQUIREMENTS_GATE, SystemRequirements),
    "design": (DESIGN_GATE, DesignArtifact),
    "work_breakdown": (BREAKDOWN_GATE, WorkBreakdown),
}


def cmd_check(settings: Settings) -> int:
    """Confirm configuration and that the mock servers answer."""
    from agentic_sdlc.mcp_client import list_tools

    table = Table(title="Environment check")
    table.add_column("Check")
    table.add_column("Result")

    table.add_row("Foundry project endpoint", settings.foundry.project_endpoint)
    table.add_row("Foundry model", settings.foundry.model)
    table.add_row("Search endpoint", settings.search.endpoint)
    table.add_row("Search index", settings.search.index_name)
    table.add_row("Embedding deployment", settings.embedding.deployment)
    table.add_row("Approver", settings.approver)

    failures = 0
    for label, url in (
        ("mock Jira", settings.mcp.jira_url),
        ("mock GitHub", settings.mcp.github_url),
        ("mock Confluence", settings.mcp.confluence_url),
    ):
        try:
            tools = asyncio.run(list_tools(url))
            table.add_row(label, f"[green]{len(tools)} tools[/green]")
        except Exception as exc:  # noqa: BLE001 - report, do not crash the check
            failures += 1
            table.add_row(label, f"[red]unreachable: {type(exc).__name__}[/red]")

    console.print(table)
    if failures:
        console.print(
            f"[yellow]{failures} mock server(s) unreachable. "
            "Start them with: python -m mcp_servers.run_all[/yellow]"
        )
        return 1
    console.print("[green]Environment looks good.[/green]")
    return 0


def cmd_index(settings: Settings, recreate: bool) -> int:
    """Create the index and load the corpus into it."""
    from agentic_sdlc.grounding.index import create_or_update_index, delete_index
    from agentic_sdlc.grounding.ingest import ingest

    if recreate:
        try:
            delete_index(settings.search)
            console.print(f"[dim]deleted existing index '{settings.search.index_name}'[/dim]")
        except Exception:  # noqa: BLE001 - absent index is fine
            pass

    create_or_update_index(settings.search, settings.embedding)
    console.print(f"[green]index '{settings.search.index_name}' ready[/green]")

    count = ingest(settings.search, settings.embedding, settings.corpus_dir)
    console.print(f"[green]indexed {count} chunks from {settings.corpus_dir}[/green]")
    return 0


def cmd_run(settings: Settings, initiative_id: str, stop_after: str, auto: str | None) -> int:
    orchestrator = Orchestrator.build(settings, auto_decision=auto)
    result = asyncio.run(orchestrator.run(initiative_id, stop_after=stop_after))

    if result.stopped_at:
        console.print(f"\n[red]Run stopped at {result.stopped_at}.[/red]")
        return 2

    for name, path in result.artifact_paths.items():
        console.print(f"[dim]{name}: {path}[/dim]")
    return 0


def cmd_verify(settings: Settings, initiative_id: str) -> int:
    """Re-check saved artifacts against the approvals on record.

    This is the demonstration that approvals are bound to content: edit a saved
    artifact by hand, run this, and the approval no longer covers it.
    """
    registry = ApprovalRegistry(settings.audit_log_path)
    run_dir = RUNS_DIR / initiative_id
    if not run_dir.exists():
        console.print(f"[red]No saved run at {run_dir}. Run the flow first.[/red]")
        return 1

    table = Table(title=f"Approval verification for {initiative_id}")
    table.add_column("Artifact")
    table.add_column("Gate")
    table.add_column("Result")

    failures = 0
    for name, (stage, schema) in VERIFIABLE.items():
        path = run_dir / f"{name}.json"
        if not path.exists():
            table.add_row(name, stage, "[dim]not produced[/dim]")
            continue

        artifact = schema.model_validate_json(path.read_text(encoding="utf-8"))
        try:
            record = registry.assert_approved(stage, artifact)
            table.add_row(name, stage, f"[green]valid ({record.audit_id})[/green]")
        except ApprovalDenied as exc:
            failures += 1
            table.add_row(name, stage, f"[red]{exc}[/red]")

    console.print(table)
    if failures:
        console.print(f"[red]{failures} artifact(s) are not covered by a valid approval.[/red]")
        return 2
    console.print("[green]Every saved artifact is covered by an approval for its exact content.[/green]")
    return 0


def cmd_audit(settings: Settings, initiative_id: str) -> int:
    registry = ApprovalRegistry(settings.audit_log_path)
    records = registry.all()
    if initiative_id:
        records = [r for r in records if r.initiative_id.lower() == initiative_id.lower()]

    if not records:
        console.print(f"[yellow]No approvals recorded in {settings.audit_log_path}.[/yellow]")
        return 0

    table = Table(title=f"Audit trail ({settings.audit_log_path})")
    for column in ("When", "Initiative", "Stage", "Decision", "Approver", "Hash", "Audit id"):
        table.add_column(column)

    for record in records:
        colour = "green" if record.decision == "approved" else "red"
        table.add_row(
            record.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            record.initiative_id,
            record.stage,
            f"[{colour}]{record.decision}[/{colour}]",
            record.approver,
            record.artifact_hash[:12],
            record.audit_id,
        )
    console.print(table)
    return 0


def cmd_tamper(settings: Settings, initiative_id: str, artifact: str) -> int:
    """Make a small, legal edit to a saved artifact so `verify` fails.

    Provided so the tamper demonstration does not depend on everyone hand
    editing JSON correctly under time pressure.
    """
    path = RUNS_DIR / initiative_id / f"{artifact}.json"
    if not path.exists():
        console.print(f"[red]{path} not found.[/red]")
        return 1

    payload = json.loads(path.read_text(encoding="utf-8"))
    marker = "Edited after approval to demonstrate hash binding."
    if isinstance(payload.get("open_questions"), list):
        payload["open_questions"].append(marker)
    elif isinstance(payload.get("risks"), list):
        payload["risks"].append(marker)
    elif isinstance(payload.get("sequencing_notes"), list):
        payload["sequencing_notes"].append(marker)
    else:
        console.print("[red]No list field available to append to.[/red]")
        return 1

    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"[yellow]Modified {path} after it was approved.[/yellow]")
    console.print(f"[dim]Now run: python -m agentic_sdlc.cli verify {initiative_id}[/dim]")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentic_sdlc", description="Agentic SDLC on Microsoft Foundry")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check", help="Verify configuration and mock server connectivity")

    index_parser = subparsers.add_parser("index", help="Create the search index and load the corpus")
    index_parser.add_argument("--recreate", action="store_true", help="Delete the index first")

    run_parser = subparsers.add_parser("run", help="Run the orchestrated flow")
    run_parser.add_argument("initiative_id")
    run_parser.add_argument("--stop-after", default="", choices=["", "requirements", "design"])
    run_parser.add_argument("--auto", default=None, choices=["approve", "reject"], help="Skip prompts (unattended)")

    verify_parser = subparsers.add_parser("verify", help="Re-check saved artifacts against recorded approvals")
    verify_parser.add_argument("initiative_id")

    audit_parser = subparsers.add_parser("audit", help="Print the approval trail")
    audit_parser.add_argument("initiative_id", nargs="?", default="")

    tamper_parser = subparsers.add_parser("tamper", help="Edit an approved artifact to show the hash binding")
    tamper_parser.add_argument("initiative_id")
    tamper_parser.add_argument("--artifact", default="requirements", choices=list(VERIFIABLE))

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        settings = load_settings()
    except ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    if args.command == "check":
        return cmd_check(settings)
    if args.command == "index":
        return cmd_index(settings, recreate=args.recreate)
    if args.command == "run":
        return cmd_run(settings, args.initiative_id, args.stop_after, args.auto)
    if args.command == "verify":
        return cmd_verify(settings, args.initiative_id)
    if args.command == "audit":
        return cmd_audit(settings, args.initiative_id)
    if args.command == "tamper":
        return cmd_tamper(settings, args.initiative_id, args.artifact)
    return 1


if __name__ == "__main__":
    sys.exit(main())
