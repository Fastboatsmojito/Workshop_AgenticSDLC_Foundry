"""Hybrid retrieval over the SDLC corpus, exposed to agents as a function tool.

Each agent gets a tool scoped to the document types it is allowed to reason
over. The Requirements Agent sees the Definition of Ready and delivery
standards; the Design Agent sees architecture standards and the design format.
Scoping at construction time is cheaper and more predictable than asking the
model to filter itself.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

from agent_framework import tool
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

from agentic_sdlc.config import EmbeddingSettings, SearchSettings
from agentic_sdlc.grounding.embeddings import build_embedding_client, embed_query

DEFAULT_TOP_K = 5
VECTOR_FIELD = "content_vector"


def _doc_type_filter(doc_types: Sequence[str]) -> str | None:
    if not doc_types:
        return None
    clauses = " or ".join(f"doc_type eq '{doc_type}'" for doc_type in doc_types)
    return f"({clauses})"


def build_corpus_search_tool(
    search_settings: SearchSettings,
    embedding_settings: EmbeddingSettings,
    doc_types: Sequence[str],
    top_k: int = DEFAULT_TOP_K,
):
    """Return a function tool that searches only `doc_types`.

    Hybrid search: the keyword half catches exact terms like "DoR-04", the
    vector half catches paraphrases. Insurance-style corpora need both.
    """
    search_client = SearchClient(
        endpoint=search_settings.endpoint,
        index_name=search_settings.index_name,
        credential=AzureKeyCredential(search_settings.api_key),
    )
    embed_client = build_embedding_client(embedding_settings)
    doc_filter = _doc_type_filter(doc_types)
    scope = ", ".join(doc_types) if doc_types else "the whole corpus"

    @tool(
        name="search_corpus",
        description=(
            f"Search the governance corpus ({scope}) for standards, templates, and "
            "checklists. Always search before asserting what a standard requires, "
            "and cite what you use."
        ),
    )
    def search_corpus(
        query: Annotated[str, "What to look for, in natural language."],
    ) -> str:
        vector = embed_query(embed_client, embedding_settings, query)
        results = search_client.search(
            search_text=query,
            vector_queries=[
                VectorizedQuery(
                    vector=vector,
                    k_nearest_neighbors=top_k,
                    fields=VECTOR_FIELD,
                )
            ],
            filter=doc_filter,
            top=top_k,
        )

        blocks: list[str] = []
        for hit in results:
            blocks.append(
                "\n".join(
                    [
                        f"doc_id: {hit['doc_id']}",
                        f"title: {hit['title']}",
                        f"section: {hit['section']}",
                        f"doc_type: {hit['doc_type']}",
                        f"content: {hit['content']}",
                    ]
                )
            )

        if not blocks:
            return (
                "No matching passages. Do not invent a standard: either search with "
                "different wording or record the gap as an open question."
            )
        return "\n\n---\n\n".join(blocks)

    return search_corpus
