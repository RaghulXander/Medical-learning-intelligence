from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.domain.surgical_pathology_ontology import (
    OntologyMappingReviewDecision,
    OntologyMappingRunStatus,
    OntologyMappingMethod,
)
from backend.services.ontology.question_mapping_service import (
    QuestionOntologyMappingService,
    normalize_mapping_text,
)
from database.models import (
    Base,
    OntologyAlias,
    OntologyNode,
    Question,
    QuestionOntologyMapping,
    QuestionStatus,
    VerificationStatus,
)
from scripts.seed_surgical_pathology_ontology import seed_surgical_pathology_ontology


def _question(question_id: str, topic: str, status=QuestionStatus.IMPORTED) -> Question:
    return Question(
        id=question_id,
        external_source="test",
        external_source_id=f"external-{question_id}",
        subject="Pathology",
        speciality="Pathology",
        topic_name_original=topic,
        topic_name_normalized=topic,
        stem="Synthetic test stem",
        options=[{"key": "A", "text": "One"}, {"key": "B", "text": "Two"}],
        correct_option="A",
        correct_index=0,
        status=status,
        content_hash=f"content-{question_id}",
        exact_stem_hash=f"exact-{question_id}",
        norm_stem_hash=f"norm-{question_id}",
    )


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    seed_surgical_pathology_ontology(engine)
    return sessionmaker(bind=engine)()


def test_normalization_is_unicode_case_and_punctuation_stable():
    assert normalize_mapping_text("  Invasive—Lobular  Carcinoma ") == "invasive lobular carcinoma"
    assert normalize_mapping_text("MAMMARY gland") == "mammary gland"


def test_preview_matches_preferred_name_and_alias_without_writing():
    session = _session()
    session.add_all([
        _question("q-breast", "Breast"),
        _question("q-mammary", "Mammary Gland"),
        _question("q-unknown", "General pathology"),
    ])
    session.commit()

    preview = QuestionOntologyMappingService().preview(
        session,
        scheme_code="SURGICAL-PATHOLOGY",
        ontology_version="2026.08-draft.1",
    )

    assert preview.input_count == 3
    assert {item.question_id for item in preview.candidates} == {"q-breast", "q-mammary"}
    assert {item.node_code for item in preview.candidates} == {"SP-BREAST"}
    assert preview.unmapped_question_ids == ["q-unknown"]
    assert session.query(QuestionOntologyMapping).count() == 0


def test_ambiguous_alias_is_reported_and_not_applied():
    session = _session()
    breast = session.query(OntologyNode).filter_by(code="SP-BREAST").one()
    kidney = session.query(OntologyNode).filter_by(code="SP-GU-KIDNEY").one()
    session.add_all([
        OntologyAlias(
            node_id=breast.id,
            alias="Shared label",
            verification_status=VerificationStatus.AI_SUGGESTED,
        ),
        OntologyAlias(
            node_id=kidney.id,
            alias="Shared label",
            verification_status=VerificationStatus.AI_SUGGESTED,
        ),
        _question("q-ambiguous", "Shared label"),
    ])
    session.commit()

    preview = QuestionOntologyMappingService().preview(
        session,
        scheme_code="SURGICAL-PATHOLOGY",
        ontology_version="2026.08-draft.1",
    )

    assert not preview.candidates
    assert preview.ambiguous[0].candidate_node_codes == ["SP-BREAST", "SP-GU-KIDNEY"]


def test_apply_is_suggested_preserves_question_status_and_rollback_is_non_destructive():
    session = _session()
    question = _question("q-apply", "Breast", status=QuestionStatus.HUMAN_REVIEW)
    session.add(question)
    session.commit()
    service = QuestionOntologyMappingService()
    preview = service.preview(
        session,
        scheme_code="SURGICAL-PATHOLOGY",
        ontology_version="2026.08-draft.1",
    )

    run = service.apply(session, preview, actor="test-rule")
    session.commit()
    mapping = session.query(QuestionOntologyMapping).one()

    assert run.status == OntologyMappingRunStatus.APPLIED
    assert mapping.verification_status == VerificationStatus.AI_SUGGESTED
    assert mapping.is_active is True
    assert mapping.match_metadata["confidence_semantics"] == "exact_lexical_match_not_medical_verification"
    assert session.get(Question, question.id).status == QuestionStatus.HUMAN_REVIEW

    second_preview = service.preview(
        session,
        scheme_code="SURGICAL-PATHOLOGY",
        ontology_version="2026.08-draft.1",
    )
    assert second_preview.skipped_existing_count == 1
    assert not second_preview.candidates

    deactivated = service.rollback(session, run.id, actor="test-reviewer")
    session.commit()
    assert deactivated == 1
    assert mapping.is_active is False
    assert run.status == OntologyMappingRunStatus.ROLLED_BACK
    assert session.get(Question, question.id).status == QuestionStatus.HUMAN_REVIEW


def test_human_correction_supersedes_suggestion_without_changing_question_status():
    session = _session()
    question = _question("q-correct", "Breast", status=QuestionStatus.IMPORTED)
    session.add(question)
    session.commit()
    service = QuestionOntologyMappingService()
    preview = service.preview(
        session,
        scheme_code="SURGICAL-PATHOLOGY",
        ontology_version="2026.08-draft.1",
    )
    run = service.apply(session, preview, actor="test-rule")
    session.commit()
    suggestion = session.query(QuestionOntologyMapping).filter_by(mapping_run_id=run.id).one()

    corrected = service.review(
        session,
        suggestion.id,
        decision=OntologyMappingReviewDecision.CORRECT,
        reviewer="human-reviewer",
        corrected_node_code="SP-BREAST-DCIS",
    )
    session.commit()

    assert suggestion.is_active is False
    assert corrected is not None
    assert corrected.is_active is True
    assert corrected.mapping_method == OntologyMappingMethod.HUMAN
    assert corrected.verification_status == VerificationStatus.HUMAN_VERIFIED
    assert corrected.supersedes_mapping_id == suggestion.id
    assert corrected.node.code == "SP-BREAST-DCIS"
    assert session.get(Question, question.id).status == QuestionStatus.IMPORTED

    # Rolling back the automated run does not erase an independent human correction.
    assert service.rollback(session, run.id, actor="rollback-operator") == 0
    session.commit()
    assert corrected.is_active is True


def test_human_rejection_deactivates_suggestion_without_replacement():
    session = _session()
    session.add(_question("q-reject", "Breast"))
    session.commit()
    service = QuestionOntologyMappingService()
    run = service.apply(
        session,
        service.preview(
            session,
            scheme_code="SURGICAL-PATHOLOGY",
            ontology_version="2026.08-draft.1",
        ),
        actor="test-rule",
    )
    session.commit()
    suggestion = session.query(QuestionOntologyMapping).filter_by(mapping_run_id=run.id).one()

    replacement = service.review(
        session,
        suggestion.id,
        decision=OntologyMappingReviewDecision.REJECT,
        reviewer="human-reviewer",
    )
    session.commit()

    assert replacement is None
    assert suggestion.is_active is False
    assert suggestion.verification_status == VerificationStatus.REJECTED
