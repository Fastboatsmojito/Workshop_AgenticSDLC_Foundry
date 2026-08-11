"""Where approval decisions are written.

Three sinks, one code path. The JSONL file is authoritative and append-only;
Confluence and the trace are how humans and auditors actually find a decision
later. Take-home swaps the Confluence URL for the real Atlassian MCP server and
nothing else changes, which is the point: the audit path you exercise against
mocks is the one that runs in production.
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from agentic_sdlc.contracts.approval import ApprovalRecord, ApprovalRegistry
from agentic_sdlc.mcp_client import call_tool

logger = logging.getLogger(__name__)


@runtime_checkable
class AuditSink(Protocol):
    name: str

    async def write(self, record: ApprovalRecord) -> None: ...


class JsonlSink:
    """Authoritative local trail. A failure here fails the gate."""

    name = "audit.jsonl"

    def __init__(self, registry: ApprovalRegistry) -> None:
        self.registry = registry

    async def write(self, record: ApprovalRecord) -> None:
        self.registry.append(record)


class ConfluenceSink:
    """Human-readable trail, one page per initiative."""

    name = "confluence"

    def __init__(self, mcp_url: str) -> None:
        self.mcp_url = mcp_url

    @staticmethod
    def page_id(initiative_id: str) -> str:
        return f"audit-{initiative_id.lower()}"

    async def write(self, record: ApprovalRecord) -> None:
        entry = (
            f"- **{record.decision.upper()}** `{record.stage}` "
            f"by {record.approver} at {record.timestamp.isoformat()} "
            f"| {record.artifact_schema} | hash `{record.artifact_hash[:12]}` "
            f"| audit `{record.audit_id}`"
            + (f"\n  - comment: {record.comment}" if record.comment else "")
            + ("\n  - artifact was edited before approval" if record.edited else "")
        )
        await call_tool(
            self.mcp_url,
            "append_to_page",
            {"page_id": self.page_id(record.initiative_id), "body": entry},
        )


class TraceSink:
    """Emits the decision as a span event so it appears inline with agent steps."""

    name = "trace"

    async def write(self, record: ApprovalRecord) -> None:
        try:
            from opentelemetry import trace
        except ImportError:  # tracing is optional in the live session
            return

        span = trace.get_current_span()
        if not span.is_recording():
            return
        span.add_event(
            "sdlc.human_approval",
            attributes={
                "sdlc.audit_id": record.audit_id,
                "sdlc.initiative_id": record.initiative_id,
                "sdlc.stage": record.stage,
                "sdlc.decision": record.decision,
                "sdlc.approver": record.approver,
                "sdlc.artifact_schema": record.artifact_schema,
                "sdlc.artifact_hash": record.artifact_hash,
                "sdlc.edited": record.edited,
            },
        )


class AuditTrail:
    """Fans a decision out to every sink.

    The JSONL sink is required: if the decision cannot be durably recorded, the
    gate must fail rather than let the run continue on an unlogged approval.
    Secondary sinks are best-effort, so a stopped mock server degrades the trail
    instead of halting the workshop.
    """

    def __init__(self, primary: JsonlSink, secondary: list[AuditSink] | None = None) -> None:
        self.primary = primary
        self.secondary = secondary or []

    async def record(self, record: ApprovalRecord) -> ApprovalRecord:
        await self.primary.write(record)
        for sink in self.secondary:
            try:
                await sink.write(record)
            except Exception as exc:  # noqa: BLE001 - a sink outage must not stop the gate
                logger.warning("Audit sink '%s' failed: %s", sink.name, exc)
        return record

    @property
    def sink_names(self) -> list[str]:
        return [self.primary.name, *(sink.name for sink in self.secondary)]
