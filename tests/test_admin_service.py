"""
tests/test_admin_service.py

Comprehensive tests for Admin & RBAC Governance (Milestone 7):
- Super Admin email safeguards (raghuldpi95@gmail.com, raghuljayan@gmail.com)
- User role assignment & permission enforcement
- Attempting to demote or mutate protected Super Admins raises PermissionError
- Admin statistics aggregation
"""

import unittest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import (
    Base,
    User,
    UserRole,
    AdminAuditLog,
    AssessmentAttempt,
    Question,
    QuestionStatus,
)
from backend.services.admin_service import AdminService, is_super_admin_email, SUPER_ADMIN_EMAILS
from backend.services.auth_service import AuthService


class TestAdminService(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Seed initial test users
        self.super_admin = User(
            id=str(uuid.uuid4()),
            email="raghuldpi95@gmail.com",
            name="Dr. Raghul Xander",
            role=UserRole.SUPER_ADMIN,
            is_email_verified=True,
        )
        self.regular_admin = User(
            id=str(uuid.uuid4()),
            email="admin@hospital.org",
            name="Dr. Standard Admin",
            role=UserRole.ADMIN,
            is_email_verified=True,
        )
        self.student_user = User(
            id=str(uuid.uuid4()),
            email="student@residency.org",
            name="Resident User",
            role=UserRole.USER,
            is_email_verified=True,
        )
        self.db.add_all([self.super_admin, self.regular_admin, self.student_user])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_super_admin_email_registry(self):
        """Validates that configured super admin emails are identified."""
        self.assertTrue(is_super_admin_email("raghuldpi95@gmail.com"))
        self.assertTrue(is_super_admin_email("RAGHULJAYAN@GMAIL.COM"))
        self.assertTrue(is_super_admin_email("  raghuldpi95@gmail.com  "))
        self.assertFalse(is_super_admin_email("other@gmail.com"))
        self.assertFalse(is_super_admin_email(None))

    def test_list_users_paginated(self):
        """Tests listing users with search, role filters, and counts."""
        res = AdminService.list_users(self.db, search="raghul")
        self.assertEqual(res["total"], 1)
        self.assertEqual(res["items"][0]["email"], "raghuldpi95@gmail.com")
        self.assertTrue(res["items"][0]["is_protected"])

        # Filter by role
        res_admin = AdminService.list_users(self.db, role="ADMIN")
        self.assertEqual(res_admin["total"], 1)
        self.assertEqual(res_admin["items"][0]["email"], "admin@hospital.org")

    def test_protected_super_admin_cannot_be_demoted(self):
        """Ensures permanent super admin accounts cannot be demoted to USER or any other role."""
        with self.assertRaises(PermissionError):
            AdminService.update_user_role(
                db=self.db,
                target_user_id=self.super_admin.id,
                new_role_str="USER",
                actor_user_id=self.regular_admin.id,
            )

        with self.assertRaises(PermissionError):
            AdminService.update_user_role(
                db=self.db,
                target_user_id=self.super_admin.id,
                new_role_str="USER",
                actor_user_id=self.super_admin.id,
            )

    def test_super_admin_can_promote_to_admin(self):
        """Super Admin can promote regular user to ADMIN."""
        res = AdminService.update_user_role(
            db=self.db,
            target_user_id=self.student_user.id,
            new_role_str="ADMIN",
            actor_user_id=self.super_admin.id,
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["new_role"], "ADMIN")

        # Verify DB and audit log
        updated = self.db.query(User).filter(User.id == self.student_user.id).first()
        self.assertEqual(updated.role, UserRole.ADMIN)

        audit = self.db.query(AdminAuditLog).filter(AdminAuditLog.entity_id == self.student_user.id).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.action, "UPDATE_USER_ROLE")
        self.assertEqual(audit.changes["new_role"], "ADMIN")

    def test_regular_admin_cannot_promote_to_admin_or_superadmin(self):
        """Regular admin cannot promote someone to ADMIN or SUPER_ADMIN."""
        with self.assertRaises(PermissionError):
            AdminService.update_user_role(
                db=self.db,
                target_user_id=self.student_user.id,
                new_role_str="ADMIN",
                actor_user_id=self.regular_admin.id,
            )

        with self.assertRaises(PermissionError):
            AdminService.update_user_role(
                db=self.db,
                target_user_id=self.student_user.id,
                new_role_str="SUPER_ADMIN",
                actor_user_id=self.regular_admin.id,
            )

    def test_regular_admin_can_promote_to_reviewer(self):
        """Regular admin can promote user to REVIEWER or EDUCATOR."""
        res = AdminService.update_user_role(
            db=self.db,
            target_user_id=self.student_user.id,
            new_role_str="REVIEWER",
            actor_user_id=self.regular_admin.id,
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["new_role"], "REVIEWER")

    def test_auth_service_auto_elevates_super_admin_email(self):
        """Tests that registering or authenticating with super admin email auto-assigns SUPER_ADMIN."""
        auth_res = AuthService.register_email_password(
            db=self.db,
            email="raghuljayan@gmail.com",
            password="StrongPassword!@#1234567890",
            name="Dr. Raghul Jayan",
        )
        self.assertEqual(auth_res["user"]["role"], "SUPER_ADMIN")

        user_db = self.db.query(User).filter(User.email == "raghuljayan@gmail.com").first()
        self.assertEqual(user_db.role, UserRole.SUPER_ADMIN)
        self.assertTrue(user_db.is_email_verified)

    def test_admin_stats_aggregation(self):
        """Tests admin stats aggregation."""
        stats = AdminService.get_admin_stats(self.db)
        self.assertGreaterEqual(stats["total_users"], 3)
        self.assertIn("SUPER_ADMIN", stats["users_by_role"])
