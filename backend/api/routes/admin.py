"""
backend/api/routes/admin.py

Admin Management & Role-Based Access Control (RBAC) API Routes.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.models import User, UserRole
from backend.services.admin_service import AdminService, is_super_admin_email
from backend.api.routes.auth import get_db, get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that enforces Admin or Super Admin role permissions."""
    is_super = is_super_admin_email(current_user.email)
    if is_super or current_user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Unauthorized: Admin or Super Administrator privileges required",
    )


class UpdateRoleRequest(BaseModel):
    role: str = Field(..., description="Target role: SUPER_ADMIN, ADMIN, REVIEWER, EDUCATOR, USER")


@router.get("/users")
def list_users(
    search: Optional[str] = Query(None, description="Search by name or email"),
    role: Optional[str] = Query("ALL", description="Filter by role"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Lists all users with search, role filters, and attempts statistics."""
    return AdminService.list_users(
        db=db,
        search=search,
        role=role,
        page=page,
        limit=limit,
    )


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    req: UpdateRoleRequest,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Updates a user's role with RBAC enforcement and Super Admin protections."""
    client_ip = request.client.host if request.client else None
    try:
        res = AdminService.update_user_role(
            db=db,
            target_user_id=user_id,
            new_role_str=req.role,
            actor_user_id=current_admin.id,
            ip_address=client_ip,
        )
        return res
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.get("/stats")
def get_admin_stats(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Returns high-level statistics for the admin dashboard."""
    return AdminService.get_admin_stats(db=db)
