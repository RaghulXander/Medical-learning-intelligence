import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.services.question_review_service import (
    InvalidQuestionStatusTransition,
    transition_question_status,
)
from database.models import Base, Question, QuestionReview, QuestionStatus, User, UserRole


class TestQuestionReviewService(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.reviewer = User(email="reviewer@example.com", name="Reviewer", role=UserRole.REVIEWER)
        self.question = Question(
            external_source_id="review-test-1",
            stem="Test question",
            options=[{"key": "A", "text": "One"}, {"key": "B", "text": "Two"}],
            correct_option="A",
            correct_index=0,
            content_hash="a" * 64,
            exact_stem_hash="b" * 64,
            norm_stem_hash="c" * 64,
            status=QuestionStatus.AI_REVIEW,
        )
        self.db.add_all([self.reviewer, self.question])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_ai_review_can_be_approved_by_reviewer(self):
        review = transition_question_status(
            self.db, self.question, QuestionStatus.APPROVED, self.reviewer.id, "Reviewed and verified"
        )
        self.db.commit()
        self.assertEqual(self.question.status, QuestionStatus.APPROVED)
        self.assertEqual(review.new_status, "APPROVED")

    def test_rejected_question_can_be_approved(self):
        self.question.status = QuestionStatus.REJECTED
        review = transition_question_status(
            self.db, self.question, QuestionStatus.APPROVED, self.reviewer.id, "Re-reviewed and approved"
        )
        self.db.commit()
        self.assertEqual(self.question.status, QuestionStatus.APPROVED)

    def test_human_review_can_approve_and_is_audited(self):
        self.question.status = QuestionStatus.HUMAN_REVIEW
        review = transition_question_status(
            self.db, self.question, QuestionStatus.APPROVED, self.reviewer.id, "Evidence checked"
        )
        self.db.commit()
        stored = self.db.query(QuestionReview).filter_by(id=review.id).one()
        self.assertEqual(self.question.status, QuestionStatus.APPROVED)
        self.assertEqual(stored.previous_status, "HUMAN_REVIEW")
        self.assertEqual(stored.new_status, "APPROVED")
        self.assertEqual(stored.reviewer_id, self.reviewer.id)

    def test_retirement_requires_notes(self):
        self.question.status = QuestionStatus.APPROVED
        with self.assertRaises(InvalidQuestionStatusTransition):
            transition_question_status(self.db, self.question, QuestionStatus.RETIRED, self.reviewer.id)

    def test_rejection_requires_notes(self):
        self.question.status = QuestionStatus.HUMAN_REVIEW
        with self.assertRaises(InvalidQuestionStatusTransition):
            transition_question_status(self.db, self.question, QuestionStatus.REJECTED, self.reviewer.id, notes="")

    def test_approved_question_can_be_rejected_with_notes(self):
        self.question.status = QuestionStatus.APPROVED
        review = transition_question_status(
            self.db, self.question, QuestionStatus.REJECTED, self.reviewer.id, notes="Retracted due to ambiguous distractor"
        )
        self.db.commit()
        self.assertEqual(self.question.status, QuestionStatus.REJECTED)
        self.assertEqual(review.new_status, "REJECTED")
        self.assertEqual(review.review_notes, "Retracted due to ambiguous distractor")


if __name__ == "__main__":
    unittest.main()
