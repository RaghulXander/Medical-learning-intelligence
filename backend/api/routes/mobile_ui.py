"""Versioned server-driven UI endpoints for precompiled mobile widgets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.api.dependencies import get_optional_current_user, require_permission
from backend.api.routes.auth import get_db
from backend.core.authorization import Permission
from backend.mobile_ui.schemas import MobileScreenDocument, PublishMobileScreenRequest
from database.models import AdminAuditLog, MobileScreenConfiguration, User


router = APIRouter(prefix="/api/mobile-ui", tags=["Mobile UI"])
DEFAULT_HOME_PATH = Path(__file__).resolve().parents[3] / "data" / "mobile-ui" / "home.json"


def read_default_home() -> MobileScreenDocument:
    return MobileScreenDocument.model_validate(json.loads(DEFAULT_HOME_PATH.read_text(encoding="utf-8")))


def _active_config(db: Session, screen_key: str) -> MobileScreenConfiguration | None:
    return (
        db.query(MobileScreenConfiguration)
        .filter(
            MobileScreenConfiguration.screen_key == screen_key,
            MobileScreenConfiguration.is_active.is_(True),
        )
        .order_by(MobileScreenConfiguration.version.desc())
        .first()
    )


def _visible(document: MobileScreenDocument, user: User | None, platform: str) -> dict[str, Any]:
    result = document.model_dump(mode="json")
    visible_widgets = []
    platform_key = platform.upper()
    for widget in result["widgets"]:
        if not widget["enabled"]:
            continue
        if "ALL" not in widget["platforms"] and platform_key not in widget["platforms"]:
            continue
        audience = widget["audience"]
        if audience == "AUTHENTICATED" and user is None:
            continue
        if audience == "FREE" and (user is None or user.is_subscribed):
            continue
        if audience == "SUBSCRIBED" and (user is None or not user.is_subscribed):
            continue
        if widget["rolloutPercentage"] < 100:
            identity = user.id if user else "anonymous"
            bucket = int(hashlib.sha256(f"{identity}:{widget['id']}".encode()).hexdigest()[:8], 16) % 100
            if bucket >= widget["rolloutPercentage"]:
                continue
        visible_widgets.append(widget)
    result["widgets"] = sorted(visible_widgets, key=lambda item: item["order"])
    return result


@router.get("/screens/{screen_key}", response_model=None)
def get_mobile_screen(
    screen_key: str,
    response: Response,
    platform: str = Query("ANDROID", pattern=r"^(IOS|ANDROID)$"),
    app_version: str = Query("1.0.0", pattern=r"^\d+\.\d+\.\d+$"),
    if_none_match: str | None = Header(default=None),
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any] | Response:
    if screen_key != "home":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown mobile screen")
    stored = _active_config(db, screen_key)
    document = MobileScreenDocument.model_validate(stored.document) if stored else read_default_home()
    version = stored.version if stored else 1
    payload = {"version": version, "document": _visible(document, current_user, platform), "appVersion": app_version}
    etag = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    response.headers["ETag"] = f'"{etag}"'
    response.headers["Cache-Control"] = f"private, max-age={document.cacheTtlSeconds}"
    if if_none_match == f'"{etag}"':
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": f'"{etag}"'})
    return payload


@router.get("/admin/screens/{screen_key}")
def get_mobile_screen_for_editing(
    screen_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MOBILE_UI_READ)),
) -> dict[str, Any]:
    if screen_key != "home":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown mobile screen")
    stored = _active_config(db, screen_key)
    document = MobileScreenDocument.model_validate(stored.document) if stored else read_default_home()
    return {"version": stored.version if stored else None, "source": "database" if stored else "bundled", "document": document.model_dump(mode="json")}


@router.put("/admin/screens/{screen_key}")
def publish_mobile_screen(
    screen_key: str,
    payload: PublishMobileScreenRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MOBILE_UI_PUBLISH)),
) -> dict[str, Any]:
    if screen_key != payload.document.screenKey:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Screen key does not match document")
    active = _active_config(db, screen_key)
    current_version = active.version if active else None
    if payload.expectedVersion != current_version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A newer mobile layout was published. Reload before saving.")
    next_version = (db.query(func.max(MobileScreenConfiguration.version)).filter_by(screen_key=screen_key).scalar() or 0) + 1
    if active:
        active.is_active = False
    record = MobileScreenConfiguration(
        screen_key=screen_key,
        version=next_version,
        schema_version=payload.document.schemaVersion,
        document=payload.document.model_dump(mode="json"),
        is_active=True,
        published_by=current_user.id,
    )
    db.add(record)
    db.add(AdminAuditLog(
        admin_id=current_user.id,
        action="MOBILE_UI_PUBLISH",
        entity_type="MOBILE_SCREEN",
        entity_id=screen_key,
        changes={"previous_version": current_version, "version": next_version, "notes": payload.notes},
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()
    return {"success": True, "version": next_version, "document": record.document}


@router.get("/admin/screens/{screen_key}/history")
def mobile_screen_history(
    screen_key: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MOBILE_UI_READ)),
) -> dict[str, Any]:
    rows = db.query(MobileScreenConfiguration).filter_by(screen_key=screen_key).order_by(MobileScreenConfiguration.version.desc()).limit(limit).all()
    return {"items": [{"version": row.version, "is_active": row.is_active, "published_by": row.published_by, "published_at": row.published_at.isoformat()} for row in rows]}
