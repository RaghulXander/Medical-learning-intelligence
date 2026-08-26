"""Reusable FastAPI authorization dependencies."""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, status

from backend.api.routes.auth import get_current_user
from backend.core.authorization import Permission, has_permission
from database.models import User


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

