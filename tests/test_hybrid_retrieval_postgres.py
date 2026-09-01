from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from backend.services.embedding_service import DeterministicMockEmbeddingProvider
from backend.services.hybrid_retrieval_service import HybridRetrievalService
from database.db import get_engine
from database.models import (
    DocumentChunk,
    DocumentChunkEmbedding,
    EmbeddingRun,
    EmbeddingRunStatus,
)


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="requires the configured disposable PostgreSQL test transaction",
)


def test_postgres_hybrid_query_and_receipt_resolve_without_persisting_rows():
    provider = DeterministicMockEmbeddingProvider()
    connection = get_engine().connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        chunk = session.query(DocumentChunk).filter(DocumentChunk.content != "").first()
        assert chunk is not None
        terms = [term for term in re.findall(r"[A-Za-z]{6,}", chunk.content) if term]
        assert terms

        run_id = str(uuid.uuid4())
        run = EmbeddingRun(
            id=run_id,
            provider="mock_test_only",
            model_id=provider.model_name,
            dimension=provider.dimension,
            chunking_version="postgres-integration-test",
            status=EmbeddingRunStatus.COMPLETED,
            expected_chunk_count=1,
            completed_chunk_count=1,
            config_hash="c" * 64,
            completed_at=datetime.now(timezone.utc),
        )
        session.add(run)
        session.add(
            DocumentChunkEmbedding(
                id=str(uuid.uuid4()),
                run_id=run_id,
                chunk_id=chunk.id,
                content_hash=chunk.content_hash,
                embedding=provider.embed_text(chunk.content),
            )
        )
        session.flush()

        outcome = HybridRetrievalService(embedding_provider=provider).search(
            session,
            terms[0],
            embedding_run_id=run_id,
            top_k=1,
        )

        assert outcome.status == "OK"
        assert outcome.results[0].chunk_id == chunk.id
        assert outcome.results[0].content_hash == chunk.content_hash
        assert outcome.results[0].embedding_run_id == run_id
    finally:
        session.close()
        transaction.rollback()
        connection.close()
