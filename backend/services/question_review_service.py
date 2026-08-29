"""Guarded and audited question editorial state transitions."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from database.models import Question, QuestionReview, QuestionStatus, ReviewerType


ALLOWED_STATUS_TRANSITIONS = {
    QuestionStatus.IMPORTED: {
        QuestionStatus.AI_REVIEW,
        QuestionStatus.HUMAN_REVIEW,
        QuestionStatus.REJECTED,
        QuestionStatus.RETIRED,
    },
    QuestionStatus.GENERATED: {
        QuestionStatus.AI_REVIEW,
        QuestionStatus.HUMAN_REVIEW,
        QuestionStatus.REJECTED,
        QuestionStatus.RETIRED,
    },
    # AI can recommend, but it cannot publish a question.
    QuestionStatus.AI_REVIEW: {
        QuestionStatus.HUMAN_REVIEW,
        QuestionStatus.REJECTED,
    },
    QuestionStatus.HUMAN_REVIEW: {
        QuestionStatus.AI_REVIEW,
        QuestionStatus.APPROVED,
        QuestionStatus.REJECTED,
        QuestionStatus.RETIRED,
    },
    QuestionStatus.APPROVED: {
        QuestionStatus.HUMAN_REVIEW,
        QuestionStatus.REPORTED,
        QuestionStatus.RETIRED,
    },
    QuestionStatus.REJECTED: {QuestionStatus.HUMAN_REVIEW, QuestionStatus.RETIRED},
    QuestionStatus.REPORTED: {QuestionStatus.HUMAN_REVIEW, QuestionStatus.RETIRED},
    QuestionStatus.RETIRED: {QuestionStatus.HUMAN_REVIEW},
}


class InvalidQuestionStatusTransition(ValueError):
    pass


def transition_question_status(
    db: Session,
    question: Question,
    new_status: QuestionStatus,
    reviewer_id: Optional[str],
    notes: Optional[str] = None,
) -> QuestionReview:
    previous_status = question.status
    allowed = ALLOWED_STATUS_TRANSITIONS.get(previous_status, set())
    if new_status not in allowed:
        raise InvalidQuestionStatusTransition(
            f"Question cannot transition from {previous_status.value} to {new_status.value}"
        )
    if new_status in {QuestionStatus.REJECTED, QuestionStatus.RETIRED} and not (notes or "").strip():
        raise InvalidQuestionStatusTransition(f"Notes are required when moving a question to {new_status.value}")

    review = QuestionReview(
        question_id=question.id,
        reviewer_id=reviewer_id,
        reviewer_type=ReviewerType.HUMAN,
        previous_status=previous_status.value,
        new_status=new_status.value,
        review_notes=(notes or "").strip() or None,
    )
    question.status = new_status
    db.add(review)
    return review
