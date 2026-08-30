"""
tests/test_question_generation.py

Unit & Integration Test Suite for Evidence-Grounded AI Question Generation,
Multi-Signal Evaluation Engine, and Editorial Review Pipeline.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.models import (
    Base,
    DocumentChunk,
    Question,
    QuestionEvidence,
    QuestionStatus,
    Source,
    SourceDocument,
    SourceType,
    User,
    UserRole,
    VerificationStatus,
)
from backend.services.embedding_service import DeterministicMockEmbeddingProvider
from backend.services.generation.evaluator import QuestionEvaluator
from backend.services.generation.generator import MockEvidenceGroundedGenerator
from backend.services.generation.models import (
    GeneratedMCQPayload,
    GeneratedOption,
    QuestionBlueprint,
)
from backend.services.generation.service import QuestionGenerationService
from backend.services.retrieval_service import EvidenceSearchResult, RetrievalService
from backend.api.main import app
from backend.api.routes.questions import get_db
from backend.api.routes.auth import get_current_user


@pytest.fixture
def gen_test_db():
    """Provides an isolated in-memory SQLite database populated with Robbins reference chunks."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()

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

    source_doc = SourceDocument(
        id="sdoc-robbins-11e",
        source_id=source.id,
        title="Robbins Pathologic Basis 11e",
        edition="11th",
        file_hash="hash-12345",
    )
    session.add(source_doc)
    session.flush()

    provider = DeterministicMockEmbeddingProvider(dimension=768)

    chunk_text = (
        "HER2 (ERBB2) gene amplification occurs in approximately 15% to 20% of breast cancers. "
        "Overexpression is assessed by immunohistochemistry (IHC) on a 0 to 3+ scale, where 3+ is positive. "
        "Equivocal 2+ cases require confirmatory in situ hybridization (ISH) for gene amplification."
    )
    chunk = DocumentChunk(
        id="chunk-her2-breast-test",
        document_id=source_doc.id,
        slice_id="slice-001",
        chunk_index=0,
        pdf_page=961,
        textbook_page=945,
        page_number=961,
        chapter_name="CHAPTER 23 The Breast",
        section_heading="Molecular Subtypes",
        content=chunk_text,
        content_hash="hash-her2-chunk",
        word_count=len(chunk_text.split()),
        embedding=provider.embed_text(chunk_text),
        embedding_model=provider.model_name,
        metadata_json={},
    )
    session.add(chunk)

    # Add an editor user for API tests
    editor = User(
        id="user-editor-1",
        email="editor@medical-exam.ai",
        name="Pathology Editor",
        role=UserRole.ADMIN,
        is_email_verified=True,
    )
    session.add(editor)
    session.commit()

    yield session
    session.close()


def test_question_blueprint_schema():
    """Verifies QuestionBlueprint data structure and serialization."""
    bp = QuestionBlueprint(
        topic="Breast Carcinoma",
        learning_objective="HER2 testing and ISH equivocal algorithm",
        difficulty="HARD",
        cognitive_level="APPLICATION",
        target_exam="NEET_SS",
    )
    data = bp.to_dict()
    assert data["topic"] == "Breast Carcinoma"
    assert data["difficulty"] == "HARD"
    assert data["target_exam"] == "NEET_SS"


def test_mock_generator_output():
    """Verifies that Mock generator formats valid MCQs with citations."""
    bp = QuestionBlueprint(
        topic="Breast Carcinoma",
        learning_objective="HER2 IHC testing",
    )
    ev = EvidenceSearchResult(
        chunk_id="c1",
        document_title="Robbins",
        document_short_name="robbins_11e",
        edition="11th",
        pdf_page=961,
        textbook_page=945,
        chapter_name="Breast",
        section_heading="Neoplasia",
        content="HER2 gene amplification occurs in 15% of breast cancers. 3+ is positive on IHC.",
        content_hash="h1",
        word_count=20,
        similarity_score=0.9,
        citation_label="Robbins 11th Ed., p. 945",
        metadata={},
    )

    generator = MockEvidenceGroundedGenerator()
    mcq = generator.generate_mcq(blueprint=bp, evidence=[ev])

    assert mcq.correct_option == "A"
    assert len(mcq.options) == 4
    assert mcq.options[0].is_correct is True
    assert "Robbins 11th Ed., p. 945" in mcq.citations[0]
    assert "HER2" in mcq.stem or "breast" in mcq.stem.lower()


def test_evaluator_valid_mcq():
    """Verifies that evaluator approves well-formed grounded MCQs."""
    evaluator = QuestionEvaluator()
    mcq = GeneratedMCQPayload(
        stem="Which of the following is the definitive diagnostic marker for classical Hodgkin lymphoma?",
        options=[
            GeneratedOption(key="A", text="CD20 and CD79a", is_correct=False, rationale="B-cell markers negative in classic RS cells"),
            GeneratedOption(key="B", text="CD30 and CD15", is_correct=True, rationale="Positive in Reed-Sternberg cells"),
            GeneratedOption(key="C", text="CD3 and CD5", is_correct=False, rationale="T-cell markers"),
            GeneratedOption(key="D", text="CD68 and CD163", is_correct=False, rationale="Histiocytic markers"),
        ],
        correct_option="B",
        explanation="Option B is correct. Reed-Sternberg cells in classical Hodgkin lymphoma are characteristically positive for CD30 and CD15, while lacking CD20 (Option A).",
        learning_objective="Immunohistochemistry of Hodgkin Lymphoma",
        difficulty="MEDIUM",
        cognitive_level="RECALL",
        question_type="SINGLE_BEST_ANSWER",
        evidence_chunk_ids=["chunk-123"],
        citations=["Robbins & Cotran 11th Ed., p. 580"],
    )

    res = evaluator.evaluate_mcq(mcq)
    assert res.passed is True
    assert res.status_assigned == "GENERATED"
    assert res.overall_score >= 0.85


def test_evaluator_catches_inconsistent_answers():
    """Verifies that evaluator rejects questions where explanation contradicts correct_option."""
    evaluator = QuestionEvaluator()
    mcq = GeneratedMCQPayload(
        stem="Sample question stem?",
        options=[
            GeneratedOption(key="A", text="Option A", is_correct=True, rationale="Declared correct"),
            GeneratedOption(key="B", text="Option B", is_correct=False, rationale="Incorrect"),
            GeneratedOption(key="C", text="Option C", is_correct=False, rationale="Incorrect"),
            GeneratedOption(key="D", text="Option D", is_correct=False, rationale="Incorrect"),
        ],
        correct_option="C",  # Contradiction: declares C but option A is marked is_correct
        explanation="Option C is not correct actually.",
        learning_objective="Testing",
        difficulty="EASY",
        cognitive_level="RECALL",
        question_type="SINGLE_BEST_ANSWER",
        evidence_chunk_ids=["chunk-1"],
        citations=["Robbins p. 10"],
    )

    res = evaluator.evaluate_mcq(mcq)
    assert res.passed is False
    assert res.status_assigned == "REJECTED"


def test_evaluator_catches_meta_distractors():
    """Verifies that evaluator penalizes forbidden 'all of the above' phrases."""
    evaluator = QuestionEvaluator()
    mcq = GeneratedMCQPayload(
        stem="Sample question stem?",
        options=[
            GeneratedOption(key="A", text="Finding 1", is_correct=False, rationale="Rationale A"),
            GeneratedOption(key="B", text="Finding 2", is_correct=False, rationale="Rationale B"),
            GeneratedOption(key="C", text="All of the above", is_correct=True, rationale="Rationale C"),
            GeneratedOption(key="D", text="None of the above", is_correct=False, rationale="Rationale D"),
        ],
        correct_option="C",
        explanation="Option C is correct because both findings apply.",
        learning_objective="Testing",
        difficulty="EASY",
        cognitive_level="RECALL",
        question_type="SINGLE_BEST_ANSWER",
        evidence_chunk_ids=["chunk-1"],
        citations=["Robbins p. 10"],
    )

    res = evaluator.evaluate_mcq(mcq)
    assert res.passed is False
    assert any("Forbidden meta-distractor phrase detected" in r for r in res.reasons)


def test_generation_service_end_to_end(gen_test_db):
    """Verifies end-to-end question generation, evaluation, and DB linkage."""
    provider = DeterministicMockEmbeddingProvider(dimension=768)
    retrieval_svc = RetrievalService(embedding_provider=provider)
    service = QuestionGenerationService(retrieval_service=retrieval_svc)
    generator = MockEvidenceGroundedGenerator()

    bp = QuestionBlueprint(
        topic="Breast Carcinoma",
        learning_objective="HER2 testing and ISH equivocal criteria",
        difficulty="HARD",
        cognitive_level="APPLICATION",
    )

    question, eval_result, mcq = service.generate_question_from_blueprint(
        db=gen_test_db,
        blueprint=bp,
        generator=generator,
        persist=True,
    )

    assert question.id is not None
    assert question.status == QuestionStatus.GENERATED
    assert question.speciality == "Pathology"
    assert question.topic_name_original == "Breast Carcinoma"
    assert len(question.options) == 4
    assert question.quality_score >= 0.85
    assert len(question.evidence_links) >= 1

    # Verify QuestionEvidence cryptographic provenance
    ev_link = question.evidence_links[0]
    assert ev_link.chunk_id == "chunk-her2-breast-test"
    assert ev_link.chapter == "CHAPTER 23 The Breast"
    assert ev_link.verification_status == VerificationStatus.AI_SUGGESTED


def test_api_generate_questions_endpoint(gen_test_db):
    """Verifies POST /api/questions/generate REST endpoint with editor authorization."""
    admin_user = gen_test_db.query(User).filter(User.email == "editor@medical-exam.ai").first()

    app.dependency_overrides[get_db] = lambda: gen_test_db
    app.dependency_overrides[get_current_user] = lambda: admin_user

    client = TestClient(app)

    payload = {
        "topic": "Breast Carcinoma",
        "learning_objective": "HER2 testing criteria",
        "difficulty": "MEDIUM",
        "cognitive_level": "APPLICATION",
        "count": 1,
        "force_mock": True,
    }

    response = client.post("/api/questions/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["generated_count"] == 1
    assert data["items"][0]["status"] == "GENERATED"
    assert len(data["items"][0]["options"]) == 4

    app.dependency_overrides.clear()
