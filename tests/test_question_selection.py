"""
tests/test_question_selection.py

Comprehensive test suite for the Intelligent Question Selection & Learner Modeling Layer (Milestone 6).
Validates hard eligibility precedence, metadata cascading fallback, learner history tracking,
Laplace-smoothed accuracy, discrete recency penalties, diversity, deterministic selection, and explainability.
"""

import unittest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import (
    AssessmentAttempt,
    AssessmentType,
    AttemptQuestion,
    AttemptStatus,
    Base,
    ClassificationSource,
    ClassificationStatus,
    Course,
    CourseCurriculumMapping,
    CurriculumLevel,
    CurriculumTopic,
    DepthLevel,
    DifficultyLevel,
    EducationalLevel,
    MarkingScheme,
    Question,
    QuestionStatus,
    QuestionType,
    User,
    UserMastery,
    UserQuestionHistory,
    UserRole,
)
from backend.services.selection import (
    UniversalQuestionSelector,
    LearnerModelService,
    QuestionRanker,
    DiversityController,
    HardEligibilityFilter,
    BlueprintConfig,
    SelectionPolicy,
    InsufficientQuestionPoolError,
)
from backend.services.assessment_service import AssessmentService


class TestQuestionSelectionAndLearnerModel(unittest.TestCase):
    """Unit and integration tests for Milestone 6 Question Selection Engine."""

    @classmethod
    def setUpClass(cls):
        """Sets up in-memory SQLite database and seeds schema."""
        cls.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False)

    def setUp(self):
        self.db = self.SessionLocal()
        self._seed_fixtures()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def _seed_fixtures(self):
        """Seeds courses, curriculum nodes, users, marking schemes, and controlled question variations."""
        # 1. Marking Schemes
        scheme = MarkingScheme(id="NEET_4_1", name="NEET Standard (+4, -1)", correct_marks=4.0, penalty_marks=1.0, unanswered_marks=0.0)
        self.db.merge(scheme)

        # 2. User
        user = User(id="user-learner-01", email="learner@docedge.ai", name="Pathology Resident", role=UserRole.USER)
        self.db.merge(user)

        # 3. Courses
        c_dm = Course(id="course-dm-onco", code="DM-ONCOPATH", name="DM Oncopathology")
        c_pg = Course(id="course-neet-pg", code="NEET-PG", name="NEET PG Pathology")
        c_ug = Course(id="course-mbbs-path", code="MBBS-PATH", name="MBBS 2nd Year Pathology")
        for c in [c_dm, c_pg, c_ug]:
            self.db.merge(c)

        # 4. Curriculum Topics
        t_breast = CurriculumTopic(id="TOPIC-BREAST-PATH", code="BREAST-PATH", name="Breast Pathology", level=CurriculumLevel.TOPIC)
        t_hem = CurriculumTopic(id="TOPIC-HEMATO-PATH", code="HEMATO-PATH", name="Hematopathology", level=CurriculumLevel.TOPIC)
        t_gi = CurriculumTopic(id="TOPIC-GI-PATH", code="GI-PATH", name="GI Pathology", level=CurriculumLevel.TOPIC)
        for t in [t_breast, t_hem, t_gi]:
            self.db.merge(t)

        # 5. Course Curriculum Mappings
        m1 = CourseCurriculumMapping(id="map-1", course_id="course-dm-onco", topic_id="TOPIC-BREAST-PATH", depth_level=DepthLevel.SUPER_SPECIALTY, exam_weightage=20.0)
        m2 = CourseCurriculumMapping(id="map-2", course_id="course-neet-pg", topic_id="TOPIC-HEMATO-PATH", depth_level=DepthLevel.POSTGRADUATE, exam_weightage=15.0)
        m3 = CourseCurriculumMapping(id="map-3", course_id="course-mbbs-path", topic_id="TOPIC-GI-PATH", depth_level=DepthLevel.UNDERGRADUATE, exam_weightage=10.0)
        for m in [m1, m2, m3]:
            self.db.merge(m)

        # 6. Seed diverse questions with explicit, inferred, and unknown metadata
        # Question 1..5: NEET-SS / DM level Breast questions
        for i in range(1, 6):
            q = Question(
                id=f"q-ss-{i:02d}",
                external_source="docedge",
                external_source_id=f"ss-{i}",
                speciality="Pathology",
                subject="Pathology",
                primary_topic_id="TOPIC-BREAST-PATH",
                stem=f"Super-specialty breast vignette #{i}: HER2 testing algorithm in invasive ductal carcinoma.",
                options=[{"key": "A", "text": "Option A"}, {"key": "B", "text": "Option B"}],
                correct_option="A",
                correct_index=0,
                difficulty=DifficultyLevel.HARD if i <= 3 else DifficultyLevel.MEDIUM,
                educational_level=EducationalLevel.SUPER_SPECIALTY,
                target_exam_levels=["NEET_SS", "INI_CET"],
                status=QuestionStatus.APPROVED,
                classification_source=ClassificationSource.MANUAL,
                classification_status=ClassificationStatus.VERIFIED,
                classification_confidence=1.0,
                content_hash=f"hash-ss-{i}",
                exact_stem_hash=f"exact-ss-{i}",
                norm_stem_hash=f"norm-ss-{i}",
            )
            self.db.merge(q)

        # Question 6..10: MD / PG level Hemato questions
        for i in range(6, 11):
            q = Question(
                id=f"q-pg-{i:02d}",
                external_source="docedge",
                external_source_id=f"pg-{i}",
                speciality="Pathology",
                subject="Pathology",
                primary_topic_id="TOPIC-HEMATO-PATH",
                stem=f"Postgraduate hematopathology vignette #{i}: Flow cytometry immunophenotyping of lymphoma.",
                options=[{"key": "A", "text": "Option A"}, {"key": "B", "text": "Option B"}],
                correct_option="B",
                correct_index=1,
                difficulty=DifficultyLevel.MEDIUM,
                educational_level=EducationalLevel.MD,
                target_exam_levels=["NEET_PG", "NEET_SS"],
                status=QuestionStatus.APPROVED,
                classification_source=ClassificationSource.MANUAL,
                classification_status=ClassificationStatus.VERIFIED,
                classification_confidence=1.0,
                content_hash=f"hash-pg-{i}",
                exact_stem_hash=f"exact-pg-{i}",
                norm_stem_hash=f"norm-pg-{i}",
            )
            self.db.merge(q)

        # Question 11..13: MBBS level basic recall questions
        for i in range(11, 14):
            q = Question(
                id=f"q-ug-{i:02d}",
                external_source="medmcqa",
                external_source_id=f"ug-{i}",
                speciality="Pathology",
                subject="Pathology",
                primary_topic_id="TOPIC-GI-PATH",
                stem=f"Undergraduate basic recall question #{i}: Most common site of gastric ulcer.",
                options=[{"key": "A", "text": "Option A"}, {"key": "B", "text": "Option B"}],
                correct_option="A",
                correct_index=0,
                difficulty=DifficultyLevel.EASY,
                educational_level=EducationalLevel.MBBS,
                target_exam_levels=["NEET_UG"],
                status=QuestionStatus.APPROVED,
                classification_source=ClassificationSource.MANUAL,
                classification_status=ClassificationStatus.VERIFIED,
                classification_confidence=1.0,
                content_hash=f"hash-ug-{i}",
                exact_stem_hash=f"exact-ug-{i}",
                norm_stem_hash=f"norm-ug-{i}",
            )
            self.db.merge(q)

        # Question 14: Unclassified / Unknown metadata question
        q_unk = Question(
            id="q-unk-14",
            external_source="medmcqa_raw",
            external_source_id="raw-14",
            speciality="Pathology",
            subject="Pathology",
            primary_topic_id="TOPIC-BREAST-PATH",
            stem="Raw unclassified question: A case of breast mass with microcalcifications.",
            options=[{"key": "A", "text": "Option A"}, {"key": "B", "text": "Option B"}],
            correct_option="A",
            correct_index=0,
            difficulty=DifficultyLevel.MEDIUM,
            educational_level=None,
            target_exam_levels=[],
            status=QuestionStatus.APPROVED,
            classification_source=ClassificationSource.UNKNOWN,
            classification_status=ClassificationStatus.UNCLASSIFIED,
            classification_confidence=0.40,
            content_hash="hash-unk-14",
            exact_stem_hash="exact-unk-14",
            norm_stem_hash="norm-unk-14",
        )
        self.db.merge(q_unk)

        # Question 15: Surgery question (Wrong speciality)
        q_surg = Question(
            id="q-surg-15",
            external_source="medmcqa",
            external_source_id="surg-15",
            speciality="General Surgery",
            subject="Surgery",
            primary_topic_id="TOPIC-BREAST-PATH",
            stem="Surgical question: Triad of acute appendicitis.",
            options=[{"key": "A", "text": "Option A"}, {"key": "B", "text": "Option B"}],
            correct_option="A",
            correct_index=0,
            difficulty=DifficultyLevel.MEDIUM,
            educational_level=EducationalLevel.MD,
            target_exam_levels=["NEET_PG"],
            status=QuestionStatus.APPROVED,
            classification_source=ClassificationSource.MANUAL,
            classification_status=ClassificationStatus.VERIFIED,
            classification_confidence=1.0,
            content_hash="hash-surg-15",
            exact_stem_hash="exact-surg-15",
            norm_stem_hash="norm-surg-15",
        )
        self.db.merge(q_surg)

        # Question 16: Near-duplicate stem hash clone of q-ss-01
        q_dup = Question(
            id="q-dup-16",
            external_source="docedge",
            external_source_id="dup-16",
            speciality="Pathology",
            subject="Pathology",
            primary_topic_id="TOPIC-BREAST-PATH",
            stem="Super-specialty breast vignette #1: HER2 testing algorithm in invasive ductal carcinoma (CLONE).",
            options=[{"key": "A", "text": "Option A"}, {"key": "B", "text": "Option B"}],
            correct_option="A",
            correct_index=0,
            difficulty=DifficultyLevel.HARD,
            educational_level=EducationalLevel.SUPER_SPECIALTY,
            target_exam_levels=["NEET_SS"],
            status=QuestionStatus.APPROVED,
            classification_source=ClassificationSource.MANUAL,
            classification_status=ClassificationStatus.VERIFIED,
            classification_confidence=1.0,
            content_hash="hash-ss-1-clone",
            exact_stem_hash="exact-ss-1-clone",
            norm_stem_hash="norm-ss-01",  # Same norm stem hash as q-ss-01!
        )
        self.db.merge(q_dup)

        self.db.commit()

    # -------------------------------------------------------------------------
    # Test Cases
    # -------------------------------------------------------------------------

    def test_neet_ss_excludes_mbbs(self):
        """Validates that a NEET-SS blueprint strictly filters out MBBS-level questions."""
        blueprint = {
            "target_exam": "NEET_SS",
            "speciality": "Pathology",
            "question_count": 5,
        }
        res = UniversalQuestionSelector.select_questions(self.db, blueprint)
        selected_ids = [q.id for q in res.selected_questions]

        # Ensure no MBBS questions (q-ug-11..13) are present
        for ug_id in ["q-ug-11", "q-ug-12", "q-ug-13"]:
            self.assertNotIn(ug_id, selected_ids)

    def test_strict_metadata_excludes_unknown(self):
        """Validates that strict_metadata_mode: true excludes questions with UNKNOWN classification."""
        blueprint = {
            "target_exam": "NEET_SS",
            "speciality": "Pathology",
            "strict_metadata_mode": True,
            "question_count": 4,
        }
        res = UniversalQuestionSelector.select_questions(self.db, blueprint)
        selected_ids = [q.id for q in res.selected_questions]
        self.assertNotIn("q-unk-14", selected_ids)

    def test_fallback_allows_unknown_when_configured(self):
        """Validates that strict_metadata_mode: false permits UNKNOWN metadata questions with penalty."""
        blueprint = {
            "topic_id": "TOPIC-BREAST-PATH",
            "speciality": "Pathology",
            "strict_metadata_mode": False,
            "question_count": 7,  # 5 SS + 1 dup + 1 unk = 7 total breast questions
        }
        res = UniversalQuestionSelector.select_questions(self.db, blueprint)
        selected_ids = [q.id for q in res.selected_questions]
        self.assertIn("q-unk-14", selected_ids)
        # Verify unknown metadata penalty reason is recorded
        self.assertIn("UNKNOWN_METADATA_PENALTY", res.selection_reasons_map["q-unk-14"])

    def test_md_questions_allowed_for_neet_ss(self):
        """Validates that MD/PG-level questions qualify for NEET-SS exams."""
        blueprint = {
            "target_exam": "NEET_SS",
            "topic_id": "TOPIC-HEMATO-PATH",
            "question_count": 4,
        }
        res = UniversalQuestionSelector.select_questions(self.db, blueprint)
        self.assertEqual(len(res.selected_questions), 4)
        for q in res.selected_questions:
            self.assertEqual(q.primary_topic_id, "TOPIC-HEMATO-PATH")

    def test_wrong_speciality_excluded(self):
        """Validates that questions outside requested specialty are excluded."""
        blueprint = {
            "speciality": "Pathology",
            "question_count": 5,
        }
        res = UniversalQuestionSelector.select_questions(self.db, blueprint)
        selected_ids = [q.id for q in res.selected_questions]
        self.assertNotIn("q-surg-15", selected_ids)

    def test_wrong_topic_excluded(self):
        """Validates that topic filters strictly isolate targeted topics."""
        blueprint = {
            "topic_id": "TOPIC-HEMATO-PATH",
            "question_count": 3,
        }
        res = UniversalQuestionSelector.select_questions(self.db, blueprint)
        for q in res.selected_questions:
            self.assertEqual(q.primary_topic_id, "TOPIC-HEMATO-PATH")

    def test_difficulty_distribution(self):
        """Validates that requested difficulty distribution is satisfied."""
        blueprint = {
            "topic_id": "TOPIC-BREAST-PATH",
            "difficulty_distribution": {"HARD": 2, "MEDIUM": 2},
            "question_count": 4,
        }
        res = UniversalQuestionSelector.select_questions(self.db, blueprint)
        self.assertEqual(res.difficulty_breakdown.get("hard"), 2)
        self.assertEqual(res.difficulty_breakdown.get("medium"), 2)

    def test_topic_distribution(self):
        """Validates that multi-topic distribution counts are exact."""
        blueprint = {
            "topic_distribution": {
                "TOPIC-BREAST-PATH": 3,
                "TOPIC-HEMATO-PATH": 3,
            },
            "question_count": 6,
        }
        res = UniversalQuestionSelector.select_questions(self.db, blueprint)
        self.assertEqual(res.topic_breakdown.get("TOPIC-BREAST-PATH"), 3)
        self.assertEqual(res.topic_breakdown.get("TOPIC-HEMATO-PATH"), 3)

    def test_repeated_error_priority(self):
        """Validates that questions with repeated consecutive mistakes receive highest remediation priority."""
        user_id = "user-learner-01"
        now = datetime.now(timezone.utc)

        # Insert 3 consecutive wrong attempts for q-ss-03
        for idx in range(3):
            h = UserQuestionHistory(
                user_id=user_id,
                question_id="q-ss-03",
                attempt_id=f"att-hist-{idx}",
                selected_answer="B",
                is_correct=False,
                marks_awarded=-1.0,
                time_spent_seconds=30,
                answered_at=now - timedelta(days=2),
            )
            self.db.add(h)
        self.db.commit()

        blueprint = {
            "topic_id": "TOPIC-BREAST-PATH",
            "assessment_mode": "LEARNING",
            "question_count": 3,
        }
        res = UniversalQuestionSelector.select_questions(self.db, blueprint, user_id=user_id)
        # q-ss-03 should be selected with REPEATED_MISTAKE_PRIORITY
        selected_ids = [q.id for q in res.selected_questions]
        self.assertIn("q-ss-03", selected_ids)
        self.assertIn("REPEATED_MISTAKE_PRIORITY", res.selection_reasons_map["q-ss-03"])

    def test_weak_topic_priority(self):
        """Validates that topics with low Laplace-smoothed accuracy are prioritized in Learning mode."""
        user_id = "user-learner-01"
        # Seed weak topic mastery: Breast = 20% accuracy (weak), Hemato = 85% accuracy (strong)
        m_breast = UserMastery(
            user_id=user_id,
            curriculum_node_id="TOPIC-BREAST-PATH",
            smoothed_accuracy=20.0,
            attempted_count=5,
            correct_count=0,
            incorrect_count=5,
        )
        m_hem = UserMastery(
            user_id=user_id,
            curriculum_node_id="TOPIC-HEMATO-PATH",
            smoothed_accuracy=85.0,
            attempted_count=10,
            correct_count=9,
            incorrect_count=1,
        )
        self.db.merge(m_breast)
        self.db.merge(m_hem)
        self.db.commit()

        blueprint = {
            "assessment_mode": "LEARNING",
            "question_count": 4,
        }
        res = UniversalQuestionSelector.select_questions(self.db, blueprint, user_id=user_id)
        # Breast questions should have WEAK_TOPIC_REMEDIATION reason
        breast_qs = [q for q in res.selected_questions if q.primary_topic_id == "TOPIC-BREAST-PATH"]
        self.assertTrue(len(breast_qs) > 0)
        for bq in breast_qs:
            self.assertIn("WEAK_TOPIC_REMEDIATION", res.selection_reasons_map[bq.id])

    def test_recent_question_penalty(self):
        """Validates that questions seen today receive severe recency penalties."""
        policy = SelectionPolicy()
        penalty_today = QuestionRanker.calculate_recency_penalty(0.1, policy)
        penalty_3days = QuestionRanker.calculate_recency_penalty(2.5, policy)
        penalty_20days = QuestionRanker.calculate_recency_penalty(20.0, policy)

        self.assertEqual(penalty_today, 100.0)
        self.assertEqual(penalty_3days, 60.0)
        self.assertEqual(penalty_20days, 0.0)

    def test_new_question_exposure(self):
        """Validates that unseen questions receive exploration boost."""
        blueprint = {
            "topic_id": "TOPIC-BREAST-PATH",
            "assessment_mode": "GRAND_TEST",
            "question_count": 3,
        }
        res = UniversalQuestionSelector.select_questions(self.db, blueprint, user_id="user-learner-01")
        for q in res.selected_questions:
            self.assertIn("NEW_QUESTION_EXPLORATION", res.selection_reasons_map[q.id])

    def test_exact_duplicate_prevention(self):
        """Validates that no exact duplicate question IDs exist in selection output."""
        blueprint = {
            "question_count": 8,
            "speciality": "Pathology",
        }
        res = UniversalQuestionSelector.select_questions(self.db, blueprint)
        selected_ids = [q.id for q in res.selected_questions]
        self.assertEqual(len(selected_ids), len(set(selected_ids)))

    def test_normalized_duplicate_prevention(self):
        """Validates that questions sharing norm_stem_hash (near-duplicates) are not co-selected."""
        blueprint = {
            "topic_id": "TOPIC-BREAST-PATH",
            "question_count": 5,
        }
        res = UniversalQuestionSelector.select_questions(self.db, blueprint)
        selected_ids = [q.id for q in res.selected_questions]
        # q-ss-01 and q-dup-16 share norm_stem_hash='norm-ss-01'; only one should be chosen
        has_ss_01 = "q-ss-01" in selected_ids
        has_dup_16 = "q-dup-16" in selected_ids
        self.assertFalse(has_ss_01 and has_dup_16, "Both near-duplicate questions were co-selected!")

    def test_insufficient_pool_fail_closed(self):
        """Validates that InsufficientQuestionPoolError is raised when requested count exceeds eligible pool."""
        blueprint = {
            "topic_id": "TOPIC-BREAST-PATH",
            "target_exam": "NEET_SS",
            "question_count": 50,  # Only 5 eligible SS breast questions exist
        }
        with self.assertRaises(InsufficientQuestionPoolError) as ctx:
            UniversalQuestionSelector.select_questions(self.db, blueprint)
        
        err = ctx.exception
        self.assertEqual(err.required_count, 50)
        self.assertTrue(err.deficit > 0)

    def test_selection_is_deterministic(self):
        """Validates that providing a random seed guarantees 100% reproducible question selection."""
        blueprint = {
            "speciality": "Pathology",
            "question_count": 5,
            "seed": 42,
        }
        res1 = UniversalQuestionSelector.select_questions(self.db, blueprint)
        res2 = UniversalQuestionSelector.select_questions(self.db, blueprint)

        ids1 = [q.id for q in res1.selected_questions]
        ids2 = [q.id for q in res2.selected_questions]
        self.assertEqual(ids1, ids2)

    def test_selection_reason_is_recorded(self):
        """Validates that explainable selection reasons and priority scores are attached to snapshots."""
        assessment = AssessmentService.create_assessment(
            db=self.db,
            title="Explainable Assessment",
            question_count=4,
            blueprint={"topic_id": "TOPIC-BREAST-PATH"},
        )
        self.assertEqual(len(assessment.assessment_questions), 4)
        for aq in assessment.assessment_questions:
            snap = aq.snapshot
            self.assertIn("selection_reasons", snap)
            self.assertIn("priority_score", snap)
            self.assertTrue(len(snap["selection_reasons"]) > 0)


if __name__ == "__main__":
    unittest.main()
