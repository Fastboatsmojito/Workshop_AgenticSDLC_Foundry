"""Tests for the mock systems of record and the corpus chunking.

The MCP tests talk to the real servers over HTTP, so they cover the transport
the agents actually use rather than a stub of it.
"""

from __future__ import annotations

import json
from importlib.metadata import version

from agent_framework import MCPStreamableHTTPTool
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from agentic_sdlc.config import DATA_DIR
from agentic_sdlc.gate.audit import ConfluenceSink
from agentic_sdlc.grounding.ingest import MANIFEST_NAME, chunk_markdown, load_corpus
from agentic_sdlc.initiative import list_initiatives
from agentic_sdlc.mcp_client import call_tool, list_tools

CORPUS_DIR = DATA_DIR / "corpus"


def test_mcp_runtime_matches_the_agent_framework_supported_range() -> None:
    installed = Version(version("mcp"))
    supported = SpecifierSet(">=1.29,<2")
    assert installed in supported, (
        f"mcp {installed} is incompatible with this Agent Framework release; "
        "install requirements.txt to restore mcp>=1.29,<2"
    )


async def test_agent_framework_loads_tools_from_the_mock_server(mock_servers) -> None:
    jira = MCPStreamableHTTPTool(
        name="jira-test",
        url=mock_servers["jira"],
        allowed_tools=["get_issue"],
        approval_mode="never_require",
        load_prompts=False,
    )

    async with jira:
        assert [function.name for function in jira.functions] == ["get_issue"]


class TestMockJira:
    async def test_exposes_the_expected_tools(self, mock_servers) -> None:
        tools = await list_tools(mock_servers["jira"])
        assert {"create_epic", "create_story", "create_test_case", "get_issue"} <= set(tools)

    async def test_created_work_can_be_read_back(self, mock_servers) -> None:
        url = mock_servers["jira"]
        epic = await call_tool(url, "create_epic", {"initiative_id": "INIT-T1", "title": "T", "outcome": "O"})
        story = await call_tool(
            url,
            "create_story",
            {
                "initiative_id": "INIT-T1",
                "epic_key": epic["key"],
                "title": "Score a claim",
                "description": "d",
                "acceptance_criteria": ["a"],
                "estimate_points": 3,
            },
        )

        readback = await call_tool(url, "get_issue", {"key": story["key"]})
        assert readback["title"] == "Score a claim"
        assert readback["epic_key"] == epic["key"]

    async def test_ids_are_numbered_per_type(self, mock_servers) -> None:
        url = mock_servers["jira"]
        epic = await call_tool(url, "create_epic", {"initiative_id": "INIT-T2", "title": "T", "outcome": "O"})
        assert epic["key"].startswith("EPIC-")

    async def test_unknown_issue_reports_an_error(self, mock_servers) -> None:
        result = await call_tool(mock_servers["jira"], "get_issue", {"key": "STORY-999"})
        assert "error" in result


class TestMockGitHub:
    async def test_branch_commit_and_pull_request(self, mock_servers) -> None:
        url = mock_servers["github"]
        await call_tool(url, "create_branch", {"branch": "feature/test-1"})
        commit = await call_tool(
            url,
            "commit_files",
            {
                "branch": "feature/test-1",
                "message": "add eligibility check",
                "paths": ["src/eligibility.py", "tests/test_eligibility.py"],
                "contents": ["# code", "# test"],
            },
        )
        assert commit["files_committed"] == 2

        pull = await call_tool(url, "open_pull_request", {"branch": "feature/test-1", "title": "t", "body": "b"})
        assert pull["state"] == "open"

    async def test_commit_rejects_mismatched_paths_and_contents(self, mock_servers) -> None:
        url = mock_servers["github"]
        await call_tool(url, "create_branch", {"branch": "feature/test-2"})
        result = await call_tool(
            url,
            "commit_files",
            {"branch": "feature/test-2", "message": "m", "paths": ["a", "b"], "contents": ["only one"]},
        )
        assert "error" in result

    async def test_commit_to_unknown_branch_is_refused(self, mock_servers) -> None:
        result = await call_tool(
            mock_servers["github"],
            "commit_files",
            {"branch": "does/not/exist", "message": "m", "paths": ["a"], "contents": ["x"]},
        )
        assert "error" in result


class TestMockConfluence:
    async def test_appending_accumulates_rather_than_overwrites(self, mock_servers) -> None:
        url = mock_servers["confluence"]
        page_id = "audit-init-append"
        await call_tool(url, "append_to_page", {"page_id": page_id, "body": "first entry"})
        await call_tool(url, "append_to_page", {"page_id": page_id, "body": "second entry"})

        page = await call_tool(url, "get_page", {"page_id": page_id})
        assert "first entry" in page["body"]
        assert "second entry" in page["body"]

    def test_audit_page_id_is_derived_from_the_initiative(self) -> None:
        assert ConfluenceSink.page_id("INIT-1042") == "audit-init-1042"


class TestCorpus:
    def test_every_manifest_document_exists(self) -> None:
        manifest = json.loads((CORPUS_DIR / MANIFEST_NAME).read_text(encoding="utf-8"))
        for entry in manifest["documents"]:
            assert (CORPUS_DIR / entry["file"]).exists(), f"missing {entry['file']}"

    def test_corpus_chunks_carry_the_metadata_agents_cite(self) -> None:
        chunks = load_corpus(CORPUS_DIR)
        assert chunks
        assert all(chunk.doc_id and chunk.section and chunk.doc_type for chunk in chunks)

    def test_all_four_document_types_are_represented(self) -> None:
        doc_types = {chunk.doc_type for chunk in load_corpus(CORPUS_DIR)}
        assert doc_types == {"dor", "standards", "architecture", "design_format"}

    def test_chunk_ids_are_unique(self) -> None:
        """Duplicate ids would silently overwrite each other in the index."""
        ids = [chunk.id for chunk in load_corpus(CORPUS_DIR)]
        assert len(ids) == len(set(ids))

    def test_chunking_splits_on_headings(self) -> None:
        chunks = chunk_markdown(
            "intro text\n\n## First\nalpha\n\n## Second\nbeta\n",
            doc_id="D",
            title="T",
            doc_type="standards",
        )
        assert [chunk.section for chunk in chunks] == ["Overview", "First", "Second"]

    def test_long_sections_are_split_on_paragraphs(self) -> None:
        body = "\n\n".join(["paragraph " * 60] * 6)
        chunks = chunk_markdown(f"## Big\n{body}", doc_id="D", title="T", doc_type="standards")
        assert len(chunks) > 1
        assert all(chunk.content for chunk in chunks)


class TestInitiatives:
    def test_initiatives_load_and_render_as_prompts(self) -> None:
        initiatives = list_initiatives(DATA_DIR / "initiatives")
        assert initiatives
        for initiative in initiatives:
            prompt = initiative.as_prompt()
            assert initiative.id in prompt
            assert initiative.business_need[:30] in prompt
