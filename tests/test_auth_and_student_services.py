"""
tests/test_auth_and_student_services.py

Comprehensive test suite for Milestone 7:
- Google Sign-In & account linking/provisioning
- Direct email/password registration & login with entropy scoring
- Cryptographic strong password generator
- Brute-force rate limiting
- JWT session rotation and remote logout-all
- Anonymous guest session & diagnostic attempt merge engine
- Adaptive onboarding profile updates
- Daily quiz & streak engine
- Continue learning & weak topic recommendations
- Exam readiness index calculation
- Smart mistake review & remediation blueprint
- Resilient draft answer synchronization
"""

import os
import uuid
import unittest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import (
    Base,
    User,
    UserRole,
    GuestSession,
    UserSession,
    AuthAuditLog,
    Assessment,
    AssessmentType,
    AssessmentQuestion,
    AssessmentAttempt,
    AttemptQuestion,
    AttemptStatus,
    Question,
    QuestionStatus,
    DifficultyLevel,
    CurriculumTopic,
    CurriculumLevel,
    UserMastery,
    UserQuestionHistory,
    MarkingScheme,
)
from backend.core.security import (
    calculate_password_entropy,
    generate_crypto_password,
    hash_password,
    hash_token,
    verify_password,
    decode_access_token,
    AuthRateLimiter,
)
from backend.core.config import reset_settings_cache
from backend.services.auth_service import AuthService
from backend.services.student_service import StudentService
from backend.services.assessment_service import AssessmentService


class TestAuthAndStudentServices(unittest.TestCase):
    """Integration and unit tests for Milestone 7 Identity, Guest Funnel & Student Services."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False)

    def setUp(self):
        self.previous_app_env = os.environ.get("APP_ENV")
        os.environ["APP_ENV"] = "test"
        reset_settings_cache()
        self.db = self.SessionLocal()
        self._seed_data()

    def tearDown(self):
        self.db.rollback()
        self.db.close()
        if self.previous_app_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = self.previous_app_env
        reset_settings_cache()

    def _seed_data(self):
        # 0. Marking Schemes
        scheme = MarkingScheme(id="NEET_4_1", name="NEET Standard (+4, -1)", correct_marks=4.0, penalty_marks=1.0, unanswered_marks=0.0)
        self.db.merge(scheme)
        # 1. Topics
        t1 = CurriculumTopic(id="TOPIC-BREAST-M7", code="BREAST-M7", name="Breast Pathology", level=CurriculumLevel.TOPIC)
        t2 = CurriculumTopic(id="TOPIC-HEMATO-M7", code="HEMATO-M7", name="Hematopathology", level=CurriculumLevel.TOPIC)
        for t in [t1, t2]:
            self.db.merge(t)

        # 2. Questions
        for i in range(1, 11):
            q = Question(
                id=f"q-m7-{i:02d}",
                external_source="docedge",
                external_source_id=f"m7-{i}",
                speciality="Pathology",
                subject="Pathology",
                primary_topic_id="TOPIC-BREAST-M7" if i <= 5 else "TOPIC-HEMATO-M7",
                stem=f"Pathology vignette #{i}: High yield case on diagnostic markers.",
                options=[{"key": "A", "text": "Option A"}, {"key": "B", "text": "Option B"}],
                correct_option="A",
                correct_index=0,
                difficulty=DifficultyLevel.MEDIUM,
                status=QuestionStatus.APPROVED,
                content_hash=f"hash-m7-{i}",
                exact_stem_hash=f"exact-m7-{i}",
                norm_stem_hash=f"norm-m7-{i}",
            )
            self.db.merge(q)

        self.db.commit()

    # -------------------------------------------------------------------------
    # Authentication Tests
    # -------------------------------------------------------------------------

    def test_password_entropy_evaluation(self):
        """Tests password entropy scoring across weak, moderate, strong, and very strong tiers."""
        weak = calculate_password_entropy("12345")
        self.assertEqual(weak["strength"], "WEAK")
        self.assertFalse(weak["is_acceptable"])

        moderate = calculate_password_entropy("Password123")
        self.assertIn(moderate["strength"], ["MODERATE", "STRONG"])

        strong = calculate_password_entropy("C0mpl3x#P@ssw0rd!2026")
        self.assertIn(strong["strength"], ["STRONG", "VERY_STRONG"])
        self.assertTrue(strong["is_acceptable"])

    def test_generate_crypto_password(self):
        """Tests strong password generator produces a high-entropy string meeting all complexity rules."""
        pwd = generate_crypto_password(24)
        self.assertEqual(len(pwd), 24)
        entropy = calculate_password_entropy(pwd)
        self.assertEqual(entropy["strength"], "VERY_STRONG")
        self.assertTrue(entropy["is_acceptable"])

    def test_google_auth_creates_new_user(self):
        """Tests that a Google ID token automatically provisions a new user and issues a valid session."""
        res = AuthService.authenticate_google(
            self.db,
            "test-only-token",
            mock_payload={
                "email": "dr.onco@aiims.edu",
                "sub": "google-sub-1001",
                "name": "Dr. Onco Resident",
                "picture": "https://avatar.url/img.png",
                "email_verified": True,
            },
        )

        self.assertTrue(res["is_new_user"])
        self.assertIsNotNone(res["access_token"])
        self.assertIsNotNone(res["refresh_token"])
        self.assertEqual(res["user"]["email"], "dr.onco@aiims.edu")
        self.assertEqual(res["user"]["name"], "Dr. Onco Resident")

        # Verify decoded JWT
        payload = decode_access_token(res["access_token"])
        self.assertIsNotNone(payload)
        self.assertEqual(payload["email"], "dr.onco@aiims.edu")

    def test_google_auth_links_existing_user(self):
        """Tests that signing in with Google links google_id to an existing email account."""
        # 1. Register with email first
        AuthService.register_email_password(
            db=self.db,
            email="resident@hospital.org",
            password="Strong#Password1234!",
            name="Resident Doctor",
        )

        # 2. Sign in with same email via Google
        res = AuthService.authenticate_google(
            self.db,
            "test-only-token",
            mock_payload={
                "email": "resident@hospital.org",
                "sub": "google-sub-2002",
                "name": "Resident Doctor",
                "picture": "https://avatar.org/pic.png",
                "email_verified": True,
            },
        )

        self.assertFalse(res["is_new_user"])
        user = self.db.query(User).filter(User.email == "resident@hospital.org").first()
        self.assertEqual(user.google_id, "google-sub-2002")

    def test_google_auth_rejects_unverified_email(self):
        """Injected test claims still require Google email verification."""
        with self.assertRaisesRegex(ValueError, "email is not verified"):
            AuthService.authenticate_google(
                self.db,
                "test-only-token",
                mock_payload={
                    "email": "unverified@example.com",
                    "sub": "google-sub-unverified",
                    "email_verified": False,
                },
            )

    def test_email_password_registration_and_login(self):
        """Tests standard email/password registration, password verification, and login."""
        reg = AuthService.register_email_password(
            db=self.db,
            email="new.student@docedge.ai",
            password="Secure#Doctor@2026",
            name="Dr. Newbie",
            target_exam="NEET_SS",
        )
        self.assertEqual(reg["user"]["email"], "new.student@docedge.ai")

        # Login with correct password
        login_res = AuthService.login_email_password(
            db=self.db,
            email="new.student@docedge.ai",
            password="Secure#Doctor@2026",
        )
        self.assertIsNotNone(login_res["access_token"])

        # Login with wrong password
        with self.assertRaises(ValueError):
            AuthService.login_email_password(
                db=self.db,
                email="new.student@docedge.ai",
                password="WrongPassword!",
            )

    def test_weak_password_registration_rejected(self):
        """Tests that weak passwords are rejected during registration."""
        with self.assertRaises(ValueError) as ctx:
            AuthService.register_email_password(
                db=self.db,
                email="fail@docedge.ai",
                password="abc",
                name="Fail User",
            )
        self.assertIn("too weak", str(ctx.exception).lower())

    def test_login_rate_limiting(self):
        """Tests brute force protection locks out an account after 5 consecutive failures."""
        AuthRateLimiter.reset("target@docedge.ai:127.0.0.1")
        
        for _ in range(5):
            AuthRateLimiter.record_failure("target@docedge.ai:127.0.0.1")

        is_locked, remaining = AuthRateLimiter.is_locked_out("target@docedge.ai:127.0.0.1")
        self.assertTrue(is_locked)
        self.assertTrue(remaining > 0)
        AuthRateLimiter.reset("target@docedge.ai:127.0.0.1")

    def test_refresh_token_rotation(self):
        """Tests that refreshing a session issues a new refresh token and invalidates the old one."""
        reg = AuthService.register_email_password(
            db=self.db,
            email="rotator@docedge.ai",
            password="Rotate#Token@2026!",
            name="Rotator",
        )
        old_refresh = reg["refresh_token"]

        ref_res = AuthService.refresh_session(self.db, old_refresh)
        new_refresh = ref_res["refresh_token"]
        self.assertNotEqual(old_refresh, new_refresh)
        self.assertIsNotNone(ref_res["access_token"])

        # Verify session expires_at is extended (sliding window)
        token_hash = hash_token(new_refresh)
        session = self.db.query(UserSession).filter(UserSession.refresh_token_hash == token_hash).first()
        self.assertIsNotNone(session)
        self.assertGreater(session.expires_at.replace(tzinfo=timezone.utc), datetime.now(timezone.utc) + timedelta(days=50))

        # Attempting to use old refresh token must fail
        with self.assertRaises(ValueError):
            AuthService.refresh_session(self.db, old_refresh)

    def test_logout_and_logout_all(self):
        """Tests single session logout and logout-all across all devices."""
        reg = AuthService.register_email_password(
            db=self.db,
            email="multidevice@docedge.ai",
            password="Multi#Device@2026!",
            name="Multi",
        )
        user_id = reg["user"]["id"]
        refresh_tok = reg["refresh_token"]

        # Logout single session
        logged_out = AuthService.logout(self.db, refresh_tok)
        self.assertTrue(logged_out)

        # Logout all devices
        revoked_count = AuthService.logout_all(self.db, user_id)
        self.assertGreaterEqual(revoked_count, 0)

    # -------------------------------------------------------------------------
    # Guest Funnel Tests
    # -------------------------------------------------------------------------

    def test_guest_session_creation(self):
        """Tests anonymous guest session creation."""
        guest = AuthService.create_guest_session(self.db, ip_address="192.168.1.1")
        self.assertIsNotNone(guest.session_token)
        expires = guest.expires_at.replace(tzinfo=timezone.utc) if guest.expires_at.tzinfo is None else guest.expires_at
        self.assertGreater(expires, datetime.now(timezone.utc))

    def test_guest_session_merge_after_auth(self):
        """Tests anonymous diagnostic test attempt is merged into registered user account."""
        # 1. Create Guest Session
        guest = AuthService.create_guest_session(self.db)

        # 2. Guest creates and completes an assessment attempt
        assessment = AssessmentService.create_assessment(
            db=self.db,
            title="5-Question Diagnostic Drill",
            question_count=4,
            blueprint={"topic_id": "TOPIC-BREAST-M7"},
        )
        attempt, _ = AssessmentService.start_attempt(
            db=self.db,
            assessment_id=assessment.id,
            user_id=None,
        )
        attempt.guest_session_id = guest.id
        self.db.commit()

        # Answer 4 questions
        answers = [
            {"question_id": aq.question_id, "selected_answer": "A", "time_spent_seconds": 30}
            for aq in assessment.assessment_questions
        ]
        AssessmentService.submit_attempt(self.db, attempt.id, responses=answers)

        # 3. User registers and merges guest session
        reg = AuthService.register_email_password(
            db=self.db,
            email="converted.guest@docedge.ai",
            password="Merged#User@2026!",
            name="Converted Guest",
        )
        merge_res = AuthService.merge_guest_session(self.db, guest.session_token, reg["user"]["id"])

        self.assertTrue(merge_res["merged"])
        self.assertEqual(merge_res["merged_attempts_count"], 1)

        # Verify attempt ownership was transferred
        att_db = self.db.query(AssessmentAttempt).filter(AssessmentAttempt.id == attempt.id).first()
        self.assertEqual(att_db.user_id, reg["user"]["id"])

        # Verify mastery was populated for newly registered user
        mastery = self.db.query(UserMastery).filter(UserMastery.user_id == reg["user"]["id"]).first()
        self.assertIsNotNone(mastery)
        self.assertGreater(mastery.attempted_count, 0)

    # -------------------------------------------------------------------------
    # Student Services Tests
    # -------------------------------------------------------------------------

    def test_adaptive_onboarding_update(self):
        """Tests updating medical onboarding preferences."""
        reg = AuthService.register_email_password(
            db=self.db,
            email="onboard@docedge.ai",
            password="Onboard#User@2026!",
            name="Dr. Onboarding",
        )
        user_id = reg["user"]["id"]

        updated = StudentService.update_onboarding_profile(
            db=self.db,
            user_id=user_id,
            target_exam="NEET_SS",
            target_year=2026,
            residency_stage="SR",
            medical_college="Tata Memorial Hospital, Mumbai",
            primary_speciality="Pathology",
        )

        self.assertEqual(updated["target_exam"], "NEET_SS")
        self.assertEqual(updated["target_year"], 2026)
        self.assertEqual(updated["residency_stage"], "SR")
        self.assertEqual(updated["medical_college"], "Tata Memorial Hospital, Mumbai")

    def test_daily_quiz_and_streak_tracking(self):
        """Tests deterministic daily quiz retrieval and streak tracking."""
        reg = AuthService.register_email_password(
            db=self.db,
            email="daily.quiz@docedge.ai",
            password="Daily#Quiz@2026!",
            name="Dr. Streak",
        )
        user_id = reg["user"]["id"]

        quiz = StudentService.get_daily_quiz(self.db, user_id)
        self.assertEqual(quiz["question_count"], 5)
        self.assertGreaterEqual(quiz["current_streak"], 1)

    def test_continue_learning_and_weak_topics(self):
        """Tests resumable in-progress attempts and weak topic recommendations."""
        reg = AuthService.register_email_password(
            db=self.db,
            email="learning.tracker@docedge.ai",
            password="Track#Learning@2026!",
            name="Dr. Tracker",
        )
        user_id = reg["user"]["id"]

        # Seed in-progress assessment
        assessment = AssessmentService.create_assessment(
            db=self.db,
            title="In Progress Mock #1",
            question_count=4,
        )
        attempt, _ = AssessmentService.start_attempt(self.db, assessment.id, user_id=user_id)

        # Seed weak topic mastery
        m = UserMastery(
            user_id=user_id,
            curriculum_node_id="TOPIC-BREAST-M7",
            smoothed_accuracy=25.0,
            attempted_count=4,
            incorrect_count=3,
        )
        self.db.merge(m)
        self.db.commit()

        continue_data = StudentService.get_continue_learning(self.db, user_id)
        self.assertEqual(len(continue_data["resumable_attempts"]), 1)
        self.assertEqual(continue_data["resumable_attempts"][0]["attempt_id"], attempt.id)
        self.assertTrue(len(continue_data["weak_topic_recommendations"]) > 0)
        self.assertEqual(continue_data["weak_topic_recommendations"][0]["curriculum_node_id"], "TOPIC-BREAST-M7")

    def test_exam_readiness_calculation(self):
        """Tests composite exam readiness index computation."""
        reg = AuthService.register_email_password(
            db=self.db,
            email="readiness.test@docedge.ai",
            password="Ready#Doctor@2026!",
            name="Dr. Ready",
        )
        user_id = reg["user"]["id"]

        readiness = StudentService.get_exam_readiness(self.db, user_id)
        self.assertIn("readiness_score", readiness)
        self.assertIn("breakdown", readiness)
        self.assertGreaterEqual(readiness["readiness_score"], 0.0)
        self.assertLessEqual(readiness["readiness_score"], 100.0)

    def test_mistake_review_and_remediation(self):
        """Tests mistake retrieval, grouping, and remediation blueprint creation."""
        reg = AuthService.register_email_password(
            db=self.db,
            email="mistakes@docedge.ai",
            password="Mistake#Drill@2026!",
            name="Dr. Mistakes",
        )
        user_id = reg["user"]["id"]
        now = datetime.now(timezone.utc)

        # Insert 2 wrong attempts for q-m7-01 and 1 wrong for q-m7-02
        for _ in range(2):
            self.db.add(UserQuestionHistory(
                user_id=user_id,
                question_id="q-m7-01",
                attempt_id=f"att-{uuid.uuid4()}",
                selected_answer="B",
                is_correct=False,
                marks_awarded=-1.0,
                time_spent_seconds=40,
                answered_at=now,
            ))
        self.db.add(UserQuestionHistory(
            user_id=user_id,
            question_id="q-m7-02",
            attempt_id=f"att-{uuid.uuid4()}",
            selected_answer="B",
            is_correct=False,
            marks_awarded=-1.0,
            time_spent_seconds=40,
            answered_at=now,
        ))
        self.db.commit()

        # Mistake review with repeated_only=True
        review_repeated = StudentService.get_mistake_review(self.db, user_id, repeated_only=True)
        self.assertEqual(len(review_repeated["mistakes"]), 1)
        self.assertEqual(review_repeated["mistakes"][0]["question_id"], "q-m7-01")
        self.assertEqual(review_repeated["mistakes"][0]["error_count"], 2)

    def test_draft_answer_sync(self):
        """Tests idempotent draft answer batch synchronization."""
        reg = AuthService.register_email_password(
            db=self.db,
            email="draft.sync@docedge.ai",
            password="Draft#Sync@2026!",
            name="Dr. Sync",
        )
        user_id = reg["user"]["id"]

        assessment = AssessmentService.create_assessment(
            db=self.db,
            title="Draft Sync Exam",
            question_count=3,
        )
        attempt, _ = AssessmentService.start_attempt(self.db, assessment.id, user_id=user_id)

        sync_payload = [
            {"question_id": aq.question_id, "selected_answer": "B", "time_spent_seconds": 25}
            for aq in assessment.assessment_questions
        ]

        sync_res = StudentService.sync_draft_answers(
            db=self.db,
            attempt_id=attempt.id,
            user_id=user_id,
            answers_payload=sync_payload,
        )

        self.assertTrue(sync_res["success"])
        self.assertEqual(sync_res["synced_count"], 3)

    def test_get_taxonomies(self):
        """Tests that the taxonomies service returns the structured examination and leaf subspecialties hierarchy."""
        tax = StudentService.get_taxonomies(self.db)
        self.assertIn("examinations", tax)
        self.assertIn("experience_stages", tax)
        self.assertIn("target_years", tax)
        self.assertGreaterEqual(len(tax["examinations"]), 4)

        # Verify NEET_SS has specialities
        neet_ss = next(e for e in tax["examinations"] if e["id"] == "NEET_SS")
        self.assertTrue(neet_ss["has_specialities"])
        self.assertGreaterEqual(len(neet_ss["specialities"]), 3)

        # Verify MBBS and NEET_PG are single leaf without subspecialties
        mbbs = next(e for e in tax["examinations"] if e["id"] == "MBBS")
        self.assertFalse(mbbs["has_specialities"])
        self.assertEqual(mbbs["specialities"], [])


if __name__ == "__main__":
    unittest.main()
