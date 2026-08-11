"""The reference run in `solutions/` has to be genuine.

Participants compare their output against it and, in guide 05, use it to see
what a valid approval looks like. If its `audit.jsonl` stopped covering its
artifacts, the reference would be teaching the opposite of the lesson.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_sdlc.contracts.approval import ApprovalDenied, ApprovalRegistry
from agentic_sdlc.contracts.artifacts import (
    Artifact,
    DesignArtifact,
    SystemRequirements,
    WorkBreakdown,
)

EXPECTED_RUN = Path(__file__).resolve().parents[1] / "solutions" / "expected-run"

STAGES: list[tuple[str, str, type[Artifact]]] = [
    ("requirements->design", "requirements.json", SystemRequirements),
    ("design->work_breakdown", "design.json", DesignArtifact),
    ("work_breakdown->delivery", "work_breakdown.json", WorkBreakdown),
]


def load(filename: str, model: type[Artifact]) -> Artifact:
    return model.model_validate_json((EXPECTED_RUN / filename).read_text(encoding="utf-8"))


@pytest.fixture
def registry() -> ApprovalRegistry:
    return ApprovalRegistry(EXPECTED_RUN / "audit.jsonl")


@pytest.mark.parametrize(("stage", "filename", "model"), STAGES)
def test_reference_artifacts_validate(stage: str, filename: str, model: type[Artifact]) -> None:
    assert isinstance(load(filename, model), model)


@pytest.mark.parametrize(("stage", "filename", "model"), STAGES)
def test_reference_approvals_cover_reference_artifacts(
    registry: ApprovalRegistry, stage: str, filename: str, model: type[Artifact]
) -> None:
    record = registry.assert_approved(stage, load(filename, model))
    assert record.decision == "approved"


def test_editing_a_reference_artifact_invalidates_its_approval(registry: ApprovalRegistry) -> None:
    requirements = load("requirements.json", SystemRequirements)
    tampered = requirements.model_copy(update={"title": requirements.title + " (revised)"})

    with pytest.raises(ApprovalDenied, match="does not cover"):
        registry.assert_approved("requirements->design", tampered)


def test_reference_citations_point_at_real_corpus_sections() -> None:
    """A citation nobody can follow is decoration. Check every one resolves to a
    document in the manifest and a heading that actually exists in it."""
    corpus = EXPECTED_RUN.parents[1] / "data" / "corpus"
    manifest = json.loads((corpus / "manifest.json").read_text(encoding="utf-8"))
    documents = {document["doc_id"]: document["file"] for document in manifest["documents"]}

    for _, filename, model in STAGES:
        artifact = load(filename, model)
        for citation in getattr(artifact, "citations", []):
            assert citation.doc_id in documents, f"{filename} cites unknown doc {citation.doc_id}"
            text = (corpus / documents[citation.doc_id]).read_text(encoding="utf-8")
            assert f"## {citation.section}" in text, (
                f"{filename} cites {citation.doc_id} §{citation.section}, "
                "which is not a heading in that document"
            )
