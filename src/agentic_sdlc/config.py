"""Environment configuration for the workshop.

Auth split, and why: the Foundry project endpoint is Entra-only, so agents
authenticate with your `az login` identity. Azure AI Search and the models
endpoint take API keys, which keeps setup short for a two-hour session. Nothing
here is a production auth pattern; see `infra/reference-architecture.md`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
RUNS_DIR = REPO_ROOT / ".runs"


class ConfigError(RuntimeError):
    """Raised when a required setting is missing, naming the variable to set."""


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(
            f"Missing required environment variable '{name}'. "
            f"Copy .env.example to .env and fill it in, then re-run."
        )
    return value


def _optional(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class FoundrySettings:
    project_endpoint: str
    model: str


@dataclass(frozen=True)
class SearchSettings:
    endpoint: str
    api_key: str
    index_name: str


@dataclass(frozen=True)
class EmbeddingSettings:
    """Embeddings go through the project's Azure OpenAI endpoint using your
    `az login` identity, so there is no second key to distribute."""

    openai_endpoint: str
    deployment: str
    api_version: str
    dimensions: int


@dataclass(frozen=True)
class McpSettings:
    """URLs of the mock systems of record.

    Take-home swaps these for the real Atlassian and GitHub MCP servers. The
    agent code does not change; only these URLs do.
    """

    jira_url: str
    github_url: str
    confluence_url: str


@dataclass(frozen=True)
class Settings:
    foundry: FoundrySettings
    search: SearchSettings
    embedding: EmbeddingSettings
    mcp: McpSettings
    approver: str
    audit_log_path: Path
    enable_tracing: bool
    corpus_dir: Path = field(default=DATA_DIR / "corpus")
    initiatives_dir: Path = field(default=DATA_DIR / "initiatives")


def load_settings(dotenv_path: str | os.PathLike[str] | None = None) -> Settings:
    """Read `.env` (if present) plus the process environment."""
    load_dotenv(dotenv_path or REPO_ROOT / ".env", override=False)

    return Settings(
        foundry=FoundrySettings(
            project_endpoint=_require("FOUNDRY_PROJECT_ENDPOINT"),
            model=_optional("FOUNDRY_MODEL", "gpt-4o-mini"),
        ),
        search=SearchSettings(
            endpoint=_require("SEARCH_ENDPOINT"),
            api_key=_require("SEARCH_API_KEY"),
            index_name=_optional("SEARCH_INDEX_NAME", "sdlc-corpus"),
        ),
        embedding=EmbeddingSettings(
            openai_endpoint=_require("FOUNDRY_OPENAI_ENDPOINT"),
            deployment=_optional("EMBEDDING_DEPLOYMENT", "text-embedding-3-small"),
            api_version=_optional("EMBEDDING_API_VERSION", "2024-10-21"),
            dimensions=int(_optional("EMBEDDING_DIMENSIONS", "1536")),
        ),
        mcp=McpSettings(
            jira_url=_optional("MCP_JIRA_URL", "http://127.0.0.1:8931/mcp"),
            github_url=_optional("MCP_GITHUB_URL", "http://127.0.0.1:8932/mcp"),
            confluence_url=_optional("MCP_CONFLUENCE_URL", "http://127.0.0.1:8933/mcp"),
        ),
        approver=_optional("APPROVER_ALIAS", os.getenv("USERNAME", "workshop-participant")),
        audit_log_path=Path(_optional("AUDIT_LOG_PATH", str(RUNS_DIR / "audit.jsonl"))),
        enable_tracing=_optional("ENABLE_TRACING", "false").lower() in {"1", "true", "yes"},
    )
