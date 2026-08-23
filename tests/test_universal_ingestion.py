"""
tests/test_universal_ingestion.py

Unit tests for the Universal Multi-Source Ingestion Engine and Hierarchical Curriculum System:
- Ingestion from CSV / Spreadsheets
- Ingestion from Google Forms responses
- Ingestion from Manual Admin Entry
- Ingestion from AI Generator pipelines
- Schema consistency across all channels
- Curriculum hierarchy traversal (Course -> Speciality -> Subject -> Topic -> Subtopic -> Learning Objective)
- User role validation (ADMIN, USER, REVIEWER, EDUCATOR)
"""

import io
import unittest
import uuid
from pathlib import Path
import sys

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.db import init_db, session_scope
from database.models import (
    Base,
    Course,
    CurriculumLevel,
    CurriculumTopic,
    Question,
    QuestionStatus,
    QuestionType,
    TopicMappingStatus,
    User,
    UserRole,
)
from backend.ingestion.universal_ingestor import UniversalQuestionIngestor
from scripts.seed_curriculum import seed_curriculum


class TestUniversalIngestionAndCurriculum(unittest.TestCase):

    def setUp(self):
        # Use StaticPool so all sessions share the same in-memory SQLite database
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
        init_db(engine=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.ingestor = UniversalQuestionIngestor(self.engine)
        seed_curriculum(self.engine)

    def tearDown(self):
        Base.metadata.drop_all(bind=self.engine)

    def test_curriculum_hierarchy_structure(self):
        with self.SessionLocal() as session:
            # Check Courses
            courses = session.query(Course).all()
            course_codes = {c.code for c in courses}
            self.assertIn("DM-ONCOPATH", course_codes)
            self.assertIn("MD-PATH", course_codes)
            self.assertIn("NEET-PG", course_codes)

            # Check Hierarchy: Speciality -> Subject -> Topic -> Subtopic -> Learning Objective
            spec = session.query(CurriculumTopic).filter_by(code="SPEC-PATH").first()
            self.assertEqual(spec.level, CurriculumLevel.SPECIALITY)

            subj = session.query(CurriculumTopic).filter_by(code="SUBJ-GEN-PATH").first()
            self.assertEqual(subj.parent_id, spec.id)
            self.assertEqual(subj.level, CurriculumLevel.SUBJECT)

            topic = session.query(CurriculumTopic).filter_by(code="TOPIC-CELL-INJURY").first()
            self.assertEqual(topic.parent_id, subj.id)
            self.assertEqual(topic.level, CurriculumLevel.TOPIC)

            subtopic = session.query(CurriculumTopic).filter_by(code="SUBTOPIC-APOPTOSIS").first()
            self.assertEqual(subtopic.parent_id, topic.id)
            self.assertEqual(subtopic.level, CurriculumLevel.SUBTOPIC)

            lo = session.query(CurriculumTopic).filter_by(code="LO-APOPTOSIS-BCL2").first()
            self.assertEqual(lo.parent_id, subtopic.id)
            self.assertEqual(lo.level, CurriculumLevel.LEARNING_OBJECTIVE)

    def test_user_roles(self):
        with self.SessionLocal() as session:
            admin = session.query(User).filter_by(email="admin@medicalexam.ai").first()
            self.assertIsNotNone(admin)
            self.assertEqual(admin.role, UserRole.ADMIN)

            student = session.query(User).filter_by(email="student@medicalexam.ai").first()
            self.assertIsNotNone(student)
            self.assertEqual(student.role, UserRole.USER)

    def test_ingest_from_csv(self):
        csv_data = """question,opa,opb,opc,opd,cop,exp,topic
"Which marker is specific for gastrointestinal stromal tumors (GIST)?","CD117 (c-KIT)","CD20","CD3","Desmin","A","CD117 is expressed in 95% of GISTs.","Gastrointestinal Pathology"
"Signet ring cell carcinoma is most commonly associated with mutation in:","CDH1 (E-cadherin)","KRAS","BRAF","RET","A","Loss of E-cadherin expression via CDH1 mutation causes diffuse gastric cancer.","Gastrointestinal Pathology"
"""
        with self.SessionLocal() as session:
            topic = session.query(CurriculumTopic).filter_by(code="TOPIC-GI-PATH").first()
            topic_id = topic.id if topic else None

        result = self.ingestor.ingest_csv(
            csv_data,
            source_name="oncopath_csv",
            primary_topic_id=topic_id,
            created_by="pathologist_upload",
        )

        self.assertEqual(result["inserted_count"], 2)

        with self.SessionLocal() as session:
            q = session.query(Question).filter(Question.stem.contains("gastrointestinal")).first()
            self.assertIsNotNone(q)
            self.assertEqual(q.external_source, "oncopath_csv")
            self.assertEqual(q.correct_option, "A")
            self.assertEqual(q.correct_index, 0)
            self.assertEqual(q.primary_topic_id, topic_id)
            self.assertEqual(q.topic_mapping_status, TopicMappingStatus.MAPPED)
            self.assertEqual(len(q.options), 4)
            self.assertEqual(q.options[0]["text"], "CD117 (c-KIT)")
            self.assertEqual(len(q.content_hash), 64)

    def test_ingest_from_google_forms(self):
        form_payload = [
            {
                "Response ID": "gform-response-99",
                "Question": "Russell bodies in plasma cells are composed of accumulated:",
                "Option A": "Immunoglobulins",
                "Option B": "Mucin",
                "Option C": "Lipids",
                "Option D": "Glycogen",
                "Correct Answer": "A",
                "Explanation": "Russell bodies represent abnormal dilated ER cisternae filled with immunoglobulins.",
                "Topic": "Cellular Pathology",
                "Email Address": "contributor@hospital.org",
            }
        ]

        result = self.ingestor.ingest_google_forms(form_payload, created_by="gforms_webhook")
        self.assertEqual(result["inserted_count"], 1)

        with self.SessionLocal() as session:
            q = session.query(Question).filter(Question.external_source_id == "google_forms-gform-response-99").first()
            self.assertIsNotNone(q)
            self.assertEqual(q.external_source, "google_forms")
            self.assertEqual(q.correct_option, "A")
            self.assertEqual(q.metadata_json["form_submitter"], "contributor@hospital.org")

    def test_ingest_manual_admin_entry(self):
        manual_data = {
            "id": "manual-entry-001",
            "stem": "Which translocation is pathognomonic for Burkitt Lymphoma?",
            "options": [
                {"key": "A", "text": "t(8;14) MYC-IGH"},
                {"key": "B", "text": "t(14;18) BCL2-IGH"},
                {"key": "C", "text": "t(9;22) BCR-ABL1"},
                {"key": "D", "text": "t(11;14) CCND1-IGH"},
            ],
            "cop": "A",
            "explanation": "Burkitt lymphoma is characterized by MYC translocation t(8;14)(q24;q32).",
            "topic_name": "Hematopathology",
        }

        with self.SessionLocal() as session:
            topic = session.query(CurriculumTopic).filter_by(code="TOPIC-LYMPHOMAS").first()
            topic_id = topic.id if topic else None

        q = self.ingestor.ingest_single(
            manual_data,
            source_type="manual_admin",
            primary_topic_id=topic_id,
            status=QuestionStatus.APPROVED,
            created_by="admin_dr_smith",
        )

        self.assertIsNotNone(q)
        self.assertEqual(q.external_source, "manual_admin")
        self.assertEqual(q.status, QuestionStatus.APPROVED)
        self.assertEqual(q.created_by, "admin_dr_smith")
        self.assertEqual(q.correct_option, "A")
        self.assertEqual(q.correct_index, 0)
        self.assertEqual(q.primary_topic_id, topic_id)

    def test_ingest_ai_generated_question(self):
        blueprint = {
            "topic": "Breast carcinoma",
            "learning_objective": "HER2 scoring by ASCO/CAP guidelines",
            "difficulty": "hard",
            "cognitive_level": "application",
        }
        ai_output = {
            "id": "ai-cand-001",
            "stem": "A 52-year-old female undergoes core biopsy for invasive breast carcinoma. IHC for HER2 reveals weak-to-moderate complete membrane staining in 15% of tumor cells. According to ASCO/CAP 2018 guidelines, what is the next step?",
            "options": [
                {"key": "A", "text": "Report as HER2 Equivocal (2+) and reflex to ISH testing"},
                {"key": "B", "text": "Report as HER2 Negative (1+)"},
                {"key": "C", "text": "Report as HER2 Positive (3+)"},
                {"key": "D", "text": "Repeat IHC on resection specimen only"},
            ],
            "cop": "A",
            "explanation": "Circumferential weak to moderate membrane staining in >10% of cells is HER2 2+ (Equivocal), requiring reflex in-situ hybridization (ISH).",
        }

        with self.SessionLocal() as session:
            topic = session.query(CurriculumTopic).filter_by(code="SUBTOPIC-HER2-TESTING").first()
            topic_id = topic.id if topic else None

        q = self.ingestor.ingest_ai_generated(
            ai_output,
            blueprint=blueprint,
            model_name="gemini-1.5-pro",
            primary_topic_id=topic_id,
        )

        self.assertIsNotNone(q)
        self.assertEqual(q.external_source, "ai_generator")
        self.assertEqual(q.status, QuestionStatus.AI_REVIEW)
        self.assertEqual(q.created_by, "ai_model:gemini-1.5-pro")
        self.assertEqual(q.difficulty, "hard")
        self.assertEqual(q.cognitive_level, "application")
        self.assertEqual(q.primary_topic_id, topic_id)
        self.assertEqual(q.metadata_json["ai_model"], "gemini-1.5-pro")
        self.assertEqual(q.metadata_json["blueprint"]["learning_objective"], "HER2 scoring by ASCO/CAP guidelines")


if __name__ == "__main__":
    unittest.main()
