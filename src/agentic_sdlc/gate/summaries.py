"""Human-readable summaries of handoff artifacts.

A reviewer at a gate needs enough to make a real decision in a few seconds,
with the full JSON one keystroke away. Dumping raw JSON at someone guarantees
rubber-stamping, which would defeat the purpose of having a gate.
"""

from __future__ import annotations

from agentic_sdlc.contracts.artifacts import (
    Artifact,
    DesignArtifact,
    NeedsClarification,
    PullRequest,
    ReleasePackage,
    SystemRequirements,
    WorkBreakdown,
)


def _citation_line(artifact: SystemRequirements | DesignArtifact) -> str:
    if not artifact.citations:
        return "Grounded in: nothing cited (worth questioning)"
    sources = {f"{c.doc_id} §{c.section}" for c in artifact.citations}
    return f"Grounded in: {', '.join(sorted(sources))}  [{len(artifact.citations)} citations]"


def summary_lines(artifact: Artifact) -> list[str]:
    """Bullet lines describing an artifact, chosen per type."""
    if isinstance(artifact, SystemRequirements):
        dor = artifact.definition_of_ready
        failed = [check.name for check in dor.checks if not check.passed]
        lines = [
            f"{len(artifact.functional)} functional requirements",
            f"{len(artifact.non_functional)} non-functional requirements",
            f"Definition of Ready: {'PASS' if dor.passed else 'FAIL'} ({dor.summary} checks)",
        ]
        if failed:
            lines.append(f"Failing checks: {', '.join(failed)}")
        if artifact.open_questions:
            lines.append(f"{len(artifact.open_questions)} open questions")
        lines.append(_citation_line(artifact))
        return lines

    if isinstance(artifact, DesignArtifact):
        lines = [
            f"{len(artifact.components)} components, {len(artifact.data_flows)} data flows",
            f"{len(artifact.decisions)} design decisions recorded",
        ]
        if artifact.risks:
            lines.append(f"{len(artifact.risks)} risks called out")
        lines.append(_citation_line(artifact))
        return lines

    if isinstance(artifact, WorkBreakdown):
        points = sum(story.estimate_points for story in artifact.stories)
        blocked = [story.id for story in artifact.stories if story.depends_on]
        lines = [
            f"{len(artifact.epics)} epics, {len(artifact.stories)} stories, {points} points",
            f"{len(artifact.test_cases)} test cases",
        ]
        if blocked:
            lines.append(f"{len(blocked)} stories have dependencies: {', '.join(blocked[:5])}")
        return lines

    if isinstance(artifact, PullRequest):
        return [
            f"Story {artifact.story_id} on branch {artifact.branch}",
            f"{len(artifact.files_changed)} files changed, {len(artifact.tests_added)} tests added",
            f"PR: {artifact.pr_url}",
        ]

    if isinstance(artifact, ReleasePackage):
        return [
            f"Version {artifact.version}",
            f"{len(artifact.included_pr_urls)} pull requests included",
            f"Published to {artifact.confluence_url}",
        ]

    if isinstance(artifact, NeedsClarification):
        return [
            f"Agent stopped at stage '{artifact.stage}' and asked instead of guessing",
            f"Question: {artifact.question}",
            f"Why it blocks: {artifact.why_it_blocks}",
        ]

    return [f"{artifact.schema_name()} (no summary defined)"]
