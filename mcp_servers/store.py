"""Tiny JSON-file store shared by the mock systems of record.

Stateful on purpose: an agent writes a story and can read it back, which is what
makes the mocks behave enough like Jira/GitHub/Confluence to be worth wiring
agents against. State lives under `.runs/mock-state/` so a reset is one delete.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

STATE_DIR = Path(__file__).resolve().parents[1] / ".runs" / "mock-state"

_LOCKS: dict[str, threading.Lock] = {}


class JsonStore:
    def __init__(self, name: str) -> None:
        self.name = name
        self.path = STATE_DIR / f"{name}.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        _LOCKS.setdefault(name, threading.Lock())

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def write(self, data: dict[str, Any]) -> None:
        self.path.write_text(
            json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )

    @contextmanager
    def edit(self) -> Iterator[dict[str, Any]]:
        """Read-modify-write under a lock so concurrent tool calls don't race."""
        with _LOCKS[self.name]:
            data = self.read()
            yield data
            self.write(data)

    def next_id(self, data: dict[str, Any], collection: str, prefix: str) -> str:
        """Next id for one prefix, counted per prefix so epics and stories
        number independently (EPIC-001, STORY-001) instead of sharing a run."""
        items = data.setdefault(collection, {})
        existing = sum(1 for key in items if key.startswith(f"{prefix}-"))
        return f"{prefix}-{existing + 1:03d}"

    def reset(self) -> None:
        if self.path.exists():
            self.path.unlink()
