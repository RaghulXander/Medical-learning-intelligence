from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.orm import Session

from backend.domain.surgical_pathology_ontology import OntologyMappingRunStatus
from backend.services.ontology.question_mapping_service import QuestionOntologyMappingService
from database.db import get_engine
from database.models import Question, QuestionOntologyMapping, QuestionStatus


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="requires the configured rollback-only PostgreSQL test transaction",
)


def test_postgres_mapping_apply_and_rollback_preserve_question_state():
    connection = get_engine().connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    question_id = str(uuid.uuid4())
    try:
        question = Question(
            id=question_id,
            external_source="m14_integration_test",
            external_source_id=f"m14-integration-{question_id}",
            subject="M14_TEST_PATHOLOGY",
            speciality="Pathology",
            topic_name_original="Breast",
            topic_name_normalized="Breast",
            stem="Synthetic integration test stem",
            options=[{"key": "A", "text": "One"}, {"key": "B", "text": "Two"}],
            correct_option="A",
            correct_index=0,
            status=QuestionStatus.IMPORTED,
            content_hash=f"content-{question_id}",
            exact_stem_hash=f"exact-{question_id}",
            norm_stem_hash=f"norm-{question_id}",
        )
        session.add(question)
        session.flush()

        service = QuestionOntologyMappingService()
        preview = service.preview(
            session,
            scheme_code="SURGICAL-PATHOLOGY",
            ontology_version="2026.08-draft.1",
            subject="M14_TEST_PATHOLOGY",
        )
        assert len(preview.candidates) == 1

        run = service.apply(session, preview, actor="postgres-test")
        session.flush()
        mapping = (
            session.query(QuestionOntologyMapping)
            .filter_by(mapping_run_id=run.id)
            .one()
        )
        assert mapping.is_active is True
        assert question.status == QuestionStatus.IMPORTED

        assert service.rollback(session, run.id, actor="postgres-test") == 1
        session.flush()
        assert mapping.is_active is False
        assert run.status == OntologyMappingRunStatus.ROLLED_BACK
        assert question.status == QuestionStatus.IMPORTED
    finally:
        session.close()
        transaction.rollback()
        connection.close()
