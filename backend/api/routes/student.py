"""
backend/api/routes/student.py

FastAPI router for Student Personalization, Daily Quizzes, Spaced Mistake Drills, and Readiness (Milestone 7).
"""

from typing import Any, Dict, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.db import get_engine, get_session_factory
from database.models import User
from backend.api.routes.auth import get_current_user, get_db
from backend.services.student_service import StudentService

router = APIRouter(prefix="/api/student", tags=["Student Hub & Services"])


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------
class OnboardingUpdateRequest(BaseModel):
    target_exam: Optional[str] = None
    target_year: Optional[int] = None
    residency_stage: Optional[str] = None
    medical_college: Optional[str] = None
    primary_speciality: Optional[str] = None


class AnswerSyncItem(BaseModel):
    question_id: str
    selected_answer: Optional[str] = None
    time_spent_seconds: Optional[int] = 0
    client_timestamp: Optional[str] = None


class DraftSyncRequest(BaseModel):
    attempt_id: str
    answers: List[AnswerSyncItem]


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@router.get("/taxonomies")
def get_curriculum_taxonomies(db: Session = Depends(get_db)):
    """Returns static/dynamic medical examination and subspecialty taxonomy trees."""
    return StudentService.get_taxonomies(db)


@router.patch("/onboarding")
def update_onboarding(
    req: OnboardingUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates the user's adaptive medical onboarding preferences."""
    try:
        res = StudentService.update_onboarding_profile(
            db=db,
            user_id=current_user.id,
            target_exam=req.target_exam,
            target_year=req.target_year,
            residency_stage=req.residency_stage,
            medical_college=req.medical_college,
            primary_speciality=req.primary_speciality,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/daily-quiz")
def get_daily_quiz(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetches today's high-yield 5-question daily pathology quiz and updates streak."""
    try:
        return StudentService.get_daily_quiz(db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/continue-learning")
def get_continue_learning(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns active in-progress assessment attempts and top 3 weak topic recommendations."""
    return StudentService.get_continue_learning(db, current_user.id)


@router.get("/readiness")
def get_exam_readiness(
    target_exam: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calculates the composite exam readiness index (0–100%)."""
    return StudentService.get_exam_readiness(db, current_user.id, target_exam or current_user.target_exam)


@router.get("/mistakes")
def get_mistake_review(
    topic_id: Optional[str] = None,
    repeated_only: bool = False,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns past mistakes with Robbins textbook citations and 1-click remediation blueprint."""
    return StudentService.get_mistake_review(
        db,
        user_id=current_user.id,
        topic_id=topic_id,
        repeated_only=repeated_only,
        limit=limit,
    )


@router.post("/sync-answers")
def sync_draft_answers(
    req: DraftSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Idempotently synchronizes batch draft answers for network resilience."""
    try:
        res = StudentService.sync_draft_answers(
            db=db,
            attempt_id=req.attempt_id,
            user_id=current_user.id,
            answers_payload=[a.model_dump() for a in req.answers],
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
