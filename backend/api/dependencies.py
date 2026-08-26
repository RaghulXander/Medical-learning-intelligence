"""Reusable FastAPI authorization dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.api.routes.auth import get_current_user, get_db
from backend.core.authorization import Permission, has_permission
from backend.core.security import decode_access_token
from database.models import GuestSession, User


def require_permission(permission: Permission) -> Callable[..., User]:
    """Build a dependency that returns the user only when permission is granted."""

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return dependency


def get_optional_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Resolve a bearer token when present; reject malformed or expired credentials."""
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    payload = decode_access_token(authorization.removeprefix("Bearer ").strip())
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token")
    user = db.query(User).filter(User.id == payload["sub"], User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is unavailable")
    return user


@dataclass(frozen=True)
class RequestPrincipal:
    user: Optional[User] = None
    guest_session: Optional[GuestSession] = None


def require_user_or_guest(
    current_user: Optional[User] = Depends(get_optional_current_user),
    guest_token: Optional[str] = Header(None, alias="X-Guest-Session-Token"),
    db: Session = Depends(get_db),
) -> RequestPrincipal:
    """Require either an authenticated account or a valid anonymous guest session."""
    if current_user:
        return RequestPrincipal(user=current_user)
    if not guest_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required")
    guest = db.query(GuestSession).filter(GuestSession.session_token == guest_token).first()
    now = datetime.now(timezone.utc)
    if not guest or guest.converted_user_id or not guest.expires_at:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid guest session")
    expires_at = guest.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Guest session has expired")
    return RequestPrincipal(guest_session=guest)
