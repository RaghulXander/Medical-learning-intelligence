"""
backend/services/admin_service.py

Admin Management & Role-Based Access Control (RBAC) Service.
- User management and role assignments (SUPER_ADMIN, ADMIN, REVIEWER, EDUCATOR, USER)
- Strict permanent protection for Super Admin emails: raghuldpi95@gmail.com, raghuljayan@gmail.com
- Admin audit logging and dashboard statistics
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database.models import (
    User,
    UserRole,
    AdminAuditLog,
    AssessmentAttempt,
    Question,
    QuestionStatus,
)

SUPER_ADMIN_EMAILS = {
    "raghuldpi95@gmail.com",
    "raghuljayan@gmail.com",
}


def is_super_admin_email(email: Optional[str]) -> bool:
    """Checks if email belongs to the permanent Super Admin registry."""
    if not email:
        return False
    return email.lower().strip() in SUPER_ADMIN_EMAILS


class AdminService:
    """
    Service providing administration capabilities, user role management,
    system statistics, and RBAC governance.
    """

    @staticmethod
    def list_users(
        db: Session,
        search: Optional[str] = None,
        role: Optional[str] = None,
        page: int = 1,
        limit: int = 25,
    ) -> Dict[str, Any]:
        """
        Returns a paginated list of users with attempts count and protection status.
        """
        query = db.query(User)

        if search:
            s = f"%{search.strip()}%"
            query = query.filter(or_(User.email.ilike(s), User.name.ilike(s)))

        if role and role.upper() != "ALL":
            try:
                role_enum = UserRole(role.upper())
                query = query.filter(User.role == role_enum)
            except ValueError:
                pass

        total = query.count()
        offset = max(0, (page - 1) * limit)
        users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()

        # Count attempts per user
        user_ids = [u.id for u in users]
        attempts_counts: Dict[str, int] = {}
        if user_ids:
            counts = (
                db.query(AssessmentAttempt.user_id, func.count(AssessmentAttempt.id))
                .filter(AssessmentAttempt.user_id.in_(user_ids))
                .group_by(AssessmentAttempt.user_id)
                .all()
            )
            attempts_counts = {uid: cnt for uid, cnt in counts}

        items = []
        for u in users:
            is_super = is_super_admin_email(u.email)
            role_val = UserRole.SUPER_ADMIN.value if is_super else (u.role.value if hasattr(u.role, "value") else str(u.role))
            items.append({
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "role": role_val,
                "is_email_verified": u.is_email_verified,
                "is_active": u.is_active,
                "is_protected": is_super,
                "target_exam": u.target_exam,
                "residency_stage": u.residency_stage,
                "medical_college": u.medical_college,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "total_attempts": attempts_counts.get(u.id, 0),
            })

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "items": items,
        }

    @staticmethod
    def update_user_role(
        db: Session,
        target_user_id: str,
        new_role_str: str,
        actor_user_id: str,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Updates a user's role with RBAC enforcement and Super Admin protection.
        - Permanent Super Admin emails cannot be modified or demoted.
        - Only SUPER_ADMIN can promote to SUPER_ADMIN or ADMIN.
        - ADMIN can assign REVIEWER, EDUCATOR, USER.
        """
        actor = db.query(User).filter(User.id == actor_user_id).first()
        if not actor:
            raise ValueError("Actor user not found")

        actor_is_super = is_super_admin_email(actor.email) or actor.role == UserRole.SUPER_ADMIN
        actor_is_admin = actor.role == UserRole.ADMIN

        if not (actor_is_super or actor_is_admin):
            raise PermissionError("Unauthorized: Admin privileges required")

        target = db.query(User).filter(User.id == target_user_id).first()
        if not target:
            raise ValueError("Target user not found")

        # 1. Protection for permanent super admins
        if is_super_admin_email(target.email) and new_role_str.upper() != UserRole.SUPER_ADMIN.value:
            raise PermissionError(f"Cannot demote or modify protected Super Admin account ({target.email})")

        try:
            new_role = UserRole(new_role_str.upper())
        except ValueError:
            raise ValueError(f"Invalid role '{new_role_str}'. Valid roles: {[r.value for r in UserRole]}")

        # 2. RBAC Promotion Rules
        if new_role in (UserRole.SUPER_ADMIN, UserRole.ADMIN) and not actor_is_super:
            raise PermissionError("Only Super Administrators can assign Admin or Super Admin roles")

        old_role = target.role.value if hasattr(target.role, "value") else str(target.role)
        target.role = new_role
        target.updated_at = datetime.now(timezone.utc)
        db.flush()

        # 3. Record Admin Audit Log
        audit = AdminAuditLog(
            id=str(uuid.uuid4()),
            admin_id=actor.id,
            action="UPDATE_USER_ROLE",
            entity_type="User",
            entity_id=target.id,
            changes={"old_role": old_role, "new_role": new_role.value},
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()

        return {
            "success": True,
            "user_id": target.id,
            "email": target.email,
            "new_role": target.role.value,
        }

    @staticmethod
    def get_admin_stats(db: Session) -> Dict[str, Any]:
        """
        Returns high-level statistics for the admin dashboard.
        """
        total_users = db.query(func.count(User.id)).scalar() or 0
        total_questions = db.query(func.count(Question.id)).scalar() or 0
        total_attempts = db.query(func.count(AssessmentAttempt.id)).scalar() or 0

        status_counts = (
            db.query(Question.status, func.count(Question.id))
            .group_by(Question.status)
            .all()
        )
        questions_by_status = {
            (st.value if hasattr(st, "value") else str(st)): cnt for st, cnt in status_counts
        }

        roles_counts = (
            db.query(User.role, func.count(User.id))
            .group_by(User.role)
            .all()
        )
        users_by_role = {
            (r.value if hasattr(r, "value") else str(r)): cnt for r, cnt in roles_counts
        }

        return {
            "total_users": total_users,
            "total_questions": total_questions,
            "total_attempts": total_attempts,
            "questions_by_status": questions_by_status,
            "users_by_role": users_by_role,
        }
