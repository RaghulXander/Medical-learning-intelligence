"""Add reversible ontology question-mapping runs.

Revision ID: 20260901_0006
Revises: 20260901_0005
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260901_0006"
down_revision = "20260901_0005"
branch_labels = None
depends_on = None


GUID = sa.String(64).with_variant(postgresql.UUID(as_uuid=False), "postgresql")
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "ontology_mapping_runs",
        sa.Column("id", GUID, primary_key=True),
        sa.Column("scheme_id", GUID, sa.ForeignKey("ontology_schemes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("ontology_version", sa.String(100), nullable=False),
        sa.Column("rule_version", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("configuration_hash", sa.String(64), nullable=False),
        sa.Column("question_filter", JSON_TYPE, nullable=False),
        sa.Column("input_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matched_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ambiguous_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unmapped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_mapping_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in ("scheme_id", "ontology_version", "status", "configuration_hash"):
        op.create_index(f"ix_ontology_mapping_runs_{column}", "ontology_mapping_runs", [column])

    op.add_column(
        "question_ontology_mappings",
        sa.Column("mapping_run_id", GUID, nullable=True),
    )
    op.add_column(
        "question_ontology_mappings",
        sa.Column("match_metadata", JSON_TYPE, nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_foreign_key(
        "fk_question_ontology_mappings_mapping_run",
        "question_ontology_mappings",
        "ontology_mapping_runs",
        ["mapping_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_question_ontology_mappings_mapping_run_id",
        "question_ontology_mappings",
        ["mapping_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_question_ontology_mappings_mapping_run_id",
        table_name="question_ontology_mappings",
    )
    op.drop_constraint(
        "fk_question_ontology_mappings_mapping_run",
        "question_ontology_mappings",
        type_="foreignkey",
    )
    op.drop_column("question_ontology_mappings", "match_metadata")
    op.drop_column("question_ontology_mappings", "mapping_run_id")
    for column in reversed(("scheme_id", "ontology_version", "status", "configuration_hash")):
        op.drop_index(f"ix_ontology_mapping_runs_{column}", table_name="ontology_mapping_runs")
    op.drop_table("ontology_mapping_runs")
