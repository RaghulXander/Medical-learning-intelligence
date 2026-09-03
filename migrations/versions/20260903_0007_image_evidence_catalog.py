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

TABLE_NULLABILITY = {
    "image_assets": {
        "id": False,
        "sha256": False,
        "pixel_hash": False,
        "filename": False,
        "storage_uri": True,
        "width": False,
        "height": False,
        "aspect_ratio": False,
        "file_size_bytes": False,
        "format": False,
        "triage_class": False,
        "curation_status": False,
        "rights_status": False,
        "entropy": False,
        "blank_score": False,
        "is_exact_duplicate": False,
        "metadata": False,
        "created_at": False,
    },
    "image_occurrences": {
        "id": False,
        "image_asset_id": False,
        "source_document_id": False,
        "pdf_page": True,
        "textbook_page": True,
        "figure_index": True,
        "figure_label": True,
        "extraction_id": True,
        "is_canonical": False,
        "metadata": False,
        "created_at": False,
    },
    "image_text_evidence_links": {
        "id": False,
        "image_asset_id": False,
        "document_chunk_id": False,
        "link_type": False,
        "confidence": False,
        "verification_status": False,
        "verified_by": True,
        "verified_at": True,
        "created_at": False,
    },
}

REQUIRED_FOREIGN_KEYS = {
    "image_assets": set(),
    "image_occurrences": {
        ("image_asset_id", "image_assets"),
        ("source_document_id", "source_documents"),
    },
    "image_text_evidence_links": {
        ("image_asset_id", "image_assets"),
        ("document_chunk_id", "document_chunks"),
    },
}

REQUIRED_INDEXES = {
    "image_assets": (
        (("curation_status",), False, "ix_image_assets_curation_status"),
        (("filename",), False, "ix_image_assets_filename"),
        (("pixel_hash",), False, "ix_image_assets_pixel_hash"),
        (("triage_class",), False, "ix_image_assets_triage_class"),
        (("sha256",), True, "ix_image_assets_sha256"),
    ),
    "image_occurrences": tuple(
        ((column,), False, f"ix_image_occurrences_{column}")
        for column in (
            "extraction_id",
            "image_asset_id",
            "pdf_page",
            "source_document_id",
            "textbook_page",
        )
    ),
    "image_text_evidence_links": tuple(
        ((column,), False, f"ix_image_text_evidence_links_{column}")
        for column in (
            "document_chunk_id",
            "image_asset_id",
            "link_type",
            "verification_status",
        )
    ),
}


def _index_signatures(inspector, table_name: str) -> set[tuple[tuple[str, ...], bool]]:
    signatures = {
        (tuple(index.get("column_names") or ()), bool(index.get("unique")))
        for index in inspector.get_indexes(table_name)
    }
    signatures.update(
        (tuple(constraint.get("column_names") or ()), True)
        for constraint in inspector.get_unique_constraints(table_name)
    )
    return signatures


def _adopt_existing_catalog_if_compatible() -> bool:
    """Adopt catalog tables created before Alembic owned this schema.

    M18's remote ingestion created these tables before migration 0007 existed.
    We may stamp them as migrated only after checking their safety-critical
    shape. A partial or incompatible catalog fails with a diagnostic instead
    of silently changing or deleting populated tables.
    """
    inspector = sa.inspect(op.get_bind())
    expected_tables = set(TABLE_NULLABILITY)
    present_tables = expected_tables.intersection(inspector.get_table_names())
    if not present_tables:
        return False
    if present_tables != expected_tables:
        missing = sorted(expected_tables - present_tables)
        raise RuntimeError(
            "Cannot adopt partial image catalog; missing tables: " + ", ".join(missing)
        )

    for table_name, expected_columns in TABLE_NULLABILITY.items():
        actual_columns = {
            column["name"]: bool(column["nullable"])
            for column in inspector.get_columns(table_name)
        }
        missing_columns = sorted(set(expected_columns) - set(actual_columns))
        if missing_columns:
            raise RuntimeError(
                f"Cannot adopt {table_name}; missing columns: "
                + ", ".join(missing_columns)
            )
        nullability_mismatches = sorted(
            column
            for column, nullable in expected_columns.items()
            if actual_columns[column] != nullable
        )
        if nullability_mismatches:
            raise RuntimeError(
                f"Cannot adopt {table_name}; incompatible nullability: "
                + ", ".join(nullability_mismatches)
            )
        primary_key = set(
            inspector.get_pk_constraint(table_name).get("constrained_columns") or ()
        )
        if primary_key != {"id"}:
            raise RuntimeError(f"Cannot adopt {table_name}; expected primary key on id")
        foreign_keys = {
            (column, foreign_key["referred_table"])
            for foreign_key in inspector.get_foreign_keys(table_name)
            for column in (foreign_key.get("constrained_columns") or ())
        }
        missing_foreign_keys = REQUIRED_FOREIGN_KEYS[table_name] - foreign_keys
        if missing_foreign_keys:
            rendered = ", ".join(
                f"{column}->{target}" for column, target in sorted(missing_foreign_keys)
            )
            raise RuntimeError(f"Cannot adopt {table_name}; missing foreign keys: {rendered}")

    for table_name, required_indexes in REQUIRED_INDEXES.items():
        signatures = _index_signatures(inspector, table_name)
        for columns, unique, index_name in required_indexes:
            if (columns, unique) not in signatures:
                op.create_index(index_name, table_name, list(columns), unique=unique)
                signatures.add((columns, unique))
    return True


def upgrade() -> None:
    if _adopt_existing_catalog_if_compatible():
        return

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
