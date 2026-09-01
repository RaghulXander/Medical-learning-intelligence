"""Add immutable, run-scoped pgvector embeddings.

Revision ID: 20260901_0005
Revises: 20260829_0004
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import VECTOR


revision = "20260901_0005"
down_revision = "20260829_0004"
branch_labels = None
depends_on = None


GUID = sa.String(64).with_variant(postgresql.UUID(as_uuid=False), "postgresql")
VECTOR_TYPE = VECTOR(768).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "embedding_runs",
        sa.Column("id", GUID, primary_key=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model_id", sa.String(150), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=True),
        sa.Column("dimension", sa.Integer(), nullable=False, server_default="768"),
        sa.Column("document_task_type", sa.String(50), nullable=False),
        sa.Column("query_task_type", sa.String(50), nullable=False),
        sa.Column("chunking_version", sa.String(100), nullable=False),
        sa.Column("status", sa.String(11), nullable=False),
        sa.Column("expected_chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_embedding_runs_provider", "embedding_runs", ["provider"])
    op.create_index("ix_embedding_runs_model_id", "embedding_runs", ["model_id"])
    op.create_index("ix_embedding_runs_status", "embedding_runs", ["status"])
    op.create_index("ix_embedding_runs_config_hash", "embedding_runs", ["config_hash"])

    op.create_table(
        "document_chunk_embeddings",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "run_id",
            GUID,
            sa.ForeignKey("embedding_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chunk_id",
            GUID,
            sa.ForeignKey("document_chunks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("embedding", VECTOR_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("run_id", "chunk_id", name="uq_document_chunk_embedding_run_chunk"),
    )
    op.create_index("ix_document_chunk_embeddings_run_id", "document_chunk_embeddings", ["run_id"])
    op.create_index("ix_document_chunk_embeddings_chunk_id", "document_chunk_embeddings", ["chunk_id"])
    op.create_index(
        "ix_document_chunk_embeddings_content_hash",
        "document_chunk_embeddings",
        ["content_hash"],
    )

    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX ix_document_chunk_embeddings_embedding_hnsw "
            "ON document_chunk_embeddings USING hnsw "
            "(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_document_chunk_embeddings_embedding_hnsw")
    op.drop_index("ix_document_chunk_embeddings_content_hash", table_name="document_chunk_embeddings")
    op.drop_index("ix_document_chunk_embeddings_chunk_id", table_name="document_chunk_embeddings")
    op.drop_index("ix_document_chunk_embeddings_run_id", table_name="document_chunk_embeddings")
    op.drop_table("document_chunk_embeddings")
    op.drop_index("ix_embedding_runs_config_hash", table_name="embedding_runs")
    op.drop_index("ix_embedding_runs_status", table_name="embedding_runs")
    op.drop_index("ix_embedding_runs_model_id", table_name="embedding_runs")
    op.drop_index("ix_embedding_runs_provider", table_name="embedding_runs")
    op.drop_table("embedding_runs")
