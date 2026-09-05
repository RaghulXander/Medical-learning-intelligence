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


def _val(enum_or_val: Any) -> Any:
    if hasattr(enum_or_val, "value"):
        return enum_or_val.value
    return enum_or_val


def question_snapshot(question: Question) -> dict[str, Any]:
    return {
        "stem": question.stem,
        "options": question.options,
        "correct_option": question.correct_option,
        "correct_index": question.correct_index,
        "explanation": question.explanation,
        "difficulty": _val(question.difficulty) if question.difficulty is not None else None,
        "cognitive_level": _val(question.cognitive_level) if question.cognitive_level is not None else None,
        "question_type": _val(question.question_type) if question.question_type is not None else "single_best_answer",
        "primary_topic_id": str(question.primary_topic_id) if question.primary_topic_id is not None else None,
        "learning_objective": question.learning_objective,
        "status": _val(question.status) if question.status is not None else "IMPORTED",
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
        comparable_current = _val(current_value)
        comparable_next = _val(next_value)
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

    # Find correct_index safely across list of dicts, strings, or dict maps
    correct_idx = None
    if isinstance(question.options, list):
        for idx, option in enumerate(question.options):
            if isinstance(option, dict):
                opt_key = option.get("key") or option.get("id") or ""
            else:
                opt_key = str(option)
            if opt_key and str(opt_key).strip().upper() == str(question.correct_option).strip().upper():
                correct_idx = idx
                break
    elif isinstance(question.options, dict):
        for idx, (k, _) in enumerate(question.options.items()):
            if str(k).strip().upper() == str(question.correct_option).strip().upper():
                correct_idx = idx
                break

    question.correct_index = correct_idx if correct_idx is not None else 0
    hashes = compute_hashes(question.stem, question.options)
    question.content_hash = hashes["content_hash"]
    question.exact_stem_hash = hashes["exact_stem_hash"]
    question.norm_stem_hash = hashes["norm_stem_hash"]
    question.updated_at = datetime.now(timezone.utc)
    return revision
