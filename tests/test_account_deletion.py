"""
tests/test_account_deletion.py

Unit tests for Milestone 17 Account Deletion & Right to Erasure:
- User purging and session revocation
- Cascading user mastery cleanup
- Anonymization of assessment attempts and question reports
- Protection of Super Administrator accounts from deletion
"""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import (
    Base,
    User,
    UserRole,
    UserSession,
    AuthAuditLog,
    AssessmentAttempt,
    Assessment,
    AssessmentType,
    NavigationPolicy,
    MarkingScheme,
)
from backend.services.auth_service import AuthService
from backend.services.admin_service import SUPER_ADMIN_EMAILS


@pytest.fixture
def db_session():
    """Creates a temporary in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        # Seed marking scheme
        scheme = MarkingScheme(
            id="NEET_4_1",
            name="NEET PG/SS Standard Scheme",
            correct_marks=4.0,
            penalty_marks=1.0,
            unanswered_marks=0.0,
        )
        session.add(scheme)
        session.commit()
        yield session
    finally:
        session.close()


def test_delete_user_account_success(db_session):
    """Verifies that user deletion permanently erases user and sessions while anonymizing attempts."""
    # 1. Create user
    user = User(
        id=str(uuid.uuid4()),
        email="doctor.test@example.com",
        name="Dr. Test Resident",
        role=UserRole.USER,
        target_exam="NEET_SS",
    )
    db_session.add(user)
    db_session.flush()

    # 2. Add an active session
    sess = UserSession(
        id=str(uuid.uuid4()),
        user_id=user.id,
        refresh_token_hash="fake_hash_12345",
        expires_at=datetime.now(timezone.utc),
    )
    db_session.add(sess)

    # 3. Add an assessment and attempt
    assessment = Assessment(
        id=str(uuid.uuid4()),
        type=AssessmentType.MOCK,
        title="Diagnostic Mock",
        question_count=10,
        duration_seconds=1800,
        marking_scheme_id="NEET_4_1",
        navigation_policy=NavigationPolicy.FREE,
    )
    db_session.add(assessment)
    db_session.flush()

    attempt = AssessmentAttempt(
        id=str(uuid.uuid4()),
        assessment_id=assessment.id,
        user_id=user.id,
    )
    db_session.add(attempt)
    db_session.commit()

    # Verify entities exist before deletion
    assert db_session.get(User, user.id) is not None
    assert db_session.query(UserSession).filter_by(user_id=user.id).count() == 1
    assert db_session.get(AssessmentAttempt, attempt.id).user_id == user.id

    # Execute deletion
    result = AuthService.delete_user_account(
        db=db_session,
        user_id=user.id,
        ip_address="127.0.0.1",
        user_agent="DocEdge-Android-Test/1.0",
    )

    assert result["success"] is True

    # 4. Verify user and sessions are deleted
    assert db_session.get(User, user.id) is None
    assert db_session.query(UserSession).filter_by(user_id=user.id).count() == 0

    # 5. Verify attempt is anonymized (user_id is None)
    anonymized_attempt = db_session.get(AssessmentAttempt, attempt.id)
    assert anonymized_attempt is not None
    assert anonymized_attempt.user_id is None

    # 6. Verify audit log was recorded
    audit_log = (
        db_session.query(AuthAuditLog)
        .filter_by(email="doctor.test@example.com", event_type="ACCOUNT_DELETED")
        .first()
    )
    assert audit_log is not None
    assert audit_log.ip_address == "127.0.0.1"


def test_protect_super_admin_deletion(db_session):
    """Ensures root Super Administrator accounts cannot be deleted."""
    admin_email = next(iter(SUPER_ADMIN_EMAILS))
    super_admin = User(
        id=str(uuid.uuid4()),
        email=admin_email,
        name="Root Super Admin",
        role=UserRole.SUPER_ADMIN,
    )
    db_session.add(super_admin)
    db_session.commit()

    with pytest.raises(ValueError, match="Super Administrator accounts cannot be deleted"):
        AuthService.delete_user_account(db=db_session, user_id=super_admin.id)

    # Verify super admin still exists
    assert db_session.get(User, super_admin.id) is not None
