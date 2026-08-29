"""Adopt the current M10 schema as the Alembic baseline.

Revision ID: 20260826_0001
Revises: None
"""

from typing import Optional

from alembic import op
from sqlalchemy import inspect, text

from database.models import Base


revision = "20260826_0001"
down_revision: Optional[str] = None
branch_labels = None
depends_on = None


# Keep the adopted M10 baseline stable as new ORM models are introduced. Without
# this allow-list, a fresh migration run would create future tables here and then
# fail when their own revisions attempt to create them.
M10_BASELINE_TABLES = (
    "users",
    "courses",
    "curriculum_topics",
    "course_curriculum_mappings",
    "sources",
    "source_documents",
    "document_chunks",
    "questions",
    "question_evidence",
    "question_reviews",
    "question_reports",
    "marking_schemes",
    "assessments",
    "assessment_sections",
    "assessment_questions",
    "assessment_attempts",
    "attempt_questions",
    "user_question_history",
    "user_mastery",
    "guest_sessions",
    "user_sessions",
    "auth_audit_logs",
    "admin_audit_logs",
)


def upgrade() -> None:
    bind = op.get_bind()
    # Fresh staging/production databases receive the complete current schema.
    # Existing current databases are adopted without dropping or recreating data.
    Base.metadata.create_all(
        bind=bind,
        tables=[Base.metadata.tables[name] for name in M10_BASELINE_TABLES],
        checkfirst=True,
    )

    # The manual subscription entitlement was added immediately before the
    # baseline. Adopt older initialized databases without requiring init_db().
    columns = {column["name"] for column in inspect(bind).get_columns("users")}
    if "is_subscribed" not in columns:
        bind.execute(text(
            "ALTER TABLE users ADD COLUMN is_subscribed BOOLEAN DEFAULT FALSE NOT NULL"
        ))


def downgrade() -> None:
    # A baseline downgrade must never destroy an adopted production database.
    raise RuntimeError("The M10 schema baseline is intentionally irreversible; restore from backup instead")
