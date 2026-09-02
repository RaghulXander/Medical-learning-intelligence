from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from database.models import (
    Base,
    DocumentChunk,
    ImageAsset,
    ImageOccurrence,
    ImageTextEvidenceLink,
    Source,
    SourceDocument,
)
from scripts.sync_remote_image_catalog import (
    CatalogSyncConflict,
    sync_image_catalog,
    sync_storage_uris,
)


SOURCE_ID = "11111111-1111-1111-1111-111111111111"
DOCUMENT_ID = "22222222-2222-2222-2222-222222222222"
CHUNK_ID = "33333333-3333-3333-3333-333333333333"
ASSET_ID = "44444444-4444-4444-4444-444444444444"
OCCURRENCE_ID = "55555555-5555-5555-5555-555555555555"
LINK_ID = "66666666-6666-6666-6666-666666666666"


def _engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _seed_text(engine, *, chunk_hash="chunk-hash"):
    with engine.begin() as connection:
        connection.execute(
            Source.__table__.insert(),
            {
                "id": SOURCE_ID,
                "short_name": "robbins_review",
                "title": "Authorized review source",
            },
        )
        connection.execute(
            SourceDocument.__table__.insert(),
            {
                "id": DOCUMENT_ID,
                "source_id": SOURCE_ID,
                "title": "Authorized review document",
                "file_hash": "document-hash",
            },
        )
        connection.execute(
            DocumentChunk.__table__.insert(),
            {
                "id": CHUNK_ID,
                "document_id": DOCUMENT_ID,
                "chunk_index": 0,
                "pdf_page": 7,
                "content": "Synthetic test evidence only.",
                "content_hash": chunk_hash,
                "word_count": 4,
            },
        )


def _seed_catalog(engine):
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        connection.execute(
            ImageAsset.__table__.insert(),
            {
                "id": ASSET_ID,
                "sha256": "a" * 64,
                "pixel_hash": "b" * 64,
                "filename": "synthetic.png",
                "storage_uri": "private/test/synthetic.png",
                "width": 32,
                "height": 32,
                "aspect_ratio": 1.0,
                "file_size_bytes": 128,
                "format": "PNG",
                "triage_class": "AUTO_KEEP_CANDIDATE",
                "curation_status": "CURATED_VALID",
                "rights_status": "RESTRICTED_INTERNAL",
                "entropy": 0.5,
                "blank_score": 0.0,
                "is_exact_duplicate": False,
                "metadata": {"fixture": True},
                "created_at": now,
            },
        )
        connection.execute(
            ImageOccurrence.__table__.insert(),
            {
                "id": OCCURRENCE_ID,
                "image_asset_id": ASSET_ID,
                "source_document_id": DOCUMENT_ID,
                "pdf_page": 7,
                "textbook_page": 2,
                "figure_index": 1,
                "figure_label": "Figure 1",
                "extraction_id": "synthetic-extraction",
                "is_canonical": True,
                "metadata": {},
                "created_at": now,
            },
        )
        connection.execute(
            ImageTextEvidenceLink.__table__.insert(),
            {
                "id": LINK_ID,
                "image_asset_id": ASSET_ID,
                "document_chunk_id": CHUNK_ID,
                "link_type": "PAGE_CO_OCCURRENCE",
                "confidence": 0.9,
                "verification_status": "AI_SUGGESTED",
                "created_at": now,
            },
        )


def test_dry_run_execute_and_idempotence():
    remote = _engine()
    local = _engine()
    _seed_text(remote)
    _seed_text(local)
    _seed_catalog(remote)

    dry_run = sync_image_catalog(
        remote,
        local,
        source_names=("robbins_review",),
        require_postgres=False,
    )
    assert dry_run["status"] == "DRY_RUN_VALID"
    assert dry_run["inserts"]["image_assets"] == 1
    with local.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(ImageAsset)) == 0

    executed = sync_image_catalog(
        remote,
        local,
        source_names=("robbins_review",),
        execute=True,
        require_postgres=False,
    )
    assert executed["status"] == "SYNCED_AND_VERIFIED"
    assert executed["counts"] == {
        "image_assets": 1,
        "image_occurrences": 1,
        "image_text_evidence_links": 1,
    }

    repeated = sync_image_catalog(
        remote,
        local,
        source_names=("robbins_review",),
        execute=True,
        require_postgres=False,
    )
    assert repeated["inserts"] == {
        "image_assets": 0,
        "image_occurrences": 0,
        "image_text_evidence_links": 0,
    }
    assert repeated["updates"] == {
        "image_assets": 0,
        "image_occurrences": 0,
        "image_text_evidence_links": 0,
    }


def test_refuses_local_text_hash_conflict():
    remote = _engine()
    local = _engine()
    _seed_text(remote)
    _seed_text(local, chunk_hash="different-local-hash")
    _seed_catalog(remote)

    with pytest.raises(CatalogSyncConflict, match="hash-conflicted"):
        sync_image_catalog(
            remote,
            local,
            source_names=("robbins_review",),
            execute=True,
            require_postgres=False,
        )


def test_storage_uri_only_refresh_is_hash_checked():
    remote = _engine()
    local = _engine()
    _seed_text(remote)
    _seed_text(local)
    _seed_catalog(remote)
    _seed_catalog(local)

    with remote.begin() as connection:
        connection.execute(
            ImageAsset.__table__.update()
            .where(ImageAsset.id == ASSET_ID)
            .values(storage_uri="https://private.example/synthetic.png")
        )

    result = sync_storage_uris(
        remote,
        local,
        source_names=("robbins_review",),
        execute=True,
        require_postgres=False,
    )
    assert result["updates"]["image_asset_storage_uris"] == 1
    with local.connect() as connection:
        assert connection.scalar(
            select(ImageAsset.storage_uri).where(ImageAsset.id == ASSET_ID)
        ) == "https://private.example/synthetic.png"
