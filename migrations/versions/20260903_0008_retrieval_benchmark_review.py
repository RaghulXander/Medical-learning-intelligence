"""Add human-reviewed retrieval benchmark workflow.

Revision ID: 20260903_0008
Revises: 20260903_0007
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260903_0008"
down_revision = "20260903_0007"
branch_labels = None
depends_on = None


GUID = sa.String(64).with_variant(postgresql.UUID(as_uuid=False), "postgresql")
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "retrieval_benchmarks",
        sa.Column("id", GUID, primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("source_file", sa.String(500), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_retrieval_benchmarks_slug", "retrieval_benchmarks", ["slug"], unique=True)
    op.create_index("ix_retrieval_benchmarks_status", "retrieval_benchmarks", ["status"])

    op.create_table(
        "retrieval_benchmark_cases",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "benchmark_id",
            GUID,
            sa.ForeignKey("retrieval_benchmarks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("case_key", sa.String(100), nullable=False),
        sa.Column("domain", sa.String(100), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("expected_chunk_ids", JSON_TYPE, nullable=False),
        sa.Column("out_of_corpus", sa.Boolean(), nullable=False),
        sa.Column("verification_status", sa.String(50), nullable=False),
        sa.Column(
            "reviewer_id",
            GUID,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "benchmark_id", "case_key", name="uq_retrieval_benchmark_case_key"
        ),
    )
    for column in ("benchmark_id", "domain", "reviewer_id", "verification_status"):
        op.create_index(
            f"ix_retrieval_benchmark_cases_{column}",
            "retrieval_benchmark_cases",
            [column],
        )

    op.create_table(
        "retrieval_benchmark_reviews",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "case_id",
            GUID,
            sa.ForeignKey("retrieval_benchmark_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reviewer_id",
            GUID,
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("previous_snapshot", JSON_TYPE, nullable=False),
        sa.Column("new_snapshot", JSON_TYPE, nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("case_id", "reviewer_id", "action"):
        op.create_index(
            f"ix_retrieval_benchmark_reviews_{column}",
            "retrieval_benchmark_reviews",
            [column],
        )


def downgrade() -> None:
    op.drop_table("retrieval_benchmark_reviews")
    op.drop_table("retrieval_benchmark_cases")
    op.drop_table("retrieval_benchmarks")
