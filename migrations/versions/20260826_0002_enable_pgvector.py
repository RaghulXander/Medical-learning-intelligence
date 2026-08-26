"""Enable pgvector on PostgreSQL deployments.

Revision ID: 20260826_0002
Revises: 20260826_0001
"""

from alembic import op


revision = "20260826_0002"
down_revision = "20260826_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Other schemas/data may depend on vector. Never remove it automatically.
    pass
