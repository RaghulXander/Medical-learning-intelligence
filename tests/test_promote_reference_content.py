"""Tests for transactional, idempotent reference-content promotion."""

from __future__ import annotations

import hashlib

import pytest
from sqlalchemy import create_engine, func, select

from database.models import Base, DocumentChunk, Source, SourceDocument, SourceType
from scripts.promote_reference_content import (
    PromotionConflictError,
    promote_reference_content,
)


def _engine(path):
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    return engine


def _seed_source(engine) -> None:
    with engine.begin() as connection:
        for suffix, short_name in (
            ("review", "robbins_review"),
            ("basis", "robbins_pathologic_basis_11th"),
            ("sternberg", "sternberg_review_2nd"),
        ):
            source_id = f"source-{suffix}"
            document_id = f"document-{suffix}"
            content = f"Synthetic reference fixture for {suffix}."
            connection.execute(
                Source.__table__.insert(),
                {
                    "id": source_id,
                    "short_name": short_name,
                    "title": f"Synthetic {suffix}",
                    "edition": "test",
                    "source_type": SourceType.TEXTBOOK,
                },
            )
            connection.execute(
                SourceDocument.__table__.insert(),
                {
                    "id": document_id,
                    "source_id": source_id,
                    "title": f"Synthetic {suffix} document",
                    "edition": "test",
                    "page_start": 1,
                    "page_end": 1,
                    "file_hash": hashlib.sha256(suffix.encode()).hexdigest(),
                    "metadata": {},
                },
            )
            connection.execute(
                DocumentChunk.__table__.insert(),
                {
                    "id": f"chunk-{suffix}",
                    "document_id": document_id,
                    "slice_id": f"slice-{suffix}",
                    "chunk_index": 0,
                    "pdf_page": 1,
                    "page_number": 1,
                    "content": content,
                    "content_hash": hashlib.sha256(content.encode()).hexdigest(),
                    "word_count": len(content.split()),
                    "metadata": {},
                },
            )


def test_promotion_preserves_unrelated_rows_and_is_idempotent(tmp_path):
    source_engine = _engine(tmp_path / "source.db")
    target_engine = _engine(tmp_path / "target.db")
    _seed_source(source_engine)

    with target_engine.begin() as connection:
        connection.execute(
            Source.__table__.insert(),
            {
                "id": "unrelated-source",
                "short_name": "unrelated",
                "title": "Unrelated seed",
                "source_type": SourceType.TEXTBOOK,
            },
        )

    first = promote_reference_content(source_engine, target_engine)
    assert first["status"] == "PROMOTED_AND_VERIFIED"
    assert first["inserted_sources"] == 3
    assert first["inserted_chunks"] == 3

    second = promote_reference_content(source_engine, target_engine)
    assert second["inserted_sources"] == 0
    assert second["inserted_source_documents"] == 0
    assert second["inserted_chunks"] == 0
    assert second["skipped_existing_chunks"] == 3

    with target_engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(Source)).scalar_one() == 4
        assert connection.execute(select(func.count()).select_from(DocumentChunk)).scalar_one() == 3
        assert connection.execute(
            select(Source.id).where(Source.short_name == "unrelated")
        ).scalar_one() == "unrelated-source"

    source_engine.dispose()
    target_engine.dispose()


def test_promotion_rolls_back_on_stable_identity_conflict(tmp_path):
    source_engine = _engine(tmp_path / "source.db")
    target_engine = _engine(tmp_path / "target.db")
    _seed_source(source_engine)

    with target_engine.begin() as connection:
        connection.execute(
            Source.__table__.insert(),
            {
                "id": "wrong-id",
                "short_name": "robbins_review",
                "title": "Conflicting source",
                "source_type": SourceType.TEXTBOOK,
            },
        )

    with pytest.raises(PromotionConflictError):
        promote_reference_content(source_engine, target_engine)

    with target_engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(SourceDocument)).scalar_one() == 0
        assert connection.execute(select(func.count()).select_from(DocumentChunk)).scalar_one() == 0

    source_engine.dispose()
    target_engine.dispose()
