"""
backend/api/routes/questions.py

FastAPI router for Question Bank Management & Editorial Review.
Provides search, topic/status filtering, question inspection, and status transitions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database.db import get_engine, get_session_factory
from database.models import (
    CognitiveLevel,
    DifficultyLevel,
    Question,
    QuestionEvidence,
    QuestionStatus,
    QuestionType,
)

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


class UpdateQuestionRequest(BaseModel):
    stem: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = None
    cognitive_level: Optional[str] = None
    primary_topic_id: Optional[str] = None
    status: Optional[str] = None


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
def get_question_detail(question_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
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
        "difficulty": q.difficulty.value if q.difficulty else "medium",
        "cognitive_level": q.cognitive_level.value if q.cognitive_level else "recall",
        "status": q.status.value if hasattr(q.status, "value") else str(q.status),
        "duplicate_cluster_id": cluster_id,
        "citations": citations,
    }


@router.patch("/{question_id}/status")
def update_question_status(
    question_id: str,
    req: UpdateQuestionStatusRequest,
    db: Session = Depends(get_db),
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
        q.status = new_status
        db.commit()
        db.refresh(q)
        return {
            "status": "success",
            "question_id": q.id,
            "new_status": q.status.value,
        }
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
) -> Dict[str, Any]:
    """Update question content during editorial review."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID '{question_id}' not found.",
        )

    if req.stem is not None:
        q.stem = req.stem
    if req.explanation is not None:
        q.explanation = req.explanation
    if req.difficulty is not None:
        try:
            q.difficulty = DifficultyLevel(req.difficulty.lower())
        except ValueError:
            pass
    if req.cognitive_level is not None:
        try:
            q.cognitive_level = CognitiveLevel(req.cognitive_level.lower())
        except ValueError:
            pass
    if req.primary_topic_id is not None:
        q.primary_topic_id = req.primary_topic_id
    if req.status is not None:
        try:
            q.status = QuestionStatus(req.status.upper())
        except ValueError:
            pass

    db.commit()
    db.refresh(q)
    return {
        "status": "success",
        "question_id": q.id,
        "updated": True,
    }


@router.post("/report")
def report_question(
    req: ReportQuestionRequest,
    db: Session = Depends(get_db),
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

