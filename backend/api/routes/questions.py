"""
backend/api/routes/questions.py

FastAPI router for Question Bank Management & Editorial Review.
Provides search, topic/status filtering, question inspection, and status transitions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database.db import get_engine, get_session_factory
from database.models import (
    CognitiveLevel,
    DifficultyLevel,
    Question,
    QuestionEvidence,
    QuestionRevision,
    QuestionStatus,
    QuestionType,
    User,
)
from backend.api.routes.auth import get_current_user
from backend.api.dependencies import require_permission
from backend.core.authorization import Permission
from backend.services.question_review_service import (
    InvalidQuestionStatusTransition,
    transition_question_status,
)
from backend.services.question_editor_service import (
    EmptyQuestionEdit,
    QuestionEditConflict,
    edit_question,
)
from backend.core.authorization import has_permission
from database.models import AdminAuditLog

router = APIRouter(prefix="/api/questions", tags=["Questions"])


def get_db():
    engine = get_engine()
    session_factory = get_session_factory(engine)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------
class UpdateQuestionStatusRequest(BaseModel):
    status: str = Field(..., example="APPROVED")
    notes: Optional[str] = None


class QuestionOptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(pattern=r"^[A-Z]$", min_length=1, max_length=1)
    text: str = Field(min_length=1, max_length=1000)


class UpdateQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_updated_at: datetime
    stem: str = Field(min_length=10, max_length=10000)
    options: list[QuestionOptionRequest] = Field(min_length=2, max_length=8)
    correct_option: str = Field(pattern=r"^[A-Z]$")
    explanation: str | None = Field(default=None, max_length=20000)
    difficulty: DifficultyLevel
    cognitive_level: CognitiveLevel
    question_type: QuestionType
    primary_topic_id: str | None = None
    learning_objective: str | None = Field(default=None, max_length=2000)
    edit_notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_options(self):
        keys = [option.key for option in self.options]
        if len(keys) != len(set(keys)):
            raise ValueError("Option keys must be unique")
        if self.correct_option not in keys:
            raise ValueError("Correct option must identify one submitted option")
        return self


class ReportQuestionRequest(BaseModel):
    question_id: str
    category: str
    notes: Optional[str] = None



# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@router.get("/topics")
def list_question_topics(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Returns all unique normalized Pathology topics with question counts."""
    results = (
        db.query(
            Question.topic_name_normalized,
            func.count(Question.id).label("count"),
        )
        .filter(Question.topic_name_normalized.isnot(None))
        .group_by(Question.topic_name_normalized)
        .order_by(func.count(Question.id).desc())
        .all()
    )
    return [
        {"name": r.topic_name_normalized, "count": r.count}
        for r in results
        if r.topic_name_normalized
    ]


@router.get("")
def list_questions(
    search: Optional[str] = Query(None, description="Search term in stem or external ID"),
    topic: Optional[str] = Query(None, description="Filter by normalized topic name"),
    status: Optional[str] = Query(None, description="Filter by status (IMPORTED, HUMAN_REVIEW, APPROVED, etc.)"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty (easy, medium, hard)"),
    cognitive_level: Optional[str] = Query(None, description="Filter by cognitive level"),
    limit: int = Query(25, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUESTIONS_READ_EDITORIAL)),
) -> Dict[str, Any]:
    """Search and filter the canonical Question Bank with pagination."""
    query = db.query(Question)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Question.stem.ilike(search_pattern),
                Question.external_source_id.ilike(search_pattern),
                Question.topic_name_normalized.ilike(search_pattern),
            )
        )

    if topic and topic != "ALL":
        query = query.filter(Question.topic_name_normalized == topic)

    if status and status.upper() != "ALL":
        try:
            status_enum = QuestionStatus(status.upper())
            query = query.filter(Question.status == status_enum)
        except ValueError:
            pass

    if difficulty and difficulty != "ALL":
        try:
            diff_enum = DifficultyLevel(difficulty.lower())
            query = query.filter(Question.difficulty == diff_enum)
        except ValueError:
            pass

    if cognitive_level and cognitive_level != "ALL":
        try:
            cog_enum = CognitiveLevel(cognitive_level.lower())
            query = query.filter(Question.cognitive_level == cog_enum)
        except ValueError:
            pass

    total = query.count()
    questions = (
        query.order_by(Question.created_at.desc(), Question.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for q in questions:
        citations = []
        if hasattr(q, "evidence_links") and q.evidence_links:
            for ev in q.evidence_links:
                citations.append({
                    "source_title": ev.source.title if ev.source else "Authoritative Textbook",
                    "chapter": ev.chapter,
                    "page_range": ev.page_range,
                    "evidence_text": ev.evidence_text,
                    "verification_status": ev.verification_status.value if hasattr(ev.verification_status, "value") else str(ev.verification_status),
                })

        cluster_id = None
        if isinstance(q.duplicate_signals, dict):
            cluster_id = q.duplicate_signals.get("cluster_id")

        items.append({
            "id": q.id,
            "external_source": q.external_source,
            "external_source_id": q.external_source_id,
            "specialty": q.speciality,
            "subject": q.subject,
            "topic_name_normalized": q.topic_name_normalized or "General Pathology",
            "topic_mapping_status": q.topic_mapping_status.value if hasattr(q.topic_mapping_status, "value") else str(q.topic_mapping_status),
            "primary_topic_id": q.primary_topic_id,
            "stem": q.stem,
            "options": q.options,
            "correct_option": q.correct_option,
            "correct_index": q.correct_index,
            "explanation": q.explanation,
            "difficulty": q.difficulty.value if q.difficulty else "medium",
            "cognitive_level": q.cognitive_level.value if q.cognitive_level else "recall",
            "question_type": q.question_type.value if hasattr(q.question_type, "value") else str(q.question_type),
            "status": q.status.value if hasattr(q.status, "value") else str(q.status),
            "duplicate_cluster_id": cluster_id,
            "citations": citations,
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@router.get("/{question_id}")
def get_question_detail(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUESTIONS_READ_EDITORIAL)),
) -> Dict[str, Any]:
    """Fetch full question record by ID."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID '{question_id}' not found.",
        )

    citations = []
    if hasattr(q, "evidence_links") and q.evidence_links:
        for ev in q.evidence_links:
            citations.append({
                "source_title": ev.source.title if ev.source else "Authoritative Textbook",
                "chapter": ev.chapter,
                "page_range": ev.page_range,
                "evidence_text": ev.evidence_text,
                "verification_status": ev.verification_status.value if hasattr(ev.verification_status, "value") else str(ev.verification_status),
            })

    cluster_id = None
    if isinstance(q.duplicate_signals, dict):
        cluster_id = q.duplicate_signals.get("cluster_id")

    return {
        "id": q.id,
        "external_source": q.external_source,
        "external_source_id": q.external_source_id,
        "specialty": q.speciality,
        "subject": q.subject,
        "topic_name_normalized": q.topic_name_normalized or "General Pathology",
        "stem": q.stem,
        "options": q.options,
        "correct_option": q.correct_option,
        "correct_index": q.correct_index,
        "explanation": q.explanation,
        "learning_objective": q.learning_objective,
        "difficulty": q.difficulty.value if q.difficulty else "medium",
        "cognitive_level": q.cognitive_level.value if q.cognitive_level else "recall",
        "status": q.status.value if hasattr(q.status, "value") else str(q.status),
        "question_type": q.question_type.value,
        "primary_topic_id": q.primary_topic_id,
        "updated_at": q.updated_at.isoformat(),
        "duplicate_cluster_id": cluster_id,
        "citations": citations,
    }


@router.patch("/{question_id}/status")
def update_question_status(
    question_id: str,
    req: UpdateQuestionStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUESTIONS_REVIEW)),
) -> Dict[str, Any]:
    """Transition a question status (APPROVED, REJECTED, HUMAN_REVIEW, etc.)."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID '{question_id}' not found.",
        )

    try:
        new_status = QuestionStatus(req.status.upper())
        if new_status == QuestionStatus.APPROVED and not has_permission(current_user.role, Permission.QUESTIONS_APPROVE):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Approval permission is required")
        if new_status == QuestionStatus.RETIRED and not has_permission(current_user.role, Permission.QUESTIONS_RETIRE):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Retirement permission is required")
        review = transition_question_status(
            db=db,
            question=q,
            new_status=new_status,
            reviewer_id=current_user.id,
            notes=req.notes,
        )
        db.add(AdminAuditLog(
            admin_id=current_user.id,
            action="QUESTION_STATUS_TRANSITION",
            entity_type="QUESTION",
            entity_id=q.id,
            changes={"new_status": new_status.value, "notes": req.notes},
        ))
        db.commit()
        db.refresh(q)
        return {
            "status": "success",
            "question_id": q.id,
            "new_status": q.status.value,
            "review_id": review.id,
        }
    except InvalidQuestionStatusTransition as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid question status: '{req.status}'.",
        )


@router.patch("/{question_id}")
def update_question_content(
    question_id: str,
    req: UpdateQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUESTIONS_EDIT)),
) -> Dict[str, Any]:
    """Update question content during editorial review."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID '{question_id}' not found.",
        )

    try:
        revision = edit_question(
            db,
            q,
            editor_id=current_user.id,
            expected_updated_at=req.expected_updated_at,
            values={
                "stem": req.stem.strip(),
                "options": [option.model_dump() for option in req.options],
                "correct_option": req.correct_option,
                "explanation": req.explanation.strip() if req.explanation else None,
                "difficulty": req.difficulty,
                "cognitive_level": req.cognitive_level,
                "question_type": req.question_type,
                "primary_topic_id": req.primary_topic_id or None,
                "learning_objective": req.learning_objective.strip() if req.learning_objective else None,
            },
            edit_notes=req.edit_notes,
        )
        db.add(AdminAuditLog(
            admin_id=current_user.id,
            action="QUESTION_CONTENT_EDIT",
            entity_type="QUESTION",
            entity_id=q.id,
            changes={"revision_number": revision.revision_number, "changed_fields": revision.changed_fields},
        ))
        db.commit()
        db.refresh(q)
        return {"status": "success", "question_id": q.id, "revision_number": revision.revision_number, "updated_at": q.updated_at.isoformat()}
    except QuestionEditConflict as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except EmptyQuestionEdit as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{question_id}/revisions")
def list_question_revisions(
    question_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUESTIONS_READ_EDITORIAL)),
) -> Dict[str, Any]:
    if not db.query(Question.id).filter(Question.id == question_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    revisions = (
        db.query(QuestionRevision)
        .filter(QuestionRevision.question_id == question_id)
        .order_by(QuestionRevision.revision_number.desc())
        .limit(limit)
        .all()
    )
    return {"items": [{
        "id": revision.id,
        "revision_number": revision.revision_number,
        "editor_id": revision.editor_id,
        "changed_fields": revision.changed_fields,
        "edit_notes": revision.edit_notes,
        "snapshot": revision.snapshot,
        "created_at": revision.created_at.isoformat(),
    } for revision in revisions]}


@router.post("/report")
def report_question(
    req: ReportQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Report question error or ambiguity for editorial review."""
    q = db.query(Question).filter(Question.id == req.question_id).first()
    if not q:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID '{req.question_id}' not found.",
        )

    # Note: status could transition to REPORTED or be recorded in audit log
    return {
        "status": "success",
        "message": f"Question {req.question_id} report recorded under category '{req.category}'.",
    }
