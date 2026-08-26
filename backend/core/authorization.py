"""Central role-to-permission policy for backend authorization decisions."""

from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet

from database.models import UserRole


class Permission(str, Enum):
    QUESTIONS_READ_EDITORIAL = "questions.read_editorial"
    QUESTIONS_EDIT = "questions.edit"
    QUESTIONS_REVIEW = "questions.review"
    QUESTIONS_APPROVE = "questions.approve"
    QUESTIONS_RETIRE = "questions.retire"
    REPORTS_SUBMIT = "reports.submit"
    REPORTS_RESOLVE = "reports.resolve"
    USERS_READ = "users.read"
    USERS_MANAGE_ROLES = "users.manage_roles"
    ENTITLEMENTS_MANAGE = "entitlements.manage"
    ATTEMPTS_READ_ANY = "attempts.read_any"


ROLE_PERMISSIONS: Dict[UserRole, FrozenSet[Permission]] = {
    UserRole.SUPER_ADMIN: frozenset(Permission),
    UserRole.ADMIN: frozenset(
        {
            Permission.QUESTIONS_READ_EDITORIAL,
            Permission.QUESTIONS_EDIT,
            Permission.QUESTIONS_REVIEW,
            Permission.QUESTIONS_APPROVE,
            Permission.QUESTIONS_RETIRE,
            Permission.REPORTS_SUBMIT,
            Permission.REPORTS_RESOLVE,
            Permission.USERS_READ,
            Permission.USERS_MANAGE_ROLES,
            Permission.ENTITLEMENTS_MANAGE,
            Permission.ATTEMPTS_READ_ANY,
        }
    ),
    UserRole.REVIEWER: frozenset(
        {
            Permission.QUESTIONS_READ_EDITORIAL,
            Permission.QUESTIONS_EDIT,
            Permission.QUESTIONS_REVIEW,
            Permission.QUESTIONS_APPROVE,
            Permission.QUESTIONS_RETIRE,
            Permission.REPORTS_SUBMIT,
            Permission.REPORTS_RESOLVE,
        }
    ),
    UserRole.EDUCATOR: frozenset(
        {
            Permission.QUESTIONS_READ_EDITORIAL,
            Permission.QUESTIONS_EDIT,
            Permission.REPORTS_SUBMIT,
        }
    ),
    UserRole.USER: frozenset({Permission.REPORTS_SUBMIT}),
}


def has_permission(role: UserRole, permission: Permission) -> bool:
    """Return whether a role is granted a named permission."""
    return permission in ROLE_PERMISSIONS.get(role, frozenset())

