"""Add the private pathology image evidence catalog.

Revision ID: 20260903_0007
Revises: 20260901_0006
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260903_0007"
down_revision = "20260901_0006"
branch_labels = None
depends_on = None


GUID = sa.String(64).with_variant(postgresql.UUID(as_uuid=False), "postgresql")
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "image_assets",
        sa.Column("id", GUID, primary_key=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("pixel_hash", sa.String(64), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_uri", sa.String(500), nullable=True),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("aspect_ratio", sa.Float(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("triage_class", sa.String(50), nullable=False),
        sa.Column("curation_status", sa.String(50), nullable=False),
        sa.Column("rights_status", sa.String(50), nullable=False),
        sa.Column("entropy", sa.Float(), nullable=False),
        sa.Column("blank_score", sa.Float(), nullable=False),
        sa.Column("is_exact_duplicate", sa.Boolean(), nullable=False),
        sa.Column("metadata", JSON_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in (
        "curation_status",
        "filename",
        "pixel_hash",
        "triage_class",
    ):
        op.create_index(f"ix_image_assets_{column}", "image_assets", [column])
    op.create_index("ix_image_assets_sha256", "image_assets", ["sha256"], unique=True)

    op.create_table(
        "image_occurrences",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "image_asset_id",
            GUID,
            sa.ForeignKey("image_assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_document_id",
            GUID,
            sa.ForeignKey("source_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pdf_page", sa.Integer(), nullable=True),
        sa.Column("textbook_page", sa.Integer(), nullable=True),
        sa.Column("figure_index", sa.Integer(), nullable=True),
        sa.Column("figure_label", sa.String(100), nullable=True),
        sa.Column("extraction_id", sa.String(150), nullable=True),
        sa.Column("is_canonical", sa.Boolean(), nullable=False),
        sa.Column("metadata", JSON_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in (
        "extraction_id",
        "image_asset_id",
        "pdf_page",
        "source_document_id",
        "textbook_page",
    ):
        op.create_index(
            f"ix_image_occurrences_{column}", "image_occurrences", [column]
        )

    op.create_table(
        "image_text_evidence_links",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "image_asset_id",
            GUID,
            sa.ForeignKey("image_assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_chunk_id",
            GUID,
            sa.ForeignKey("document_chunks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("link_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("verification_status", sa.String(50), nullable=False),
        sa.Column("verified_by", sa.String(100), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in (
        "document_chunk_id",
        "image_asset_id",
        "link_type",
        "verification_status",
    ):
        op.create_index(
            f"ix_image_text_evidence_links_{column}",
            "image_text_evidence_links",
            [column],
        )


def downgrade() -> None:
    op.drop_table("image_text_evidence_links")
    op.drop_table("image_occurrences")
    op.drop_table("image_assets")
