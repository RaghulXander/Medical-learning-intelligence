"""Validated, optimistic and revisioned question content editing."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.ingestion.universal_ingestor import compute_hashes
from database.models import Question, QuestionRevision


class QuestionEditConflict(ValueError):
    """Raised when an editor submits against an older question revision."""


class EmptyQuestionEdit(ValueError):
    """Raised when a submitted document is identical to the stored question."""


EDITABLE_FIELDS = (
    "stem",
    "options",
    "correct_option",
    "explanation",
    "difficulty",
    "cognitive_level",
    "question_type",
    "primary_topic_id",
    "learning_objective",
)


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def question_snapshot(question: Question) -> dict[str, Any]:
    return {
        "stem": question.stem,
        "options": question.options,
        "correct_option": question.correct_option,
        "correct_index": question.correct_index,
        "explanation": question.explanation,
        "difficulty": question.difficulty.value if question.difficulty else None,
        "cognitive_level": question.cognitive_level.value if question.cognitive_level else None,
        "question_type": question.question_type.value,
        "primary_topic_id": question.primary_topic_id,
        "learning_objective": question.learning_objective,
        "status": question.status.value,
        "updated_at": question.updated_at.isoformat() if question.updated_at else None,
    }


def edit_question(
    db: Session,
    question: Question,
    *,
    editor_id: str,
    expected_updated_at: datetime,
    values: dict[str, Any],
    edit_notes: str | None = None,
) -> QuestionRevision:
    """Store the previous snapshot and apply one validated full-document edit."""

    stored_updated_at = _utc(question.updated_at)
    submitted_updated_at = _utc(expected_updated_at)
    if abs((stored_updated_at - submitted_updated_at).total_seconds()) > 0.001:
        raise QuestionEditConflict("This question changed after it was loaded. Reload before saving.")

    before = question_snapshot(question)
    changed_fields = []
    for field in EDITABLE_FIELDS:
        next_value = values[field]
        current_value = getattr(question, field)
        comparable_current = current_value.value if hasattr(current_value, "value") else current_value
        comparable_next = next_value.value if hasattr(next_value, "value") else next_value
        if comparable_current != comparable_next:
            changed_fields.append(field)

    if not changed_fields:
        raise EmptyQuestionEdit("No question fields changed")

    revision_number = (
        db.query(func.max(QuestionRevision.revision_number))
        .filter(QuestionRevision.question_id == question.id)
        .scalar()
        or 0
    ) + 1
    revision = QuestionRevision(
        question_id=question.id,
        editor_id=editor_id,
        revision_number=revision_number,
        snapshot=before,
        changed_fields=changed_fields,
        edit_notes=(edit_notes or "").strip() or None,
    )
    db.add(revision)

    for field in EDITABLE_FIELDS:
        setattr(question, field, values[field])

    question.correct_index = next(
        index for index, option in enumerate(question.options) if option["key"] == question.correct_option
    )
    hashes = compute_hashes(question.stem, question.options)
    question.content_hash = hashes["content_hash"]
    question.exact_stem_hash = hashes["exact_stem_hash"]
    question.norm_stem_hash = hashes["norm_stem_hash"]
    question.updated_at = datetime.now(timezone.utc)
    return revision
