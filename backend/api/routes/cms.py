"""Authenticated landing-page CMS validation and Git publishing endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.api.dependencies import require_permission
from backend.api.routes.auth import get_db
from backend.cms.github_publisher import (
    CmsNotConfigured,
    CmsPublishConflict,
    CmsPublishError,
    GitHubContentPublisher,
    read_local_document,
)
from backend.cms.schemas import LandingPageDocument, PublishLandingPageRequest
from backend.core.authorization import Permission
from database.models import AdminAuditLog, User


router = APIRouter(prefix="/api/cms", tags=["CMS"])


@router.get("/landing-page")
def get_landing_page(
    current_user: User = Depends(require_permission(Permission.CONTENT_READ)),
) -> dict[str, Any]:
    publisher = GitHubContentPublisher()
    if publisher.settings.configured:
        try:
            document, sha = publisher.get_document()
            validated = LandingPageDocument.model_validate(document)
            return {"document": validated.model_dump(mode="json"), "sha": sha, "source": "github"}
        except (CmsPublishError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    validated = LandingPageDocument.model_validate(read_local_document())
    return {"document": validated.model_dump(mode="json"), "sha": None, "source": "local"}


@router.post("/landing-page/validate")
def validate_landing_page(
    document: LandingPageDocument,
    current_user: User = Depends(require_permission(Permission.CONTENT_EDIT)),
) -> dict[str, Any]:
    return {"valid": True, "section_count": len(document.sections)}


@router.put("/landing-page/publish")
def publish_landing_page(
    payload: PublishLandingPageRequest,
    request: Request,
    current_user: User = Depends(require_permission(Permission.CONTENT_PUBLISH)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    publisher = GitHubContentPublisher()
    document = payload.document.model_copy(
        update={"documentVersion": datetime.now(timezone.utc)}
    )
    changed_sections = [section.id for section in document.sections]
    message = payload.message or f"cms: publish landing page ({len(changed_sections)} sections)"
    try:
        result = publisher.publish(document.model_dump(mode="json"), payload.baseSha, message)
    except CmsNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except CmsPublishConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except CmsPublishError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    db.add(AdminAuditLog(
        admin_id=current_user.id,
        action="CMS_PUBLISH",
        entity_type="LANDING_PAGE",
        entity_id=result.get("commit_sha") or "unknown",
        changes={
            "base_sha": payload.baseSha,
            "commit_sha": result.get("commit_sha"),
            "content_sha": result.get("content_sha"),
            "section_ids": changed_sections,
            "schema_version": document.schemaVersion,
        },
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()
    return {"success": True, "document": document.model_dump(mode="json"), **result}


@router.get("/landing-page/history")
def landing_page_history(
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(require_permission(Permission.CONTENT_READ)),
) -> dict[str, Any]:
    try:
        return {"items": GitHubContentPublisher().history(limit)}
    except CmsNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except CmsPublishError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
