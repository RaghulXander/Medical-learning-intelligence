"""Role-gated API for human verification of retrieval benchmark labels."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.dependencies import require_permission
from backend.api.routes.auth import get_db
from backend.core.authorization import Permission
from backend.services.retrieval_review_service import (
    ReviewConflictError,
    RetrievalReviewService,
)
from database.models import User


router = APIRouter(prefix="/api/admin/retrieval-review", tags=["retrieval-review"])
reviewer_dependency = require_permission(Permission.QUESTIONS_REVIEW)


class UpdateCaseRequest(BaseModel):
    expected_revision: int = Field(..., ge=1)
    domain: str = Field(..., min_length=2, max_length=100)
    query: str = Field(..., min_length=5, max_length=1000)
    expected_chunk_ids: List[str] = Field(default_factory=list, max_length=20)
    out_of_corpus: bool = False
    notes: str = Field(default="", max_length=4000)


class DecideCaseRequest(BaseModel):
    expected_revision: int = Field(..., ge=1)
    notes: str = Field(..., min_length=3, max_length=4000)


def _translate_error(exc: Exception):
    if isinstance(exc, ReviewConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/evidence/search")
def search_review_evidence(
    q: str = Query(..., min_length=2, max_length=200),
    source: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=25),
    current_user: User = Depends(reviewer_dependency),
    db: Session = Depends(get_db),
):
    try:
        return {
            "items": RetrievalReviewService.search_evidence(
                db, query=q, source_short_name=source, limit=limit
            )
        }
    except ValueError as exc:
        _translate_error(exc)


@router.get("/{benchmark_slug}")
def get_review_summary(
    benchmark_slug: str,
    current_user: User = Depends(reviewer_dependency),
    db: Session = Depends(get_db),
):
    try:
        return RetrievalReviewService.summary(db, benchmark_slug)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/{benchmark_slug}/cases")
def list_review_cases(
    benchmark_slug: str,
    verification_status: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(reviewer_dependency),
    db: Session = Depends(get_db),
):
    try:
        return RetrievalReviewService.list_cases(
            db,
            benchmark_slug,
            verification_status=verification_status,
            domain=domain,
            page=page,
            limit=limit,
        )
    except ValueError as exc:
        _translate_error(exc)


@router.get("/{benchmark_slug}/cases/{case_id}")
def get_review_case(
    benchmark_slug: str,
    case_id: str,
    current_user: User = Depends(reviewer_dependency),
    db: Session = Depends(get_db),
):
    try:
        return RetrievalReviewService.get_case(db, benchmark_slug, case_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/{benchmark_slug}/cases/{case_id}")
def update_review_case(
    benchmark_slug: str,
    case_id: str,
    req: UpdateCaseRequest,
    current_user: User = Depends(reviewer_dependency),
    db: Session = Depends(get_db),
):
    try:
        return RetrievalReviewService.update_case(
            db,
            benchmark_slug,
            case_id,
            reviewer_id=current_user.id,
            expected_revision=req.expected_revision,
            domain=req.domain,
            query=req.query,
            expected_chunk_ids=req.expected_chunk_ids,
            out_of_corpus=req.out_of_corpus,
            notes=req.notes,
        )
    except (ValueError, ReviewConflictError) as exc:
        _translate_error(exc)


@router.post("/{benchmark_slug}/cases/{case_id}/approve")
def approve_review_case(
    benchmark_slug: str,
    case_id: str,
    req: DecideCaseRequest,
    current_user: User = Depends(reviewer_dependency),
    db: Session = Depends(get_db),
):
    try:
        return RetrievalReviewService.decide_case(
            db,
            benchmark_slug,
            case_id,
            reviewer_id=current_user.id,
            expected_revision=req.expected_revision,
            approve=True,
            notes=req.notes,
        )
    except (ValueError, ReviewConflictError) as exc:
        _translate_error(exc)


@router.post("/{benchmark_slug}/cases/{case_id}/reject")
def reject_review_case(
    benchmark_slug: str,
    case_id: str,
    req: DecideCaseRequest,
    current_user: User = Depends(reviewer_dependency),
    db: Session = Depends(get_db),
):
    try:
        return RetrievalReviewService.decide_case(
            db,
            benchmark_slug,
            case_id,
            reviewer_id=current_user.id,
            expected_revision=req.expected_revision,
            approve=False,
            notes=req.notes,
        )
    except (ValueError, ReviewConflictError) as exc:
        _translate_error(exc)
