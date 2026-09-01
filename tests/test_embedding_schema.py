from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.services.embedding_service import (
    EmbeddingProviderError,
    GeminiEmbeddingProvider,
)
from database.models import (
    Base,
    DocumentChunk,
    DocumentChunkEmbedding,
    EmbeddingRun,
    EmbeddingRunStatus,
    Source,
    SourceDocument,
    SourceType,
)


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_versioned_embedding_is_scoped_to_run_and_chunk():
    session = _session()
    source = Source(
        id="source-1",
        short_name="book",
        title="Book",
        source_type=SourceType.TEXTBOOK,
    )
    document = SourceDocument(id="document-1", source=source, title="Book")
    chunk = DocumentChunk(
        id="chunk-1",
        document=document,
        content="Evidence",
        content_hash="a" * 64,
        word_count=1,
    )
    run = EmbeddingRun(
        id="run-1",
        provider="google_vertex_ai",
        model_id="gemini-embedding-001",
        dimension=768,
        chunking_version="document-chunks-v1",
        status=EmbeddingRunStatus.COMPLETED,
        expected_chunk_count=1,
        completed_chunk_count=1,
        config_hash="b" * 64,
        completed_at=datetime.now(timezone.utc),
    )
    record = DocumentChunkEmbedding(
        id="embedding-1",
        run=run,
        chunk=chunk,
        content_hash=chunk.content_hash,
        embedding=[0.0] * 767 + [1.0],
    )
    session.add(record)
    session.commit()

    assert run.embeddings == [record]
    assert chunk.embedding_records == [record]
    assert len(record.embedding) == 768

    duplicate = DocumentChunkEmbedding(
        id="embedding-2",
        run_id=run.id,
        chunk_id=chunk.id,
        content_hash=chunk.content_hash,
        embedding=[1.0] + [0.0] * 767,
    )
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        session.commit()


class _FailingModels:
    def embed_content(self, **_kwargs):
        raise RuntimeError("provider unavailable")


class _FailingClient:
    models = _FailingModels()


def test_configured_remote_provider_never_falls_back_to_mock(monkeypatch):
    monkeypatch.setattr(GeminiEmbeddingProvider, "_init_client", lambda self: None)
    provider = GeminiEmbeddingProvider(api_key="configured-test-key")
    provider._client = _FailingClient()
    monkeypatch.setattr("backend.services.embedding_service.time.sleep", lambda _seconds: None)

    with pytest.raises(EmbeddingProviderError, match="after 3 attempts"):
        provider.embed_batch(["medical evidence"])
