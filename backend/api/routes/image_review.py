"""Admin API for pathology image curation and multimodal pilot readiness."""

from __future__ import annotations

import os
from typing import Optional
from urllib.parse import urlparse

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.dependencies import require_permission
from backend.api.routes.auth import get_db
from backend.core.authorization import Permission
from backend.services.image_review_service import ImageReviewConflictError, ImageReviewService
from database.models import ImageAsset, User


router = APIRouter(prefix="/api/admin/image-review", tags=["image-review"])
reviewer_dependency = require_permission(Permission.MEDIA_MANAGE)


class SaveImageReviewRequest(BaseModel):
    expected_revision: int = Field(..., ge=1)
    utility_class: str = Field(..., min_length=3, max_length=50)
    diagnosis: Optional[str] = Field(None, max_length=255)
    stain: Optional[str] = Field(None, max_length=100)
    magnification: Optional[str] = Field(None, max_length=50)
    caption: Optional[str] = Field(None, max_length=4000)
    occurrence_id: Optional[str] = None
    link_id: Optional[str] = None
    notes: str = Field(..., min_length=3, max_length=4000)
    attested: bool = False


def _translate(exc: Exception):
    if isinstance(exc, ImageReviewConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("")
def get_image_review_summary(
    current_user: User = Depends(reviewer_dependency), db: Session = Depends(get_db)
):
    return ImageReviewService.summary(db)


@router.get("/assets")
def list_image_review_assets(
    curation_status: Optional[str] = Query(None),
    utility_class: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    pilot_shortlisted: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(reviewer_dependency),
    db: Session = Depends(get_db),
):
    return ImageReviewService.list_assets(
        db,
        curation_status=curation_status,
        utility_class=utility_class,
        source=source,
        pilot_shortlisted=pilot_shortlisted,
        page=page,
        limit=limit,
    )


@router.get("/pilot-readiness")
def get_multimodal_pilot_readiness(
    current_user: User = Depends(reviewer_dependency), db: Session = Depends(get_db)
):
    return ImageReviewService.pilot_readiness(db)


@router.get("/assets/{asset_id}")
def get_image_review_asset(
    asset_id: str,
    current_user: User = Depends(reviewer_dependency),
    db: Session = Depends(get_db),
):
    try:
        return ImageReviewService.get_asset(db, asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


from pathlib import Path

@router.get("/assets/{asset_id}/content", include_in_schema=False)
def get_private_image_content(
    asset_id: str,
    current_user: User = Depends(reviewer_dependency),
    db: Session = Depends(get_db),
):
    """Proxy an image from local disk if available, or from configured R2 storage."""
    asset = db.query(ImageAsset).filter_by(id=asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image asset unavailable")

    # 1. First priority: Check local processed image catalog (fastest, zero network egress)
    if asset.filename:
        local_candidates = [
            Path("data/processed/images") / asset.filename,
            Path("data/processed/images/curated_valid") / asset.filename,
        ]
        for candidate in local_candidates:
            if candidate.is_file():
                media_type = "image/png" if asset.filename.lower().endswith(".png") else "image/jpeg"
                return Response(
                    content=candidate.read_bytes(),
                    media_type=media_type,
                    headers={"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"},
                )

    # 2. Second priority: Proxy from storage_uri
    if not asset.storage_uri:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image object unavailable")
    allowed_prefix = os.getenv("R2_PUBLIC_URL", "").rstrip("/")
    parsed = urlparse(asset.storage_uri)
    if (
        not allowed_prefix
        or not asset.storage_uri.startswith(f"{allowed_prefix}/")
        or parsed.scheme != "https"
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Image preview origin is not allowlisted. Configure R2_PUBLIC_URL "
                "on the backend to the exact prefix stored before /pathology/."
            ),
        )
    try:
        upstream = requests.get(asset.storage_uri, timeout=(3, 15))
        upstream.raise_for_status()
    except requests.RequestException:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Image object fetch failed")
    if len(upstream.content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image is too large")
    media_type = upstream.headers.get("content-type", "application/octet-stream").split(";")[0]
    if not media_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Object is not an image")
    return Response(
        content=upstream.content,
        media_type=media_type,
        headers={"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"},
    )


@router.patch("/assets/{asset_id}")
def save_image_review_draft(
    asset_id: str,
    req: SaveImageReviewRequest,
    current_user: User = Depends(reviewer_dependency),
    db: Session = Depends(get_db),
):
    try:
        return ImageReviewService.save(
            db, asset_id, reviewer_id=current_user.id, action="SAVE_DRAFT", **req.model_dump(exclude={"attested"})
        )
    except (ValueError, ImageReviewConflictError) as exc:
        _translate(exc)


@router.post("/assets/{asset_id}/{action}")
def decide_image_review(
    asset_id: str,
    action: str,
    req: SaveImageReviewRequest,
    current_user: User = Depends(reviewer_dependency),
    db: Session = Depends(get_db),
):
    action_map = {
        "approve-study": "APPROVE_INTERNAL_STUDY",
        "approve-question": "APPROVE_INTERNAL_QUESTION_CANDIDATE",
        "reject-non-educational": "REJECTED_NON_EDUCATIONAL",
        "reject-quality": "REJECTED_UNUSABLE_QUALITY",
        "provenance-unresolved": "PROVENANCE_UNRESOLVED",
    }
    if action not in action_map:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown review action")
    if not req.attested:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Human attestation is required")
    try:
        return ImageReviewService.save(
            db,
            asset_id,
            reviewer_id=current_user.id,
            action=action_map[action],
            **req.model_dump(exclude={"attested"}),
        )
    except (ValueError, ImageReviewConflictError) as exc:
        _translate(exc)
