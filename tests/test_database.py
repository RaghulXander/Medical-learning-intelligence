"""
tests/test_database.py

Unit and integration tests for the Medical Exam AI database layer:
- Table initialization and schema validation
- Model constraints and relationships (Course, Topic, Mapping, Source, Document, Chunk, Evidence, Review, Report)
- Cross-course topic mappings with depth levels (Undergraduate, Postgraduate, Super-Specialty)
- JSONB options and metadata queries
- JSONL batch ingestion and idempotency
"""

import json
import tempfile
import unittest
from pathlib import Path
import sys

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from database.models import (
    Base,
    Course,
    CourseCurriculumMapping,
    CurriculumLevel,
    CurriculumTopic,
    DepthLevel,
    DocumentChunk,
    Question,
    QuestionEvidence,
    QuestionReport,
    QuestionReview,
    QuestionStatus,
    QuestionType,
    ReportCategory,
    ReportStatus,
    ReviewerType,
    Source,
    SourceDocument,
    SourceType,
    TopicMappingStatus,
    User,
    UserRole,
    VerificationStatus,
)
from database.db import init_db
from scripts.import_to_db import (
    FOUNDATIONAL_SOURCES,
    import_questions_from_jsonl,
    seed_sources_and_curriculum,
)
from scripts.seed_curriculum import seed_curriculum


class TestDatabaseLayer(unittest.TestCase):

    def setUp(self):
        # Create an in-memory SQLite database with StaticPool for isolated testing
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
        init_db(engine=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def tearDown(self):
        Base.metadata.drop_all(bind=self.engine)

    def test_schema_creation_and_tables(self):
        table_names = Base.metadata.tables.keys()
        expected_tables = {
            "users",
            "courses",
            "curriculum_topics",
            "course_curriculum_mappings",
            "sources",
            "source_documents",
            "document_chunks",
            "questions",
            "question_evidence",
            "question_reviews",
            "question_reports",
        }
        for t in expected_tables:
            self.assertIn(t, table_names)

    def test_seed_sources_and_curriculum(self):
        seed_curriculum(self.engine)
        with self.SessionLocal() as session:
            # Check Sources
            sources_count = session.query(Source).count()
            self.assertEqual(sources_count, len(FOUNDATIONAL_SOURCES))

            robbins = session.query(Source).filter_by(short_name="robbins_pathology").first()
            self.assertIsNotNone(robbins)
            self.assertEqual(robbins.source_type, SourceType.TEXTBOOK)
            self.assertEqual(robbins.edition, "11th Edition")
            self.assertEqual(
                session.query(SourceDocument).filter_by(source_id=robbins.id).count(),
                0,
            )

            # Check Canonical Knowledge Domain Tree
            spec = session.query(CurriculumTopic).filter_by(code="SPEC-PATH").first()
            self.assertIsNotNone(spec)
            self.assertEqual(spec.level, CurriculumLevel.SPECIALITY)

            subj = session.query(CurriculumTopic).filter_by(code="SUBJ-GEN-PATH").first()
            self.assertIsNotNone(subj)
            self.assertEqual(subj.parent_id, spec.id)

            # Check Cross-Course Topic Mappings
            breast_topic = session.query(CurriculumTopic).filter_by(code="TOPIC-BREAST-PATH").first()
            self.assertIsNotNone(breast_topic)
            mappings = session.query(CourseCurriculumMapping).filter_by(topic_id=breast_topic.id).all()
            self.assertEqual(len(mappings), 4)  # Mapped to DM, MD, NEET-PG, MBBS

            dm_map = next(m for m in mappings if m.course.code == "DM-ONCOPATH")
            mbbs_map = next(m for m in mappings if m.course.code == "MBBS-PATH")
            self.assertEqual(dm_map.depth_level, DepthLevel.SUPER_SPECIALTY)
            self.assertEqual(mbbs_map.depth_level, DepthLevel.UNDERGRADUATE)

    def test_evidence_and_document_provenance_linkages(self):
        seed_curriculum(self.engine)
        with self.SessionLocal() as session:
            source = Source(
                short_name="automated_test_source",
                title="Automated Test Editorial Source",
                author="Test suite",
                source_type=SourceType.JOURNAL_ARTICLE,
            )
            session.add(source)
            session.flush()
            doc = SourceDocument(
                source_id=source.id,
                title="Synthetic test document",
                chapter_number=1,
            )
            session.add(doc)
            session.flush()
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=0,
                section_heading="Synthetic section",
                page_number=1,
                content="Synthetic evidence used only to test database relationships.",
                content_hash="synthetic_test_chunk_hash",
            )
            session.add(chunk)
            session.flush()

            q = Question(
                id="q-evidence-test",
                external_source="manual",
                external_source_id="manual-ev-1",
                stem="Which drug targets HER2 amplification in breast carcinoma?",
                options=[{"key": "A", "text": "Trastuzumab"}, {"key": "B", "text": "Imatinib"}],
                correct_option="A",
                correct_index=0,
                content_hash="hash_ev_doc",
                exact_stem_hash="hash_stem_doc",
                norm_stem_hash="hash_norm_stem_doc",
            )
            session.add(q)
            session.flush()

            evidence = QuestionEvidence(
                question_id=q.id,
                source_id=source.id,
                document_id=doc.id,
                chunk_id=chunk.id,
                chapter="Synthetic chapter 1",
                page_range="p. 1",
                section="Synthetic section",
                excerpt="Synthetic evidence used only to test database relationships.",
                verification_status=VerificationStatus.HUMAN_VERIFIED,
                confidence=1.0,
            )
            session.add(evidence)
            session.commit()

            q_fetched = session.query(Question).filter_by(id="q-evidence-test").first()
            self.assertEqual(len(q_fetched.evidence_links), 1)
            ev = q_fetched.evidence_links[0]
            self.assertEqual(ev.verification_status, VerificationStatus.HUMAN_VERIFIED)
            self.assertEqual(ev.source.short_name, "automated_test_source")
            self.assertEqual(ev.document.title, "Synthetic test document")
            self.assertEqual(ev.chunk.page_number, 1)

    def test_init_db_adds_missing_question_columns(self):
        legacy_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )

        with legacy_engine.begin() as conn:
            conn.exec_driver_sql(
                "CREATE TABLE questions ("
                "id TEXT PRIMARY KEY, "
                "external_source VARCHAR(50) NOT NULL DEFAULT 'medmcqa', "
                "external_source_id VARCHAR(100) NOT NULL UNIQUE, "
                "speciality VARCHAR(100) NOT NULL DEFAULT 'Pathology', "
                "subject VARCHAR(100) NOT NULL DEFAULT 'Pathology', "
                "topic_name_original VARCHAR(255), "
                "topic_name_normalized VARCHAR(255), "
                "learning_objective TEXT, "
                "question_type VARCHAR(50) NOT NULL DEFAULT 'single_best_answer', "
                "stem TEXT NOT NULL, "
                "options JSON NOT NULL, "
                "correct_option CHAR(1), "
                "correct_index INT NOT NULL DEFAULT -1, "
                "is_labeled BOOLEAN NOT NULL DEFAULT TRUE, "
                "explanation TEXT, "
                "difficulty VARCHAR(20), "
                "cognitive_level VARCHAR(20), "
                "status VARCHAR(50) NOT NULL DEFAULT 'IMPORTED', "
                "quality_score FLOAT, "
                "content_hash CHAR(64) NOT NULL, "
                "exact_stem_hash CHAR(64) NOT NULL, "
                "norm_stem_hash CHAR(64) NOT NULL, "
                "metadata JSON NOT NULL DEFAULT '{}', "
                "created_by VARCHAR(100) NOT NULL DEFAULT 'system_import', "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP "
                ");"
            )

        init_db(engine=legacy_engine)

        with legacy_engine.begin() as conn:
            cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(questions)").fetchall()]
        self.assertIn("educational_level", cols)
        self.assertIn("target_exam_levels", cols)

    def test_batch_import_from_jsonl(self):
        sample_records = [
            {
                "id": "b1-uuid",
                "external_source": "medmcqa",
                "external_source_id": "medmcqa-b1",
                "speciality": "Pathology",
                "subject": "Pathology",
                "topic_name_original": "Neoplasia",
                "topic_name_normalized": "Neoplasia",
                "topic_mapping_status": "RAW_ONLY",
                "question_type": "single_best_answer",
                "stem": "Hallmark of malignancy is:",
                "options": [{"key": "A", "text": "Invasion and Metastasis"}, {"key": "B", "text": "Hyperplasia"}],
                "correct_option": "A",
                "correct_index": 0,
                "is_labeled": True,
                "explanation": "Metastasis unequivocally proves malignancy.",
                "status": "IMPORTED",
                "content_hash": "hash_b1",
                "exact_stem_hash": "exact_b1",
                "norm_stem_hash": "norm_b1",
                "created_at": "2026-08-23T12:00:00Z",
                "updated_at": "2026-08-23T12:00:00Z",
                "metadata": {"split": "train"},
            }
        ]

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".jsonl", delete=False, encoding="utf-8") as tmp:
            for r in sample_records:
                tmp.write(json.dumps(r) + "\n")
            tmp_path = Path(tmp.name)

        try:
            stats = import_questions_from_jsonl(tmp_path, self.engine, batch_size=1)
            self.assertEqual(stats["total_read"], 1)
            self.assertEqual(stats["total_inserted"], 1)

            with self.SessionLocal() as session:
                self.assertEqual(session.query(Question).count(), 1)
        finally:
            tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()
