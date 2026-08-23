"""
backend/api/routes/assessments.py

FastAPI router for the Universal Assessment Engine.
Exposes endpoints for listing presets, generating assessments, runner state sync, submission, and review.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.db import get_engine, get_session_factory
from database.models import AssessmentType, NavigationPolicy
from backend.services.assessment_service import (
    AssessmentService,
    AssessmentServiceError,
    AttemptAlreadySubmittedError,
    AttemptNotFoundError,
    QuestionCountUnavailableError,
)

router = APIRouter(prefix="/api/assessments", tags=["Assessments"])


# Dependency to get DB session
def get_db():
    engine = get_engine()
    session_factory = get_session_factory(engine)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


# -----------------------------------------------------------------------------
# Request / Response Schemas
# -----------------------------------------------------------------------------
class SectionConfigSchema(BaseModel):
    name: str = Field(..., example="Part A: General Pathology")
    question_count: int = Field(..., example=50)
    duration_seconds: Optional[int] = Field(None, example=3000)
    navigation_policy: Optional[str] = Field("FREE", example="FREE")


class CreateAssessmentRequest(BaseModel):
    title: str = Field(..., example="Pathology Mock Exam")
    type: str = Field(default="MOCK", example="MOCK")
    question_count: int = Field(default=50, example=50)
    duration_seconds: int = Field(default=3000, example=3000)
    marking_scheme_id: str = Field(default="NEET_4_1", example="NEET_4_1")
    navigation_policy: str = Field(default="FREE", example="FREE")
    blueprint: Optional[Dict[str, Any]] = Field(default_factory=dict)
    sections: Optional[List[SectionConfigSchema]] = None


class StartAttemptRequest(BaseModel):
    user_id: Optional[str] = None


class HeartbeatQuestionResponse(BaseModel):
    question_id: str
    selected_answer: Optional[str] = None
    marked_for_review: Optional[bool] = False
    time_spent_seconds: Optional[int] = 0


class HeartbeatRequest(BaseModel):
    responses: List[HeartbeatQuestionResponse]
    elapsed_seconds: Optional[int] = None


class SubmitAttemptRequest(BaseModel):
    responses: Optional[List[HeartbeatQuestionResponse]] = None
    final_elapsed_seconds: Optional[int] = None


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@router.get("/presets")
def get_assessment_presets() -> List[Dict[str, Any]]:
    """Returns standard 1-click presets (NEET-SS, NEET-PG, INI-CET, Daily Dose, etc.)."""
    return AssessmentService.list_presets()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_assessment(
    req: CreateAssessmentRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Generates an assessment from blueprint parameters and freezes question snapshots."""
    try:
        sec_cfgs = [s.model_dump() for s in req.sections] if req.sections else None
        assessment = AssessmentService.create_assessment(
            db=db,
            title=req.title,
            assessment_type=AssessmentType(req.type),
            question_count=req.question_count,
            duration_seconds=req.duration_seconds,
            marking_scheme_id=req.marking_scheme_id,
            navigation_policy=NavigationPolicy(req.navigation_policy),
            blueprint=req.blueprint,
            sections_config=sec_cfgs,
        )
        return {
            "status": "success",
            "assessment_id": assessment.id,
            "title": assessment.title,
            "type": assessment.type.value,
            "question_count": assessment.question_count,
            "duration_seconds": assessment.duration_seconds,
            "marking_scheme_id": assessment.marking_scheme_id,
        }
    except QuestionCountUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AssessmentServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{assessment_id}/start")
def start_assessment_attempt(
    assessment_id: str,
    req: Optional[StartAttemptRequest] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Starts an assessment attempt and returns sanitized questions (zero answer leaks)."""
    user_id = req.user_id if req else None
    try:
        attempt, sanitized_questions = AssessmentService.start_attempt(
            db=db,
            assessment_id=assessment_id,
            user_id=user_id,
        )
        return {
            "attempt_id": attempt.id,
            "assessment_id": attempt.assessment_id,
            "status": attempt.status.value,
            "started_at": attempt.started_at.isoformat(),
            "duration_seconds": attempt.assessment.duration_seconds,
            "total_questions": attempt.assessment.question_count,
            "navigation_policy": attempt.assessment.navigation_policy.value,
            "questions": sanitized_questions,
        }
    except AssessmentServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/attempts/{attempt_id}")
def get_attempt_state(
    attempt_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Fetches current attempt state for the active runner shell."""
    try:
        return AssessmentService.get_attempt_state(db=db, attempt_id=attempt_id)
    except AttemptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/attempts/{attempt_id}/heartbeat")
def record_heartbeat(
    attempt_id: str,
    req: HeartbeatRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Background heartbeat sync: saves answers, review marks, and elapsed time."""
    try:
        resp_dicts = [r.model_dump() for r in req.responses]
        return AssessmentService.record_heartbeat(
            db=db,
            attempt_id=attempt_id,
            responses=resp_dicts,
            elapsed_seconds=req.elapsed_seconds,
        )
    except AttemptAlreadySubmittedError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AttemptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/attempts/{attempt_id}/submit")
def submit_attempt(
    attempt_id: str,
    req: Optional[SubmitAttemptRequest] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Submits the exam, evaluates answers against ground truth, and computes final scorecard."""
    try:
        resp_dicts = [r.model_dump() for r in req.responses] if req and req.responses else None
        elapsed = req.final_elapsed_seconds if req else None
        return AssessmentService.submit_attempt(
            db=db,
            attempt_id=attempt_id,
            responses=resp_dicts,
            final_elapsed_seconds=elapsed,
        )
    except AttemptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/attempts/{attempt_id}/results")
def get_attempt_results(
    attempt_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Returns diagnostic scorecard with raw marks, negative loss, and topic breakdowns."""
    try:
        return AssessmentService.get_results(db=db, attempt_id=attempt_id)
    except AttemptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/attempts/{attempt_id}/review")
def get_attempt_review(
    attempt_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Returns full question-by-question review with ground truth, explanations, and citations."""
    try:
        return AssessmentService.get_review(db=db, attempt_id=attempt_id)
    except AttemptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
