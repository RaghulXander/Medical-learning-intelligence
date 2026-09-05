import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.services.generation.m19d_pilot import (
    M19D_EMBEDDING_RUN_ID,
    M19D_RETRIEVAL_CONFIG_HASH,
    M19DPilotService,
    PilotBlueprintRow,
    ProviderCandidate,
    ProviderOption,
    ProviderReceipt,
    evidence_packet_hash,
    load_blueprint,
    shuffle_candidate,
    validate_evidence_mapping,
)
from backend.services.hybrid_retrieval_service import (
    HybridEvidenceReceipt,
    HybridRetrievalOutcome,
)
from database.models import Base, DocumentChunk, QuestionStatus, Source, SourceDocument, SourceType
from scripts.run_m19d_text_pilot import validate_acceptance_report


ROOT = Path(__file__).resolve().parent.parent
BLUEPRINT_PATH = ROOT / "data/generation/blueprints/m19d_text_pilot_v1.json"
REPORT_PATH = ROOT / "data/evaluation/retrieval/reports/m19c_retrieval_eval_v1.json"


def make_row() -> PilotBlueprintRow:
    return PilotBlueprintRow(
        id="m19d-general-01",
        domain="general_pathology",
        topic="Cell injury",
        subtopic="Coagulative necrosis",
        learning_objective="Relate ischemic myocardial injury to coagulative necrosis.",
        retrieval_query="ischemic myocardial infarction coagulative necrosis morphology",
        target_exam="NEET_SS",
        difficulty="MEDIUM",
        cognitive_level="APPLICATION",
        question_type="SINGLE_BEST_ANSWER",
        source_requirements=["robbins_pathologic_basis_11th"],
        minimum_evidence_count=1,
    )


def make_receipt() -> HybridEvidenceReceipt:
    return HybridEvidenceReceipt(
        rank=1,
        chunk_id="chunk-1",
        content_hash="chunk-hash-1",
        source_id="source-1",
        source_short_name="robbins_pathologic_basis_11th",
        source_title="Robbins & Cotran Pathologic Basis of Disease",
        edition="11th Edition",
        pdf_page=55,
        textbook_page=39,
        chapter_name="Cell Injury",
        section_heading="Necrosis",
        dense_score=0.8,
        lexical_score=0.2,
        fused_score=0.9,
        embedding_run_id=M19D_EMBEDDING_RUN_ID,
        retrieval_configuration_hash=M19D_RETRIEVAL_CONFIG_HASH,
        content=(
            "Ischemic injury in solid organs generally produces coagulative necrosis. "
            "The affected tissue initially retains its basic architecture."
        ),
    )


def make_candidate() -> ProviderCandidate:
    return ProviderCandidate(
        stem="A myocardial infarct shows preserved tissue outlines after ischemic cell injury. Which necrosis pattern is most likely?",
        options=[
            ProviderOption(text="Coagulative necrosis", is_correct=True, rationale="Ischemic myocardial injury produces this pattern.", evidence_chunk_ids=["chunk-1"]),
            ProviderOption(text="Liquefactive necrosis", is_correct=False, rationale="This is not the described ischemic myocardial pattern.", evidence_chunk_ids=["chunk-1"]),
            ProviderOption(text="Caseous necrosis", is_correct=False, rationale="This does not match the retained myocardial architecture.", evidence_chunk_ids=["chunk-1"]),
            ProviderOption(text="Fat necrosis", is_correct=False, rationale="This does not match the involved tissue or mechanism.", evidence_chunk_ids=["chunk-1"]),
        ],
        explanation="The ischemic myocardial cell injury produces coagulative necrosis with temporary preservation of tissue outlines.",
        explanation_evidence_chunk_ids=["chunk-1"],
    )


def test_blueprint_has_accepted_shape_and_hashes():
    blueprint, blueprint_hash = load_blueprint(BLUEPRINT_PATH)
    assert blueprint.status == "APPROVED"
    assert blueprint.is_approved is True
    assert len(blueprint.rows) == 50
    assert len(blueprint_hash) == 64
    assert {row.domain for row in blueprint.rows} == {
        "diagnostic_techniques",
        "general_pathology",
        "hematopathology",
        "neoplasia",
        "systemic_pathology",
    }


def test_acceptance_report_is_bound_to_blueprint():
    blueprint, _ = load_blueprint(BLUEPRINT_PATH)
    report = validate_acceptance_report(REPORT_PATH, blueprint)
    assert report["gate_passed"] is True
    assert report["recall_at_5"] == pytest.approx(0.98)


def test_shuffle_is_reproducible_and_remaps_answer():
    candidate = make_candidate()
    first = shuffle_candidate(candidate, seed_material="blueprint:row")
    second = shuffle_candidate(candidate, seed_material="blueprint:row")
    assert first == second
    options, correct, _ = first
    assert len(options) == 4
    assert sum(item["is_correct"] for item in options) == 1
    assert next(item["id"] for item in options if item["is_correct"]) == correct


def test_mapping_rejects_an_invented_chunk_id():
    candidate = make_candidate()
    candidate.options[1].evidence_chunk_ids = ["invented"]
    with pytest.raises(ValueError, match="absent evidence"):
        validate_evidence_mapping(candidate, [make_receipt()])


def test_evidence_packet_hash_excludes_source_text():
    first = make_receipt()
    second_payload = first.to_dict()
    second_payload["content"] = "Different private source text with identical provenance."
    second = HybridEvidenceReceipt(**second_payload)
    assert evidence_packet_hash([first]) == evidence_packet_hash([second])


class FakeRetrieval:
    def __init__(self, receipt):
        self.receipt = receipt
        self.calls = 0

    def search(self, *_args, **kwargs):
        self.calls += 1
        assert kwargs["embedding_run_id"] == M19D_EMBEDDING_RUN_ID
        return HybridRetrievalOutcome(
            status="OK",
            query="test",
            embedding_run_id=M19D_EMBEDDING_RUN_ID,
            retrieval_configuration_hash=M19D_RETRIEVAL_CONFIG_HASH,
            results=[self.receipt],
        )


class FakeGenerator:
    def __init__(self):
        self.calls = 0

    def generate(self, *, row, evidence):
        self.calls += 1
        return make_candidate(), ProviderReceipt(
            provider="test_vertex",
            model="test-model",
            model_version="1",
            project="test-project",
            location="test-location",
            prompt_version="test-prompt",
            response_id="response-1",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            latency_ms=10,
        )


def test_service_persists_human_review_candidate_and_resumes_idempotently():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    source = Source(
        id="source-1",
        short_name="robbins_pathologic_basis_11th",
        title="Robbins & Cotran Pathologic Basis of Disease",
        edition="11th Edition",
        source_type=SourceType.TEXTBOOK,
    )
    document = SourceDocument(
        id="document-1",
        source_id=source.id,
        title="Robbins 11th",
        edition="11th Edition",
        file_hash="document-hash",
    )
    chunk = DocumentChunk(
        id="chunk-1",
        document_id=document.id,
        slice_id="slice-1",
        chunk_index=0,
        pdf_page=55,
        textbook_page=39,
        page_number=55,
        chapter_name="Cell Injury",
        section_heading="Necrosis",
        content=make_receipt().content,
        content_hash="chunk-hash-1",
        word_count=20,
        metadata_json={},
    )
    session.add_all([source, document, chunk])
    session.commit()

    retrieval = FakeRetrieval(make_receipt())
    generator = FakeGenerator()
    service = M19DPilotService(
        retrieval=retrieval,
        generator=generator,
        blueprint_id="m19d-text-pilot-v1",
        blueprint_hash="b" * 64,
    )
    question, created = service.generate_row(session, make_row())
    assert created is True
    assert question.status in {QuestionStatus.HUMAN_REVIEW, QuestionStatus.AI_REVIEW}
    assert question.status != QuestionStatus.APPROVED
    assert question.classification_confidence == question.quality_score
    assert question.evidence_links[0].excerpt is None
    assert question.metadata_json["provider_receipt"]["response_id"] == "response-1"
    assert question.metadata_json["citations"][0].endswith("p. 39")

    same_question, created_again = service.generate_row(session, make_row())
    assert created_again is False
    assert same_question.id == question.id
    assert retrieval.calls == 1
    assert generator.calls == 1
    session.close()
