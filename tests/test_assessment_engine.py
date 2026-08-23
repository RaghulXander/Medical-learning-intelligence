"""
tests/test_assessment_engine.py

Comprehensive test suite for the Universal Assessment Engine.
Covers blueprint generation, multi-section partitioning, answer secrecy,
heartbeat sync, scoring formulas (NEET +4/-1, INI-CET +1/-0.33), and review.
"""

import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentSection,
    AssessmentType,
    AttemptStatus,
    Base,
    DifficultyLevel,
    MarkingScheme,
    NavigationPolicy,
    Question,
    QuestionStatus,
    QuestionType,
)
from backend.services.assessment_service import (
    AssessmentService,
    AttemptAlreadySubmittedError,
    AttemptNotFoundError,
    QuestionCountUnavailableError,
)


class TestUniversalAssessmentEngine(unittest.TestCase):
    """Unit and integration tests for the Universal Assessment Engine."""

    @classmethod
    def setUpClass(cls):
        """Sets up in-memory SQLite database and seeds test fixtures."""
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
        """Seeds standard marking schemes and sample questions."""
        # 1. Marking schemes
        schemes = [
            MarkingScheme(id="NEET_4_1", name="NEET Standard (+4, -1)", correct_marks=4.0, penalty_marks=1.0, unanswered_marks=0.0),
            MarkingScheme(id="INICET_1_033", name="INI-CET Standard (+1, -0.3333)", correct_marks=1.0, penalty_marks=0.3333, unanswered_marks=0.0),
            MarkingScheme(id="ZERO_PENALTY", name="Learning Mode (+1, 0)", correct_marks=1.0, penalty_marks=0.0, unanswered_marks=0.0),
        ]
        for s in schemes:
            self.db.merge(s)

        # 2. Seed 15 test questions
        for i in range(1, 16):
            q_id = f"test-q-{i:02d}"
            existing = self.db.get(Question, q_id)
            if not existing:
                options = [
                    {"key": "A", "text": f"Option A for question #{i}"},
                    {"key": "B", "text": f"Option B for question #{i}"},
                    {"key": "C", "text": f"Option C for question #{i}"},
                    {"key": "D", "text": f"Option D for question #{i}"},
                ]
                q = Question(
                    id=q_id,
                    external_source="test",
                    external_source_id=f"test-{i}",
                    primary_topic_id="TOPIC-BREAST-PATH" if i <= 10 else "TOPIC-LYMPHOMAS",
                    stem=f"Clinical vignette for question #{i}: What is the diagnostic finding?",
                    question_type=QuestionType.SINGLE_BEST_ANSWER,
                    options=options,
                    correct_option="A" if i % 2 == 1 else "B",
                    correct_index=0 if i % 2 == 1 else 1,
                    explanation=f"Explanation for question #{i} referencing Robbins.",
                    difficulty=DifficultyLevel.HARD if i <= 5 else DifficultyLevel.MEDIUM,
                    status=QuestionStatus.APPROVED,
                    content_hash=f"hash-{i}",
                    exact_stem_hash=f"exact-{i}",
                    norm_stem_hash=f"norm-{i}",
                )
                self.db.add(q)

        self.db.commit()


    def test_list_presets(self):
        """Verifies standard presets include NEET-SS, NEET-PG, INI-CET, and Daily Dose."""
        presets = AssessmentService.list_presets()
        preset_ids = [p["id"] for p in presets]
        self.assertIn("neet-ss-mock", preset_ids)
        self.assertIn("neet-pg-mock", preset_ids)
        self.assertIn("inicet-mock", preset_ids)
        self.assertIn("daily-dose", preset_ids)

    def test_create_assessment_and_freeze_snapshots(self):
        """Verifies assessment creation freezes immutable question snapshots."""
        assessment = AssessmentService.create_assessment(
            db=self.db,
            title="10Q Pathology Quick Test",
            assessment_type=AssessmentType.TOPIC,
            question_count=10,
            duration_seconds=600,
            marking_scheme_id="NEET_4_1",
            blueprint={"topic_id": "TOPIC-BREAST-PATH"},
        )

        self.assertIsNotNone(assessment.id)
        self.assertEqual(assessment.question_count, 10)
        self.assertEqual(len(assessment.assessment_questions), 10)

        # Check snapshot contents
        aq = assessment.assessment_questions[0]
        self.assertIn("stem", aq.snapshot)
        self.assertIn("options", aq.snapshot)
        self.assertEqual(len(aq.snapshot["options"]), 4)
        self.assertIn("correct_option", aq.snapshot)
        self.assertIn("explanation", aq.snapshot)

    def test_multi_section_partitioning(self):
        """Verifies multi-section tests correctly partition question allocations."""
        sections_config = [
            {"name": "Part A: General", "question_count": 4},
            {"name": "Part B: Specialty", "question_count": 6},
        ]
        assessment = AssessmentService.create_assessment(
            db=self.db,
            title="NEET-SS Two-Section Mock",
            assessment_type=AssessmentType.MOCK,
            question_count=10,
            duration_seconds=900,
            marking_scheme_id="NEET_4_1",
            sections_config=sections_config,
        )

        self.assertEqual(len(assessment.sections), 2)
        sec_a = assessment.sections[0]
        sec_b = assessment.sections[1]

        # Verify question section mapping
        sec_a_qs = [aq for aq in assessment.assessment_questions if aq.section_id == sec_a.id]
        sec_b_qs = [aq for aq in assessment.assessment_questions if aq.section_id == sec_b.id]
        self.assertEqual(len(sec_a_qs), 4)
        self.assertEqual(len(sec_b_qs), 6)

    def test_start_attempt_answer_secrecy(self):
        """Verifies client runner payload strictly strips correct_option and explanation."""
        assessment = AssessmentService.create_assessment(
            db=self.db,
            title="Security Verification Exam",
            question_count=5,
            duration_seconds=300,
        )

        attempt, sanitized_questions = AssessmentService.start_attempt(
            db=self.db,
            assessment_id=assessment.id,
        )

        self.assertEqual(attempt.status, AttemptStatus.IN_PROGRESS)
        self.assertEqual(len(sanitized_questions), 5)

        for sq in sanitized_questions:
            # Ensure stem, options, and status are present
            self.assertIn("stem", sq)
            self.assertIn("options", sq)
            self.assertIn("status", sq)
            self.assertEqual(sq["status"], "UNANSWERED")

            # CRITICAL: Ensure zero answer leaks
            self.assertNotIn("correct_option", sq)
            self.assertNotIn("correct_answer", sq)
            self.assertNotIn("explanation", sq)

    def test_heartbeat_sync_and_prometric_status(self):
        """Verifies heartbeat updates question responses and calculates Prometric status."""
        assessment = AssessmentService.create_assessment(
            db=self.db,
            title="Heartbeat Exam",
            question_count=4,
            duration_seconds=300,
        )

        attempt, _ = AssessmentService.start_attempt(db=self.db, assessment_id=assessment.id)
        q_ids = [aq.question_id for aq in assessment.assessment_questions]

        # Sync responses: Q1 answered, Q2 answered & marked, Q3 marked only, Q4 untouched
        responses = [
            {"question_id": q_ids[0], "selected_answer": "A", "marked_for_review": False, "time_spent_seconds": 25},
            {"question_id": q_ids[1], "selected_answer": "B", "marked_for_review": True, "time_spent_seconds": 40},
            {"question_id": q_ids[2], "selected_answer": None, "marked_for_review": True, "time_spent_seconds": 15},
        ]

        sync_res = AssessmentService.record_heartbeat(
            db=self.db,
            attempt_id=attempt.id,
            responses=responses,
            elapsed_seconds=80,
        )
        self.assertEqual(sync_res["answered_count"], 2)
        self.assertEqual(sync_res["unanswered_count"], 2)

        # Check runner state
        state = AssessmentService.get_attempt_state(db=self.db, attempt_id=attempt.id)
        status_map = {q["question_id"]: q["status"] for q in state["questions"]}

        self.assertEqual(status_map[q_ids[0]], "ANSWERED")
        self.assertEqual(status_map[q_ids[1]], "ANSWERED_AND_MARKED")
        self.assertEqual(status_map[q_ids[2]], "MARKED_FOR_REVIEW")
        self.assertEqual(status_map[q_ids[3]], "UNANSWERED")

    def test_neet_scoring_calculation(self):
        """
        Tests NEET Standard (+4 / -1) scoring calculation.
        Scenario: 10 Questions
        - 6 Correct (+24 marks)
        - 2 Incorrect (-2 marks)
        - 2 Unanswered (0 marks)
        Expected Score: 22 / 40 (55.0%), Accuracy: 75.0%
        """
        assessment = AssessmentService.create_assessment(
            db=self.db,
            title="NEET Scoring Exam",
            question_count=10,
            duration_seconds=600,
            marking_scheme_id="NEET_4_1",
        )

        attempt, _ = AssessmentService.start_attempt(db=self.db, assessment_id=assessment.id)
        
        # Build responses
        responses = []
        for idx, aq in enumerate(assessment.assessment_questions):
            corr = aq.snapshot["correct_option"]
            wrong = "C" if corr != "C" else "D"

            if idx < 6:
                # 6 Correct
                responses.append({"question_id": aq.question_id, "selected_answer": corr, "time_spent_seconds": 30})
            elif idx < 8:
                # 2 Incorrect
                responses.append({"question_id": aq.question_id, "selected_answer": wrong, "time_spent_seconds": 45})
            else:
                # 2 Unanswered
                responses.append({"question_id": aq.question_id, "selected_answer": None, "time_spent_seconds": 10})

        # Submit attempt
        results = AssessmentService.submit_attempt(
            db=self.db,
            attempt_id=attempt.id,
            responses=responses,
            final_elapsed_seconds=300,
        )

        self.assertEqual(results["status"], AttemptStatus.SUBMITTED.value)
        self.assertEqual(results["correct_count"], 6)
        self.assertEqual(results["incorrect_count"], 2)
        self.assertEqual(results["unanswered_count"], 2)
        self.assertEqual(results["score"], 22.0)
        self.assertEqual(results["max_score"], 40.0)
        self.assertEqual(results["percentage"], 55.0)
        self.assertEqual(results["accuracy"], 75.0)
        self.assertEqual(results["negative_marks_lost"], 2.0)

    def test_inicet_scoring_calculation(self):
        """
        Tests INI-CET (+1 / -0.3333) scoring calculation.
        Scenario: 6 Questions
        - 3 Correct (+3.0 marks)
        - 3 Incorrect (-1.0 mark)
        Expected Score: 2.0 / 6.0 (33.3%)
        """
        assessment = AssessmentService.create_assessment(
            db=self.db,
            title="INI-CET Scoring Exam",
            question_count=6,
            duration_seconds=360,
            marking_scheme_id="INICET_1_033",
        )

        attempt, _ = AssessmentService.start_attempt(db=self.db, assessment_id=assessment.id)

        responses = []
        for idx, aq in enumerate(assessment.assessment_questions):
            corr = aq.snapshot["correct_option"]
            wrong = "C" if corr != "C" else "D"
            ans = corr if idx < 3 else wrong
            responses.append({"question_id": aq.question_id, "selected_answer": ans})

        results = AssessmentService.submit_attempt(
            db=self.db,
            attempt_id=attempt.id,
            responses=responses,
        )

        self.assertEqual(results["correct_count"], 3)
        self.assertEqual(results["incorrect_count"], 3)
        self.assertEqual(results["score"], 2.0)
        self.assertEqual(results["max_score"], 6.0)

    def test_deep_review_canvas(self):
        """Verifies review endpoint exposes full question context, explanations, and ground truth."""
        assessment = AssessmentService.create_assessment(
            db=self.db,
            title="Review Test",
            question_count=3,
        )
        attempt, _ = AssessmentService.start_attempt(db=self.db, assessment_id=assessment.id)
        AssessmentService.submit_attempt(db=self.db, attempt_id=attempt.id)

        review = AssessmentService.get_review(db=self.db, attempt_id=attempt.id)
        self.assertEqual(len(review["review_questions"]), 3)

        first_q = review["review_questions"][0]
        self.assertIn("stem", first_q)
        self.assertIn("options", first_q)
        self.assertIn("correct_answer", first_q)
        self.assertIn("explanation", first_q)
        self.assertIn("marks_awarded", first_q)
        self.assertIn("primary_topic_id", first_q)


if __name__ == "__main__":
    unittest.main()
