"""
tests/test_evidence_retrieval.py

Unit & Integration Test Suite for Reference Evidence Ingestion,
Vector Embedding Generation, and Semantic Retrieval Services.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool
from database.models import Base, DocumentChunk, Source, SourceDocument, SourceType
from backend.services.embedding_service import (
    DeterministicMockEmbeddingProvider,
    cosine_similarity,
)
from backend.services.retrieval_service import RetrievalService
from backend.api.main import app
from backend.api.routes.evidence import get_db


@pytest.fixture
def test_db_session():
    """Provides an isolated in-memory SQLite database session populated with test chunks."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()

    # Create Source
    source = Source(
        id="src-robbins-11e",
        short_name="robbins_pathologic_basis_11th",
        title="Robbins & Cotran Pathologic Basis of Disease",
        edition="11th",
        year=2024,
        source_type=SourceType.TEXTBOOK,
    )
    session.add(source)
    session.flush()

    # Create SourceDocument
    source_doc = SourceDocument(
        id="sdoc-robbins-11e-vol1",
        source_id=source.id,
        title="Robbins & Cotran Pathologic Basis of Disease (11th Edition)",
        edition="11th",
        file_hash="c43661f8d57ee7a29382d030a42620d270d7cb90f52c32817fe6bebae5e10129",
    )
    session.add(source_doc)
    session.flush()

    provider = DeterministicMockEmbeddingProvider(dimension=768)

    # Chunk 1: Neoplasia & HER2
    c1_text = (
        "HER2 (ERBB2) gene amplification occurs in approximately 15% to 20% of breast cancers. "
        "Overexpression is assessed by immunohistochemistry (IHC) on a 0 to 3+ scale, where 3+ is positive. "
        "Equivocal 2+ cases require confirmatory in situ hybridization (ISH) for gene amplification."
    )
    chunk1 = DocumentChunk(
        id="chunk-her2-breast",
        document_id=source_doc.id,
        slice_id="robbins_p0256_p0270",
        chunk_index=0,
        pdf_page=263,
        textbook_page=247,
        page_number=263,
        chapter_name="Chapter 7: Neoplasia",
        section_heading="Molecular Basis of Cancer",
        content=c1_text,
        content_hash="hash-her2-breast-001",
        word_count=len(c1_text.split()),
        embedding=provider.embed_text(c1_text),
        embedding_model=provider.model_name,
        metadata_json={"tags": ["breast", "her2", "ihc"]},
    )

    # Chunk 2: Plasma Cell Neoplasms & Russell Bodies
    c2_text = (
        "Plasma cell neoplasms frequently display Russell bodies (intracytoplasmic inclusions of IgG) "
        "and Dutcher bodies (intranuclear pseudoinclusions). In Mott cells, the cytoplasm is crowded "
        "with grapelike clusters of Russell bodies."
    )
    chunk2 = DocumentChunk(
        id="chunk-russell-bodies",
        document_id=source_doc.id,
        slice_id="robbins_p0600_p0615",
        chunk_index=1,
        pdf_page=610,
        textbook_page=592,
        page_number=610,
        chapter_name="Chapter 13: Diseases of White Blood Cells",
        section_heading="Plasma Cell Myeloma",
        content=c2_text,
        content_hash="hash-russell-bodies-002",
        word_count=len(c2_text.split()),
        embedding=provider.embed_text(c2_text),
        embedding_model=provider.model_name,
        metadata_json={"tags": ["hematopathology", "myeloma", "russell_bodies"]},
    )

    session.add_all([chunk1, chunk2])
    session.commit()

    yield session

    session.close()


def test_cosine_similarity():
    """Verifies cosine similarity mathematics."""
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    vec_c = [0.0, 1.0, 0.0]
    vec_d = [-1.0, 0.0, 0.0]

    assert pytest.approx(cosine_similarity(vec_a, vec_b), 0.001) == 1.0
    assert pytest.approx(cosine_similarity(vec_a, vec_c), 0.001) == 0.0
    assert pytest.approx(cosine_similarity(vec_a, vec_d), 0.001) == -1.0
    assert cosine_similarity([], []) == 0.0


def test_deterministic_embedding_provider():
    """Verifies deterministic embedding provider consistency and unit length."""
    provider = DeterministicMockEmbeddingProvider(dimension=768)

    emb1 = provider.embed_text("HER2 amplification in breast adenocarcinoma")
    emb2 = provider.embed_text("HER2 amplification in breast adenocarcinoma")
    emb3 = provider.embed_text("Russell bodies in plasma cell myeloma")

    assert len(emb1) == 768
    assert emb1 == emb2  # Deterministic consistency
    assert emb1 != emb3  # Distinct topics produce distinct vectors

    sim_same = cosine_similarity(emb1, emb2)
    assert pytest.approx(sim_same, 0.001) == 1.0


def test_retrieval_service_semantic_search(test_db_session):
    """Tests semantic search ranking and citation formatting."""
    provider = DeterministicMockEmbeddingProvider(dimension=768)
    service = RetrievalService(embedding_provider=provider)

    results = service.search_evidence(
        db=test_db_session,
        query="HER2 breast cancer IHC 3+ equivocal",
        top_k=5,
        min_score=0.1,
    )

    assert len(results) >= 1
    top_result = results[0]
    assert top_result.chunk_id == "chunk-her2-breast"
    assert top_result.pdf_page == 263
    assert top_result.textbook_page == 247
    assert top_result.chapter_name == "Chapter 7: Neoplasia"
    assert "Robbins & Cotran Pathologic Basis of Disease, 11th Ed., p. 247 (Chapter 7: Neoplasia)" in top_result.citation_label
    assert "HER2" in top_result.content


def test_retrieval_service_filters(test_db_session):
    """Tests chapter and page range filters in retrieval service."""
    provider = DeterministicMockEmbeddingProvider(dimension=768)
    service = RetrievalService(embedding_provider=provider)

    # Filter for hematopathology chapter
    results_hema = service.search_evidence(
        db=test_db_session,
        query="Russell bodies Mott cells",
        chapter_filter="White Blood Cells",
        min_score=0.1,
    )
    assert len(results_hema) == 1
    assert results_hema[0].chunk_id == "chunk-russell-bodies"

    # Filter with non-matching document short_name
    results_empty = service.search_evidence(
        db=test_db_session,
        query="HER2 amplification",
        doc_filter="non_existent_book",
    )
    assert len(results_empty) == 0


def test_evidence_api_endpoints(test_db_session):
    """Tests REST API endpoints for evidence search and lookup."""
    app.dependency_overrides[get_db] = lambda: test_db_session
    client = TestClient(app)

    # Test POST /api/evidence/search
    search_payload = {
        "query": "HER2 breast cancer immunohistochemistry",
        "top_k": 3,
        "min_score": 0.1,
    }
    response = client.post("/api/evidence/search", json=search_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == search_payload["query"]
    assert data["total_found"] >= 1
    assert data["results"][0]["pdf_page"] == 263

    # Test GET /api/evidence/stats
    stats_resp = client.get("/api/evidence/stats")
    assert stats_resp.status_code == 200
    stats_data = stats_resp.json()
    assert stats_data["total_chunks"] == 2
    assert len(stats_data["documents"]) == 1

    # Test GET /api/evidence/{chunk_id}
    chunk_resp = client.get("/api/evidence/chunk-her2-breast")
    assert chunk_resp.status_code == 200
    chunk_data = chunk_resp.json()
    assert chunk_data["chunk_id"] == "chunk-her2-breast"
    assert chunk_data["chapter_name"] == "Chapter 7: Neoplasia"

    # Test GET 404 for invalid chunk
    not_found_resp = client.get("/api/evidence/invalid-chunk-uuid")
    assert not_found_resp.status_code == 404

    app.dependency_overrides.clear()
