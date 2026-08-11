"""The input to the flow: a business requirement that cleared intake.

Everything upstream of this (idea capture, business case, prioritisation) is the
delivery model's job, not an agent's. The flow starts where a requirement has
been approved and handed over.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class Initiative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    business_need: str
    requester: str
    constraints: list[str]
    success_measures: list[str]

    def as_prompt(self) -> str:
        """Render the initiative as the opening message to an agent."""
        constraints = "\n".join(f"- {item}" for item in self.constraints) or "- none stated"
        measures = "\n".join(f"- {item}" for item in self.success_measures) or "- none stated"
        return (
            f"Initiative {self.id}: {self.title}\n\n"
            f"Business need:\n{self.business_need}\n\n"
            f"Requested by: {self.requester}\n\n"
            f"Constraints:\n{constraints}\n\n"
            f"Success measures:\n{measures}"
        )


def load_initiative(path: str | Path) -> Initiative:
    return Initiative.model_validate_json(Path(path).read_text(encoding="utf-8"))


def find_initiative(initiatives_dir: Path, initiative_id: str) -> Initiative:
    """Look up an initiative by id, listing what exists when it is not found."""
    for path in sorted(initiatives_dir.glob("*.json")):
        initiative = load_initiative(path)
        if initiative.id.lower() == initiative_id.lower():
            return initiative
    available = ", ".join(sorted(p.stem for p in initiatives_dir.glob("*.json"))) or "none"
    raise FileNotFoundError(f"No initiative '{initiative_id}' in {initiatives_dir}. Available: {available}")


def list_initiatives(initiatives_dir: Path) -> list[Initiative]:
    return [load_initiative(path) for path in sorted(initiatives_dir.glob("*.json"))]


def dump_initiative(initiative: Initiative, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(initiative.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
