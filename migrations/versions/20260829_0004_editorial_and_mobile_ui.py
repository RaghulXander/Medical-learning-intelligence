"""Add question revisions and server-driven mobile screen configurations.

Revision ID: 20260829_0004
Revises: 20260829_0003
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260829_0004"
down_revision = "20260829_0003"
branch_labels = None
depends_on = None


GUID = sa.String(64).with_variant(postgresql.UUID(as_uuid=False), "postgresql")
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "question_revisions",
        sa.Column("id", GUID, primary_key=True),
        sa.Column("question_id", GUID, sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("editor_id", GUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", JSON_TYPE, nullable=False),
        sa.Column("changed_fields", JSON_TYPE, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("edit_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("question_id", "revision_number", name="uq_question_revision_number"),
    )
    op.create_index("ix_question_revisions_question_id", "question_revisions", ["question_id"])
    op.create_index("ix_question_revisions_editor_id", "question_revisions", ["editor_id"])

    op.create_table(
        "mobile_screen_configurations",
        sa.Column("id", GUID, primary_key=True),
        sa.Column("screen_key", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("document", JSON_TYPE, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("published_by", GUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("screen_key", "version", name="uq_mobile_screen_version"),
    )
    op.create_index("ix_mobile_screen_configurations_screen_key", "mobile_screen_configurations", ["screen_key"])
    op.create_index("ix_mobile_screen_configurations_is_active", "mobile_screen_configurations", ["is_active"])
    op.create_index("ix_mobile_screen_configurations_published_by", "mobile_screen_configurations", ["published_by"])
    op.create_index("ix_mobile_screen_active", "mobile_screen_configurations", ["screen_key", "is_active"])


def downgrade() -> None:
    op.drop_index("ix_mobile_screen_active", table_name="mobile_screen_configurations")
    op.drop_index("ix_mobile_screen_configurations_published_by", table_name="mobile_screen_configurations")
    op.drop_index("ix_mobile_screen_configurations_is_active", table_name="mobile_screen_configurations")
    op.drop_index("ix_mobile_screen_configurations_screen_key", table_name="mobile_screen_configurations")
    op.drop_table("mobile_screen_configurations")
    op.drop_index("ix_question_revisions_editor_id", table_name="question_revisions")
    op.drop_index("ix_question_revisions_question_id", table_name="question_revisions")
    op.drop_table("question_revisions")
