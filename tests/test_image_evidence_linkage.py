"""
tests/test_image_evidence_linkage.py

Unit tests for Milestone 18C Image-to-Text Evidence Linkage Engine and ORM models.
"""

import json
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
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
from scripts.link_images_to_evidence import ImageEvidenceLinker


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Seed source and document
    from database.models import SourceType

    source = Source(
        id=str(uuid.uuid4()),
        title="Robbins & Cotran Pathologic Basis of Disease",
        short_name="robbins_pathologic_basis_11th",
        source_type=SourceType.TEXTBOOK,
    )
    session.add(source)

    doc = SourceDocument(
        id=str(uuid.uuid4()),
        source_id=source.id,
        title="Pathologic Basis of Disease 11th Edition",
    )
    session.add(doc)

    # Seed Chunks
    # Chunk 1 on page 70 with explicit figure citation
    c1 = DocumentChunk(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        pdf_page=70,
        textbook_page=54,
        content="The gross specimen in Fig. 1 shows extensive coagulative necrosis with pale architecture.",
        content_hash="hash-chunk-1",
    )
    # Chunk 2 on page 70 with general description
    c2 = DocumentChunk(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        pdf_page=70,
        textbook_page=54,
        content="Apoptosis differs morphologically from necrosis by cellular shrinkage.",
        content_hash="hash-chunk-2",
    )
    # Chunk 3 on page 71 (adjacent page)
    c3 = DocumentChunk(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        pdf_page=71,
        textbook_page=55,
        content="Ischemic injury progression in renal tubules.",
        content_hash="hash-chunk-3",
    )
    session.add_all([c1, c2, c3])
    session.commit()

    yield session
    session.close()


def test_find_matching_chunks_citation_and_cooccurrence(test_db):
    linker = ImageEvidenceLinker(db_session=test_db, dry_run=True)
    doc_id = list(linker.doc_map.values())[0]

    # Test exact page with Figure 1 match
    matches = linker.find_matching_chunks(
        document_id=doc_id,
        pdf_page=70,
        textbook_page=54,
        fig_idx=1,
    )

    assert len(matches) == 2
    types = [m[1] for m in matches]
    confidences = [m[2] for m in matches]

    assert "FIGURE_CITATION" in types
    assert "PAGE_CO_OCCURRENCE" in types
    assert 0.98 in confidences
    assert 0.90 in confidences


def test_find_matching_chunks_adjacent_page_fallback(test_db):
    linker = ImageEvidenceLinker(db_session=test_db, dry_run=True)
    doc_id = list(linker.doc_map.values())[0]

    # Page 72 has no exact chunk, should match page 71 (adjacent)
    matches = linker.find_matching_chunks(
        document_id=doc_id,
        pdf_page=72,
        textbook_page=56,
        fig_idx=1,
    )

    assert len(matches) == 1
    assert matches[0][1] == "ADJACENT_PAGE_CO_OCCURRENCE"
    assert matches[0][2] == 0.75


def test_link_manifest_creates_orm_records(test_db, tmp_path):
    manifest_file = tmp_path / "test_manifest.json"
    manifest_data = {
        "images": [
            {
                "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                "filename": "img-robins-p0070-f001.png",
                "source_short_name": "robbins_pathologic_basis_11th",
                "pdf_page": 70,
                "textbook_page": 54,
                "figure_index": 1,
                "width": 800,
                "height": 600,
                "aspect_ratio": 1.3333,
                "file_size_bytes": 125000,
                "triage_class": "AUTO_KEEP_CANDIDATE",
            }
        ]
    }
    manifest_file.write_text(json.dumps(manifest_data))

    linker = ImageEvidenceLinker(db_session=test_db, dry_run=False)
    stats = linker.link_manifest(manifest_path=manifest_file)

    assert stats["total_images"] == 1
    assert stats["assets_created"] == 1
    assert stats["occurrences_created"] == 1
    assert stats["links_created"] == 2  # 1 figure citation + 1 page co-occurrence

    # Check database records
    assets = test_db.query(ImageAsset).all()
    assert len(assets) == 1
    assert assets[0].filename == "img-robins-p0070-f001.png"

    occurrences = test_db.query(ImageOccurrence).all()
    assert len(occurrences) == 1
    assert occurrences[0].figure_label == "Figure 1"

    links = test_db.query(ImageTextEvidenceLink).all()
    assert len(links) == 2
