"""Embedding client for the corpus.

Uses the project's Azure OpenAI endpoint with your `az login` identity rather
than an API key, so the same credential covers Foundry and embeddings.
"""

from __future__ import annotations

from functools import lru_cache

from azure.identity import AzureCliCredential, get_bearer_token_provider
from openai import AzureOpenAI

from agentic_sdlc.config import EmbeddingSettings

COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"

# Azure OpenAI caps how many inputs one embeddings call accepts.
_BATCH_SIZE = 16


@lru_cache(maxsize=1)
def _credential() -> AzureCliCredential:
    return AzureCliCredential()


def build_embedding_client(settings: EmbeddingSettings) -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=settings.openai_endpoint,
        api_version=settings.api_version,
        azure_ad_token_provider=get_bearer_token_provider(_credential(), COGNITIVE_SERVICES_SCOPE),
    )


def embed_texts(
    client: AzureOpenAI,
    settings: EmbeddingSettings,
    texts: list[str],
) -> list[list[float]]:
    """Embed a list of texts, batching to stay within request limits."""
    vectors: list[list[float]] = []
    for start in range(0, len(texts), _BATCH_SIZE):
        batch = texts[start : start + _BATCH_SIZE]
        response = client.embeddings.create(
            model=settings.deployment,
            input=batch,
            dimensions=settings.dimensions,
        )
        vectors.extend(item.embedding for item in response.data)
    return vectors


def embed_query(client: AzureOpenAI, settings: EmbeddingSettings, query: str) -> list[float]:
    return embed_texts(client, settings, [query])[0]
