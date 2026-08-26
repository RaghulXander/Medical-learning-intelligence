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
from database.models import AssessmentAttempt, AssessmentType, NavigationPolicy
from backend.api.dependencies import RequestPrincipal, require_user_or_guest
from backend.core.authorization import Permission, has_permission
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


def _require_attempt_owner(
    db: Session,
    attempt_id: str,
    principal: RequestPrincipal,
) -> AssessmentAttempt:
    """Return an attempt only to its owner or an explicitly privileged administrator."""
    attempt = db.get(AssessmentAttempt, attempt_id)
    owns_attempt = bool(
        attempt
        and (
            (principal.user and attempt.user_id == principal.user.id)
            or (
                principal.user
                and has_permission(principal.user.role, Permission.ATTEMPTS_READ_ANY)
            )
            or (
                principal.guest_session
                and attempt.guest_session_id == principal.guest_session.id
            )
        )
    )
    if not owns_attempt:
        # Do not reveal whether another user's attempt exists.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    return attempt


def _require_requested_user(user_id: str, principal: RequestPrincipal) -> None:
    if principal.user and (
        principal.user.id == user_id
        or has_permission(principal.user.role, Permission.ATTEMPTS_READ_ANY)
    ):
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User learning data not found")


def _require_exam_access(principal: RequestPrincipal) -> None:
    """Enforce the temporary manual entitlement before billing is available."""
    if not principal.user:
        # Preserve the existing limited guest diagnostic flow.
        return
    if principal.user.is_subscribed or has_permission(
        principal.user.role, Permission.ATTEMPTS_READ_ANY
    ):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Exam access requires activation. Please contact support.",
    )


# -----------------------------------------------------------------------------
# Request / Response Schemas
# -----------------------------------------------------------------------------
class SectionConfigSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, example="Part A: General Pathology")
    question_count: int = Field(..., ge=1, le=150, example=50)
    duration_seconds: Optional[int] = Field(None, ge=60, le=86400, example=3000)
    navigation_policy: Optional[str] = Field("FREE", example="FREE")


class CreateAssessmentRequest(BaseModel):
    preset_id: Optional[str] = Field(None, description="Canonical ID returned by /presets")
    title: str = Field(..., min_length=1, max_length=255, example="Pathology Mock Exam")
    type: str = Field(default="MOCK", example="MOCK")
    question_count: int = Field(default=50, ge=1, le=150, example=50)
    duration_seconds: int = Field(default=3000, ge=60, le=86400, example=3000)
    marking_scheme_id: str = Field(default="NEET_4_1", example="NEET_4_1")
    navigation_policy: str = Field(default="FREE", example="FREE")
    blueprint: Optional[Dict[str, Any]] = Field(default_factory=dict)
    sections: Optional[List[SectionConfigSchema]] = None


class HeartbeatQuestionResponse(BaseModel):
    question_id: str
    selected_answer: Optional[str] = None
    marked_for_review: Optional[bool] = False
    time_spent_seconds: Optional[int] = Field(0, ge=0, le=86400)


class HeartbeatRequest(BaseModel):
    responses: List[HeartbeatQuestionResponse] = Field(..., max_length=150)
    elapsed_seconds: Optional[int] = Field(None, ge=0, le=86400)


class SubmitAttemptRequest(BaseModel):
    responses: Optional[List[HeartbeatQuestionResponse]] = Field(None, max_length=150)
    final_elapsed_seconds: Optional[int] = Field(None, ge=0, le=86400)


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
    principal: RequestPrincipal = Depends(require_user_or_guest),
) -> Dict[str, Any]:
    """Generates an assessment from blueprint parameters and freezes question snapshots."""
    _require_exam_access(principal)
    try:
        preset = AssessmentService.get_preset(req.preset_id) if req.preset_id else None
        blueprint = dict(req.blueprint or {})
        if preset and preset.get("depth_level"):
            blueprint.setdefault("educational_levels", [preset["depth_level"]])
        sec_cfgs = (
            preset.get("sections")
            if preset and preset.get("sections")
            else [s.model_dump() for s in req.sections] if req.sections else None
        )
        assessment = AssessmentService.create_assessment(
            db=db,
            title=preset["title"] if preset else req.title,
            assessment_type=AssessmentType(preset["type"] if preset else req.type),
            question_count=preset["question_count"] if preset else req.question_count,
            duration_seconds=preset["duration_seconds"] if preset else req.duration_seconds,
            marking_scheme_id=preset["marking_scheme_id"] if preset else req.marking_scheme_id,
            navigation_policy=NavigationPolicy(preset["navigation_policy"] if preset else req.navigation_policy),
            blueprint=blueprint,
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
    db: Session = Depends(get_db),
    principal: RequestPrincipal = Depends(require_user_or_guest),
) -> Dict[str, Any]:
    """Starts an assessment attempt and returns sanitized questions (zero answer leaks)."""
    _require_exam_access(principal)
    try:
        attempt, sanitized_questions = AssessmentService.start_attempt(
            db=db,
            assessment_id=assessment_id,
            user_id=principal.user.id if principal.user else None,
            guest_session_id=principal.guest_session.id if principal.guest_session else None,
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
    principal: RequestPrincipal = Depends(require_user_or_guest),
) -> Dict[str, Any]:
    """Fetches current attempt state for the active runner shell."""
    try:
        _require_attempt_owner(db, attempt_id, principal)
        return AssessmentService.get_attempt_state(db=db, attempt_id=attempt_id)
    except AttemptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/attempts/{attempt_id}/heartbeat")
def record_heartbeat(
    attempt_id: str,
    req: HeartbeatRequest,
    db: Session = Depends(get_db),
    principal: RequestPrincipal = Depends(require_user_or_guest),
) -> Dict[str, Any]:
    """Background heartbeat sync: saves answers, review marks, and elapsed time."""
    try:
        _require_attempt_owner(db, attempt_id, principal)
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
    principal: RequestPrincipal = Depends(require_user_or_guest),
) -> Dict[str, Any]:
    """Submits the exam, evaluates answers against ground truth, and computes final scorecard."""
    try:
        _require_attempt_owner(db, attempt_id, principal)
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
    principal: RequestPrincipal = Depends(require_user_or_guest),
) -> Dict[str, Any]:
    """Returns diagnostic scorecard with raw marks, negative loss, and topic breakdowns."""
    try:
        _require_attempt_owner(db, attempt_id, principal)
        return AssessmentService.get_results(db=db, attempt_id=attempt_id)
    except AttemptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/attempts/{attempt_id}/review")
def get_attempt_review(
    attempt_id: str,
    db: Session = Depends(get_db),
    principal: RequestPrincipal = Depends(require_user_or_guest),
) -> Dict[str, Any]:
    """Returns full question-by-question review with ground truth, explanations, and citations."""
    try:
        attempt = _require_attempt_owner(db, attempt_id, principal)
        if attempt.status.value == "IN_PROGRESS":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Question review is available only after submission",
            )
        return AssessmentService.get_review(db=db, attempt_id=attempt_id)
    except AttemptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/preview")
def preview_assessment(
    req: CreateAssessmentRequest,
    db: Session = Depends(get_db),
    principal: RequestPrincipal = Depends(require_user_or_guest),
) -> Dict[str, Any]:
    """Simulates question selection and returns topic/difficulty distributions and explainable selection reasons."""
    try:
        return AssessmentService.preview_assessment(
            db=db,
            blueprint=req.blueprint or {},
            user_id=principal.user.id if principal.user else None,
            question_count=req.question_count,
        )
    except QuestionCountUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AssessmentServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/users/{user_id}/mastery")
def get_user_mastery(
    user_id: str,
    db: Session = Depends(get_db),
    principal: RequestPrincipal = Depends(require_user_or_guest),
) -> List[Dict[str, Any]]:
    """Returns the user's Laplace-smoothed mastery across all attempted curriculum nodes."""
    _require_requested_user(user_id, principal)
    from database.models import UserMastery
    records = db.query(UserMastery).filter(UserMastery.user_id == user_id).all()
    return [
        {
            "curriculum_node_id": r.curriculum_node_id,
            "smoothed_accuracy": r.smoothed_accuracy,
            "attempted_count": r.attempted_count,
            "correct_count": r.correct_count,
            "incorrect_count": r.incorrect_count,
            "exposure_count": r.exposure_count,
            "average_time_seconds": r.average_time_seconds,
            "last_seen_at": r.last_seen_at.isoformat() if r.last_seen_at else None,
        }
        for r in records
    ]


@router.get("/users/{user_id}/history")
def get_user_history(
    user_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    principal: RequestPrincipal = Depends(require_user_or_guest),
) -> List[Dict[str, Any]]:
    """Returns recent question interaction history for a user."""
    _require_requested_user(user_id, principal)
    from database.models import UserQuestionHistory
    records = (
        db.query(UserQuestionHistory)
        .filter(UserQuestionHistory.user_id == user_id)
        .order_by(UserQuestionHistory.answered_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "question_id": r.question_id,
            "attempt_id": r.attempt_id,
            "selected_answer": r.selected_answer,
            "is_correct": r.is_correct,
            "marks_awarded": r.marks_awarded,
            "time_spent_seconds": r.time_spent_seconds,
            "answered_at": r.answered_at.isoformat(),
        }
        for r in records
    ]
