"""Chunk the corpus, embed it, and push it into Azure AI Search.

Push-model indexing rather than an indexer plus skillset: fewer moving parts,
no waiting on a scheduled run, and the chunking is right here in Python where
participants can see and change it.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from agentic_sdlc.config import EmbeddingSettings, SearchSettings
from agentic_sdlc.grounding.embeddings import build_embedding_client, embed_texts

MANIFEST_NAME = "manifest.json"
MAX_CHUNK_CHARS = 1400
UPLOAD_BATCH = 50


@dataclass
class Chunk:
    id: str
    doc_id: str
    title: str
    section: str
    doc_type: str
    content: str


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "section"


def _split_oversized(text: str) -> list[str]:
    """Split a long section on paragraph boundaries, never mid-sentence."""
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]

    parts: list[str] = []
    buffer = ""
    for paragraph in text.split("\n\n"):
        if buffer and len(buffer) + len(paragraph) + 2 > MAX_CHUNK_CHARS:
            parts.append(buffer.strip())
            buffer = paragraph
        else:
            buffer = f"{buffer}\n\n{paragraph}" if buffer else paragraph
    if buffer.strip():
        parts.append(buffer.strip())
    return parts


def chunk_markdown(text: str, doc_id: str, title: str, doc_type: str) -> list[Chunk]:
    """Split on level-2 headings, then on paragraphs if a section runs long.

    Heading-aligned chunks mean a citation can name a real section, which is
    what makes the citations in the artifacts checkable by a human.
    """
    sections: list[tuple[str, str]] = []
    current_heading = "Overview"
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    chunks: list[Chunk] = []
    for heading, body in sections:
        if not body:
            continue
        for position, piece in enumerate(_split_oversized(body)):
            suffix = f"-{position}" if position else ""
            chunks.append(
                Chunk(
                    id=f"{doc_id}--{_slug(heading)}{suffix}",
                    doc_id=doc_id,
                    title=title,
                    section=heading,
                    doc_type=doc_type,
                    content=piece,
                )
            )
    return chunks


def load_corpus(corpus_dir: Path) -> list[Chunk]:
    """Read every document listed in the corpus manifest and chunk it."""
    manifest_path = corpus_dir / MANIFEST_NAME
    if not manifest_path.exists():
        raise FileNotFoundError(f"Corpus manifest not found at {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunks: list[Chunk] = []
    for entry in manifest["documents"]:
        path = corpus_dir / entry["file"]
        if not path.exists():
            raise FileNotFoundError(f"Corpus file {path} listed in manifest but missing")
        chunks.extend(
            chunk_markdown(
                text=path.read_text(encoding="utf-8"),
                doc_id=entry["doc_id"],
                title=entry["title"],
                doc_type=entry["doc_type"],
            )
        )
    return chunks


def ingest(
    search: SearchSettings,
    embedding: EmbeddingSettings,
    corpus_dir: Path,
) -> int:
    """Embed and upload the whole corpus. Returns the number of chunks indexed."""
    chunks = load_corpus(corpus_dir)
    if not chunks:
        return 0

    embed_client = build_embedding_client(embedding)
    vectors = embed_texts(embed_client, embedding, [chunk.content for chunk in chunks])

    documents = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        document = asdict(chunk)
        document["content_vector"] = vector
        documents.append(document)

    search_client = SearchClient(
        endpoint=search.endpoint,
        index_name=search.index_name,
        credential=AzureKeyCredential(search.api_key),
    )
    for start in range(0, len(documents), UPLOAD_BATCH):
        search_client.upload_documents(documents[start : start + UPLOAD_BATCH])

    return len(documents)
