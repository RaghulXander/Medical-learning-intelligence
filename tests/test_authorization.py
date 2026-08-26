"""Unit tests for the central role permission matrix."""

import unittest

from backend.core.authorization import Permission, has_permission
from database.models import UserRole


class AuthorizationPolicyTests(unittest.TestCase):
    def test_student_cannot_edit_or_review_questions(self):
        self.assertFalse(has_permission(UserRole.USER, Permission.QUESTIONS_EDIT))
        self.assertFalse(has_permission(UserRole.USER, Permission.QUESTIONS_REVIEW))
        self.assertTrue(has_permission(UserRole.USER, Permission.REPORTS_SUBMIT))

    def test_educator_can_edit_but_not_approve(self):
        self.assertTrue(has_permission(UserRole.EDUCATOR, Permission.QUESTIONS_EDIT))
        self.assertFalse(has_permission(UserRole.EDUCATOR, Permission.QUESTIONS_APPROVE))

    def test_reviewer_can_approve_but_not_manage_entitlements(self):
        self.assertTrue(has_permission(UserRole.REVIEWER, Permission.QUESTIONS_APPROVE))
        self.assertFalse(has_permission(UserRole.REVIEWER, Permission.ENTITLEMENTS_MANAGE))

    def test_super_admin_has_every_permission(self):
        for permission in Permission:
            self.assertTrue(has_permission(UserRole.SUPER_ADMIN, permission))


if __name__ == "__main__":
    unittest.main()
