"""Add auditable image curation and multimodal provenance gates.

Revision ID: 20260905_0009
Revises: 20260903_0008
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260905_0009"
down_revision = "20260903_0008"
branch_labels = None
depends_on = None


GUID = sa.String(64).with_variant(postgresql.UUID(as_uuid=False), "postgresql")
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column("image_assets", sa.Column("reviewed_utility_class", sa.String(50)))
    op.add_column("image_assets", sa.Column("reviewed_diagnosis", sa.String(255)))
    op.add_column("image_assets", sa.Column("reviewed_stain", sa.String(100)))
    op.add_column("image_assets", sa.Column("reviewed_magnification", sa.String(50)))
    op.add_column("image_assets", sa.Column("reviewed_caption", sa.Text()))
    op.add_column("image_assets", sa.Column("automated_rank_score", sa.Float()))
    op.add_column("image_assets", sa.Column("automated_rank_version", sa.String(50)))
    op.add_column("image_assets", sa.Column("automated_suggested_utility_class", sa.String(50)))
    op.add_column("image_assets", sa.Column("automated_tags", JSON_TYPE))
    op.add_column(
        "image_assets",
        sa.Column("pilot_shortlisted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "image_assets",
        sa.Column("storage_access_status", sa.String(50), nullable=False, server_default="UNVERIFIED"),
    )
    op.add_column(
        "image_assets",
        sa.Column("metadata_verification_status", sa.String(50), nullable=False, server_default="UNVERIFIED"),
    )
    op.add_column(
        "image_assets", sa.Column("review_revision", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column("image_assets", sa.Column("curation_reviewed_by", GUID))
    op.add_column("image_assets", sa.Column("curation_reviewed_at", sa.DateTime(timezone=True)))
    op.create_foreign_key(
        "fk_image_assets_curation_reviewer",
        "image_assets",
        "users",
        ["curation_reviewed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_image_assets_metadata_verification_status", "image_assets", ["metadata_verification_status"])
    op.create_index("ix_image_assets_storage_access_status", "image_assets", ["storage_access_status"])
    op.create_index("ix_image_assets_curation_reviewed_by", "image_assets", ["curation_reviewed_by"])
    op.create_index("ix_image_assets_pilot_shortlisted", "image_assets", ["pilot_shortlisted"])
    op.create_index("ix_image_assets_automated_rank_score", "image_assets", ["automated_rank_score"])

    # An evidence link must identify the exact occurrence, not merely a reused
    # binary asset. Existing suggestions remain nullable until a human resolves
    # them in the review UI.
    op.add_column("image_text_evidence_links", sa.Column("image_occurrence_id", GUID))
    op.create_foreign_key(
        "fk_image_text_links_occurrence",
        "image_text_evidence_links",
        "image_occurrences",
        ["image_occurrence_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_image_text_evidence_links_occurrence_id",
        "image_text_evidence_links",
        ["image_occurrence_id"],
    )

    op.create_table(
        "image_reviews",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "image_asset_id",
            GUID,
            sa.ForeignKey("image_assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reviewer_id",
            GUID,
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("previous_snapshot", JSON_TYPE, nullable=False),
        sa.Column("new_snapshot", JSON_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("image_asset_id", "reviewer_id", "action"):
        op.create_index(f"ix_image_reviews_{column}", "image_reviews", [column])

    op.create_table(
        "question_image_evidence",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "question_id", GUID, sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "image_asset_id", GUID, sa.ForeignKey("image_assets.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "image_occurrence_id",
            GUID,
            sa.ForeignKey("image_occurrences.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "image_text_evidence_link_id",
            GUID,
            sa.ForeignKey("image_text_evidence_links.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("role", sa.String(50), nullable=False, server_default="QUESTION_STEM"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "question_id", "image_occurrence_id", name="uq_question_image_evidence_occurrence"
        ),
    )
    for column in ("question_id", "image_asset_id", "image_occurrence_id"):
        op.create_index(f"ix_question_image_evidence_{column}", "question_image_evidence", [column])


def downgrade() -> None:
    op.drop_table("question_image_evidence")
    op.drop_table("image_reviews")
    op.drop_index("ix_image_text_evidence_links_occurrence_id", table_name="image_text_evidence_links")
    op.drop_constraint("fk_image_text_links_occurrence", "image_text_evidence_links", type_="foreignkey")
    op.drop_column("image_text_evidence_links", "image_occurrence_id")
    op.drop_index("ix_image_assets_curation_reviewed_by", table_name="image_assets")
    op.drop_index("ix_image_assets_automated_rank_score", table_name="image_assets")
    op.drop_index("ix_image_assets_pilot_shortlisted", table_name="image_assets")
    op.drop_index("ix_image_assets_storage_access_status", table_name="image_assets")
    op.drop_index("ix_image_assets_metadata_verification_status", table_name="image_assets")
    op.drop_constraint("fk_image_assets_curation_reviewer", "image_assets", type_="foreignkey")
    for column in (
        "curation_reviewed_at",
        "curation_reviewed_by",
        "review_revision",
        "metadata_verification_status",
        "storage_access_status",
        "reviewed_caption",
        "pilot_shortlisted",
        "automated_tags",
        "automated_suggested_utility_class",
        "automated_rank_version",
        "automated_rank_score",
        "reviewed_magnification",
        "reviewed_stain",
        "reviewed_diagnosis",
        "reviewed_utility_class",
    ):
        op.drop_column("image_assets", column)
