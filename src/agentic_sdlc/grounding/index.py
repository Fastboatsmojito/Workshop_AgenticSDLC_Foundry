"""Azure AI Search index definition for the SDLC corpus.

One index holds every document type (Definition of Ready, delivery standards,
architecture standards, design format) with a filterable `doc_type`. Agents
filter to the slice they are entitled to reason over, which keeps the
Requirements Agent from quoting architecture standards at you and makes
retrieval scoping an explicit design choice rather than an accident.
"""

from __future__ import annotations

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

from agentic_sdlc.config import EmbeddingSettings, SearchSettings

VECTOR_PROFILE = "sdlc-vector-profile"
HNSW_CONFIG = "sdlc-hnsw"
SEMANTIC_CONFIG = "sdlc-semantic"


def build_index_client(settings: SearchSettings) -> SearchIndexClient:
    return SearchIndexClient(
        endpoint=settings.endpoint,
        credential=AzureKeyCredential(settings.api_key),
    )


def build_index(search: SearchSettings, embedding: EmbeddingSettings) -> SearchIndex:
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SimpleField(name="doc_id", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SearchableField(name="section", type=SearchFieldDataType.String),
        SimpleField(
            name="doc_type",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=embedding.dimensions,
            vector_search_profile_name=VECTOR_PROFILE,
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name=HNSW_CONFIG)],
        profiles=[VectorSearchProfile(name=VECTOR_PROFILE, algorithm_configuration_name=HNSW_CONFIG)],
    )

    # Defined so the semantic ranker can be switched on later without a rebuild.
    # Queries default to plain hybrid; see grounding/search.py.
    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name=SEMANTIC_CONFIG,
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="title"),
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[SemanticField(field_name="section")],
                ),
            )
        ]
    )

    return SearchIndex(
        name=search.index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )


def create_or_update_index(search: SearchSettings, embedding: EmbeddingSettings) -> SearchIndex:
    client = build_index_client(search)
    return client.create_or_update_index(build_index(search, embedding))


def delete_index(search: SearchSettings) -> None:
    build_index_client(search).delete_index(search.index_name)
