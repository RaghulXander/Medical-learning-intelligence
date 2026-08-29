"""Add the versioned Surgical Pathology ontology schema.

Revision ID: 20260829_0003
Revises: 20260826_0002
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260829_0003"
down_revision = "20260826_0002"
branch_labels = None
depends_on = None


GUID = sa.String(64).with_variant(postgresql.UUID(as_uuid=False), "postgresql")
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def enum_type(*values: str) -> sa.Enum:
    return sa.Enum(*values, native_enum=False)


def upgrade() -> None:
    op.create_table(
        "ontology_schemes",
        sa.Column("id", GUID, primary_key=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column(
            "status",
            enum_type("DRAFT", "RELEASED", "DEPRECATED", "RETIRED"),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", JSON_TYPE, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(100), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("code", "version", name="uq_ontology_scheme_version"),
    )
    op.create_index("ix_ontology_schemes_code", "ontology_schemes", ["code"])
    op.create_index("ix_ontology_schemes_status", "ontology_schemes", ["status"])

    op.create_table(
        "ontology_nodes",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "scheme_id",
            GUID,
            sa.ForeignKey("ontology_schemes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(150), nullable=False),
        sa.Column("preferred_name", sa.String(255), nullable=False),
        sa.Column(
            "node_type",
            enum_type(
                "ROOT", "DISCIPLINE", "METHOD_GROUP", "METHOD", "ANATOMIC_SYSTEM",
                "ORGAN", "ANATOMIC_SITE", "DISEASE_FAMILY", "DIAGNOSTIC_ENTITY",
                "MORPHOLOGIC_FEATURE", "CLINICAL_FEATURE", "GROSS_FEATURE", "IHC_MARKER",
                "MOLECULAR_ALTERATION", "GRADING_SYSTEM", "STAGING_SYSTEM",
                "LEARNING_OBJECTIVE",
            ),
            nullable=False,
        ),
        sa.Column("parent_id", GUID, sa.ForeignKey("ontology_nodes.id", ondelete="RESTRICT")),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            enum_type("DRAFT", "RELEASED", "DEPRECATED", "RETIRED"),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("metadata", JSON_TYPE, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(100), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("scheme_id", "code", name="uq_ontology_node_scheme_code"),
        sa.CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_ontology_node_not_self_parent"),
        sa.CheckConstraint("valid_to IS NULL OR valid_to > valid_from", name="ck_ontology_node_valid_range"),
    )
    op.create_index("ix_ontology_nodes_scheme_id", "ontology_nodes", ["scheme_id"])
    op.create_index("ix_ontology_nodes_parent_id", "ontology_nodes", ["parent_id"])
    op.create_index("ix_ontology_nodes_preferred_name", "ontology_nodes", ["preferred_name"])
    op.create_index("ix_ontology_nodes_node_type", "ontology_nodes", ["node_type"])
    op.create_index("ix_ontology_nodes_status", "ontology_nodes", ["status"])

    op.create_table(
        "ontology_aliases",
        sa.Column("id", GUID, primary_key=True),
        sa.Column("node_id", GUID, sa.ForeignKey("ontology_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias", sa.String(255), nullable=False),
        sa.Column("alias_type", sa.String(50), nullable=False, server_default="SYNONYM"),
        sa.Column("language", sa.String(20), nullable=False, server_default="en"),
        sa.Column("source", sa.String(500), nullable=True),
        sa.Column(
            "verification_status",
            enum_type("AI_SUGGESTED", "HUMAN_VERIFIED", "REJECTED"),
            nullable=False,
            server_default="AI_SUGGESTED",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("node_id", "alias", "language", name="uq_ontology_alias_node_text_language"),
    )
    op.create_index("ix_ontology_aliases_node_id", "ontology_aliases", ["node_id"])
    op.create_index("ix_ontology_aliases_alias", "ontology_aliases", ["alias"])
    op.create_index("ix_ontology_aliases_verification_status", "ontology_aliases", ["verification_status"])

    op.create_table(
        "ontology_relationships",
        sa.Column("id", GUID, primary_key=True),
        sa.Column("source_node_id", GUID, sa.ForeignKey("ontology_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "relationship_type",
            enum_type(
                "IS_A", "PART_OF", "LOCATED_IN", "HAS_CLINICAL_FEATURE", "HAS_GROSS_FEATURE",
                "HAS_MICROSCOPIC_FEATURE", "EXPRESSES_MARKER", "LACKS_MARKER",
                "HAS_MOLECULAR_ALTERATION", "USES_GRADING_SYSTEM", "USES_STAGING_SYSTEM",
                "DIFFERENTIAL_OF", "MIMICS", "ASSOCIATED_WITH", "SUPERSEDES",
            ),
            nullable=False,
        ),
        sa.Column("target_node_id", GUID, sa.ForeignKey("ontology_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("qualifier", JSON_TYPE, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("polarity", sa.String(30), nullable=True),
        sa.Column("frequency", sa.String(30), nullable=True),
        sa.Column("diagnostic_weight", sa.String(30), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1"),
        sa.Column(
            "verification_status",
            enum_type("AI_SUGGESTED", "HUMAN_VERIFIED", "REJECTED"),
            nullable=False,
            server_default="AI_SUGGESTED",
        ),
        sa.Column("created_by", sa.String(100), nullable=False, server_default="system"),
        sa.Column("reviewed_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "source_node_id", "relationship_type", "target_node_id",
            name="uq_ontology_relationship_triple",
        ),
        sa.CheckConstraint("source_node_id <> target_node_id", name="ck_ontology_relationship_not_self"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_ontology_relationship_confidence"),
    )
    op.create_index("ix_ontology_relationships_source_node_id", "ontology_relationships", ["source_node_id"])
    op.create_index("ix_ontology_relationships_target_node_id", "ontology_relationships", ["target_node_id"])
    op.create_index("ix_ontology_relationships_relationship_type", "ontology_relationships", ["relationship_type"])
    op.create_index("ix_ontology_relationships_verification_status", "ontology_relationships", ["verification_status"])

    op.create_table(
        "ontology_evidence",
        sa.Column("id", GUID, primary_key=True),
        sa.Column("node_id", GUID, sa.ForeignKey("ontology_nodes.id", ondelete="CASCADE")),
        sa.Column("relationship_id", GUID, sa.ForeignKey("ontology_relationships.id", ondelete="CASCADE")),
        sa.Column("source_id", GUID, sa.ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_id", GUID, sa.ForeignKey("source_documents.id", ondelete="SET NULL")),
        sa.Column("chunk_id", GUID, sa.ForeignKey("document_chunks.id", ondelete="SET NULL")),
        sa.Column("chapter", sa.String(150), nullable=True),
        sa.Column("section", sa.String(255), nullable=True),
        sa.Column("page_range", sa.String(50), nullable=True),
        sa.Column(
            "verification_status",
            enum_type("AI_SUGGESTED", "HUMAN_VERIFIED", "REJECTED"),
            nullable=False,
            server_default="AI_SUGGESTED",
        ),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(100), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(node_id IS NOT NULL AND relationship_id IS NULL) OR "
            "(node_id IS NULL AND relationship_id IS NOT NULL)",
            name="ck_ontology_evidence_exactly_one_target",
        ),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_ontology_evidence_confidence"),
    )
    for column in ("node_id", "relationship_id", "source_id", "document_id", "chunk_id", "verification_status"):
        op.create_index(f"ix_ontology_evidence_{column}", "ontology_evidence", [column])

    op.create_table(
        "question_ontology_mappings",
        sa.Column("id", GUID, primary_key=True),
        sa.Column("question_id", GUID, sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("node_id", GUID, sa.ForeignKey("ontology_nodes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "mapping_role",
            enum_type("PRIMARY", "SECONDARY", "DIFFERENTIAL", "METHOD"),
            nullable=False,
            server_default="PRIMARY",
        ),
        sa.Column(
            "mapping_method",
            enum_type("RULE", "AI_SUGGESTED", "HUMAN"),
            nullable=False,
            server_default="RULE",
        ),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1"),
        sa.Column(
            "verification_status",
            enum_type("AI_SUGGESTED", "HUMAN_VERIFIED", "REJECTED"),
            nullable=False,
            server_default="AI_SUGGESTED",
        ),
        sa.Column("ontology_version", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "supersedes_mapping_id",
            GUID,
            sa.ForeignKey("question_ontology_mappings.id", ondelete="SET NULL"),
        ),
        sa.Column("mapped_by", sa.String(100), nullable=False, server_default="system"),
        sa.Column("reviewed_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_question_ontology_mapping_confidence"),
    )
    for column in (
        "question_id", "node_id", "mapping_role", "mapping_method", "verification_status",
        "ontology_version", "is_active",
    ):
        op.create_index(f"ix_question_ontology_mappings_{column}", "question_ontology_mappings", [column])

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION validate_ontology_node_parent()
            RETURNS TRIGGER AS $$
            DECLARE
                parent_scheme UUID;
                parent_type TEXT;
                cycle_found BOOLEAN;
            BEGIN
                IF NEW.node_type = 'ROOT' THEN
                    IF NEW.parent_id IS NOT NULL THEN
                        RAISE EXCEPTION 'ROOT ontology nodes cannot have a parent';
                    END IF;
                    RETURN NEW;
                END IF;
                IF NEW.parent_id IS NULL THEN
                    RAISE EXCEPTION 'non-root ontology nodes require a parent';
                END IF;

                SELECT scheme_id, node_type INTO parent_scheme, parent_type
                FROM ontology_nodes WHERE id = NEW.parent_id;
                IF parent_scheme IS NULL OR parent_scheme <> NEW.scheme_id THEN
                    RAISE EXCEPTION 'ontology parent must exist in the same scheme';
                END IF;

                IF NOT (
                    (NEW.node_type = 'DISCIPLINE' AND parent_type = 'ROOT') OR
                    (NEW.node_type = 'METHOD_GROUP' AND parent_type IN ('DISCIPLINE', 'METHOD_GROUP')) OR
                    (NEW.node_type = 'METHOD' AND parent_type IN ('METHOD_GROUP', 'METHOD')) OR
                    (NEW.node_type = 'ANATOMIC_SYSTEM' AND parent_type IN ('DISCIPLINE', 'ANATOMIC_SYSTEM')) OR
                    (NEW.node_type = 'ORGAN' AND parent_type IN ('DISCIPLINE', 'ANATOMIC_SYSTEM', 'ORGAN')) OR
                    (NEW.node_type = 'ANATOMIC_SITE' AND parent_type IN ('ANATOMIC_SYSTEM', 'ORGAN', 'ANATOMIC_SITE')) OR
                    (NEW.node_type = 'DISEASE_FAMILY' AND parent_type IN ('ANATOMIC_SYSTEM', 'ORGAN', 'ANATOMIC_SITE', 'DISEASE_FAMILY', 'METHOD_GROUP')) OR
                    (NEW.node_type = 'DIAGNOSTIC_ENTITY' AND parent_type IN ('ANATOMIC_SYSTEM', 'ORGAN', 'ANATOMIC_SITE', 'DISEASE_FAMILY')) OR
                    (NEW.node_type IN ('MORPHOLOGIC_FEATURE', 'CLINICAL_FEATURE', 'GROSS_FEATURE', 'IHC_MARKER', 'MOLECULAR_ALTERATION', 'GRADING_SYSTEM', 'STAGING_SYSTEM') AND parent_type = 'METHOD_GROUP') OR
                    (NEW.node_type = 'LEARNING_OBJECTIVE' AND parent_type IN ('METHOD', 'DISEASE_FAMILY', 'DIAGNOSTIC_ENTITY'))
                ) THEN
                    RAISE EXCEPTION 'invalid ontology parent type % for child type %', parent_type, NEW.node_type;
                END IF;

                WITH RECURSIVE ancestors(id, parent_id) AS (
                    SELECT id, parent_id FROM ontology_nodes WHERE id = NEW.parent_id
                    UNION ALL
                    SELECT node.id, node.parent_id
                    FROM ontology_nodes node
                    JOIN ancestors ON node.id = ancestors.parent_id
                )
                SELECT EXISTS(SELECT 1 FROM ancestors WHERE id = NEW.id) INTO cycle_found;
                IF cycle_found THEN
                    RAISE EXCEPTION 'ontology parent cycle detected';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER trg_validate_ontology_node_parent
            BEFORE INSERT OR UPDATE OF parent_id, node_type, scheme_id ON ontology_nodes
            FOR EACH ROW EXECUTE FUNCTION validate_ontology_node_parent();
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_validate_ontology_node_parent ON ontology_nodes")
        op.execute("DROP FUNCTION IF EXISTS validate_ontology_node_parent()")

    op.drop_table("question_ontology_mappings")
    op.drop_table("ontology_evidence")
    op.drop_table("ontology_relationships")
    op.drop_table("ontology_aliases")
    op.drop_table("ontology_nodes")
    op.drop_table("ontology_schemes")
