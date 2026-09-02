"""
database/models.py

SQLAlchemy 2.0 Declarative ORM models for Medical Exam AI.
Supports PostgreSQL (with JSONB/UUID) and SQLite fallback for local development and testing.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, TypeDecorator, String as SQLString
from pgvector.sqlalchemy import VECTOR

from backend.domain.surgical_pathology_ontology import (
    OntologyMappingMethod,
    OntologyMappingRole,
    OntologyMappingRunStatus,
    OntologyNodeStatus,
    OntologyNodeType,
    OntologyRelationshipType,
    OntologySchemeStatus,
)


class Base(DeclarativeBase):
    pass


# -----------------------------------------------------------------------------
# Cross-database GUID Type Decorator
# -----------------------------------------------------------------------------
class GUID(TypeDecorator):
    """Platform-independent GUID/UUID type.
    Uses PostgreSQL's native UUID type, otherwise uses String(64).
    """
    impl = SQLString(64)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=False))
        else:
            return dialect.type_descriptor(SQLString(64))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return str(value)


# Cross-database JSON type (JSONB on PostgreSQL, JSON on SQLite)
JSONType = JSON().with_variant(JSONB, "postgresql")
EmbeddingVectorType = VECTOR(768).with_variant(JSON(), "sqlite")


def make_enum(enum_cls):
    """Creates an Enum type that serializes enum.value instead of enum.name."""
    return Enum(
        enum_cls,
        values_callable=lambda x: [e.value for e in x],
        native_enum=False,
    )


# -----------------------------------------------------------------------------
# Python Enums
# -----------------------------------------------------------------------------
class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    REVIEWER = "REVIEWER"
    EDUCATOR = "EDUCATOR"
    USER = "USER"


class CurriculumLevel(str, enum.Enum):
    SPECIALITY = "speciality"
    SUBJECT = "subject"
    TOPIC = "topic"
    SUBTOPIC = "subtopic"
    LEARNING_OBJECTIVE = "learning_objective"


class DepthLevel(str, enum.Enum):
    UNDERGRADUATE = "undergraduate"
    POSTGRADUATE = "postgraduate"
    SUPER_SPECIALTY = "super_specialty"
    GENERAL = "general"


class TopicMappingStatus(str, enum.Enum):
    UNMAPPED = "UNMAPPED"
    RAW_ONLY = "RAW_ONLY"
    MAPPED = "MAPPED"


class QuestionType(str, enum.Enum):
    SINGLE_BEST_ANSWER = "single_best_answer"
    MULTIPLE_CHOICE = "multiple_choice"
    CASE_BASED = "case_based"


class DifficultyLevel(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class CognitiveLevel(str, enum.Enum):
    RECALL = "recall"
    UNDERSTANDING = "understanding"
    APPLICATION = "application"
    ANALYSIS = "analysis"


class QuestionStatus(str, enum.Enum):
    IMPORTED = "IMPORTED"
    GENERATED = "GENERATED"
    AI_REVIEW = "AI_REVIEW"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REPORTED = "REPORTED"
    RETIRED = "RETIRED"


class SourceType(str, enum.Enum):
    TEXTBOOK = "textbook"
    WHO_CLASSIFICATION = "who_classification"
    GUIDELINE = "guideline"
    JOURNAL_ARTICLE = "journal_article"


class VerificationStatus(str, enum.Enum):
    AI_SUGGESTED = "AI_SUGGESTED"
    HUMAN_VERIFIED = "HUMAN_VERIFIED"
    REJECTED = "REJECTED"


class EmbeddingRunStatus(str, enum.Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"


class ReviewerType(str, enum.Enum):
    HUMAN = "human"
    AI_EVALUATOR = "ai_evaluator"
    PUBMEDBERT = "pubmedbert"


class ReportCategory(str, enum.Enum):
    INCORRECT_ANSWER = "incorrect_answer"
    INCORRECT_EXPLANATION = "incorrect_explanation"
    AMBIGUOUS_QUESTION = "ambiguous_question"
    OUTDATED_GUIDELINE = "outdated_guideline"
    OTHER = "other"


class AssessmentType(str, enum.Enum):
    MOCK = "MOCK"
    SUBJECT = "SUBJECT"
    TOPIC = "TOPIC"
    SUBTOPIC = "SUBTOPIC"
    DAILY = "DAILY"
    CUSTOM = "CUSTOM"


class NavigationPolicy(str, enum.Enum):
    FREE = "FREE"
    SECTION_LOCKED = "SECTION_LOCKED"
    LINEAR = "LINEAR"


class AttemptStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    TIMED_OUT = "TIMED_OUT"
    ABANDONED = "ABANDONED"


class EducationalLevel(str, enum.Enum):
    MBBS = "MBBS"
    MD = "MD"
    DNB = "DNB"
    DM = "DM"
    MCH = "MCH"
    SUPER_SPECIALTY = "SUPER_SPECIALTY"


class ClassificationSource(str, enum.Enum):
    MANUAL = "MANUAL"
    CURRICULUM_INFERENCE = "CURRICULUM_INFERENCE"
    AI_CLASSIFIED = "AI_CLASSIFIED"
    UNKNOWN = "UNKNOWN"


class ClassificationStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    PENDING_REVIEW = "PENDING_REVIEW"
    UNCLASSIFIED = "UNCLASSIFIED"


class AssessmentMode(str, enum.Enum):
    LEARNING = "LEARNING"
    PRACTICE = "PRACTICE"
    MOCK = "MOCK"
    GRAND_TEST = "GRAND_TEST"


class ConfidenceLevel(str, enum.Enum):
    GUESS = "GUESS"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ReportStatus(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


# -----------------------------------------------------------------------------
# 1. User Model
# -----------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(make_enum(UserRole), default=UserRole.USER, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    google_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    target_exam: Mapped[Optional[str]] = mapped_column(String(50), default="NEET_SS", nullable=True, index=True)
    target_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    medical_college: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    residency_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    primary_speciality: Mapped[Optional[str]] = mapped_column(String(100), default="Pathology", nullable=True)
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_active_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Manual entitlement until the Milestone 50 billing/subscription system.
    is_subscribed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# -----------------------------------------------------------------------------
# 2. Course Model (Medical Programs / Exams)
# -----------------------------------------------------------------------------
class Course(Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_audience: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    course_mappings: Mapped[List["CourseCurriculumMapping"]] = relationship("CourseCurriculumMapping", back_populates="course", cascade="all, delete-orphan")


# -----------------------------------------------------------------------------
# 3. Canonical Knowledge Domain Hierarchy (Independent of single course)
# Speciality -> Subject -> Topic -> Subtopic -> Learning Objective
# -----------------------------------------------------------------------------
class CurriculumTopic(Base):
    __tablename__ = "curriculum_topics"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("curriculum_topics.id", ondelete="CASCADE"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    level: Mapped[CurriculumLevel] = mapped_column(
        make_enum(CurriculumLevel), default=CurriculumLevel.TOPIC, nullable=False, index=True
    )
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    children: Mapped[List["CurriculumTopic"]] = relationship("CurriculumTopic", backref="parent", remote_side=[id])
    course_mappings: Mapped[List["CourseCurriculumMapping"]] = relationship("CourseCurriculumMapping", back_populates="topic", cascade="all, delete-orphan")
    primary_questions: Mapped[List["Question"]] = relationship("Question", back_populates="primary_topic")


# -----------------------------------------------------------------------------
# 4. Course Curriculum Mapping (Cross-course topic sharing & depth expectations)
# -----------------------------------------------------------------------------
class CourseCurriculumMapping(Base):
    __tablename__ = "course_curriculum_mappings"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id: Mapped[str] = mapped_column(GUID(), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id: Mapped[str] = mapped_column(GUID(), ForeignKey("curriculum_topics.id", ondelete="CASCADE"), nullable=False, index=True)
    depth_level: Mapped[DepthLevel] = mapped_column(
        make_enum(DepthLevel), default=DepthLevel.POSTGRADUATE, nullable=False
    )
    exam_weightage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_core: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    competency_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    learning_objectives: Mapped[List[Dict[str, Any]]] = mapped_column(JSONType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint("course_id", "topic_id", name="uq_course_topic"),)

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="course_mappings")
    topic: Mapped["CurriculumTopic"] = relationship("CurriculumTopic", back_populates="course_mappings")


# -----------------------------------------------------------------------------
# 4a. Versioned Knowledge Ontology
# -----------------------------------------------------------------------------
class OntologyScheme(Base):
    __tablename__ = "ontology_schemes"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[OntologySchemeStatus] = mapped_column(
        make_enum(OntologySchemeStatus), default=OntologySchemeStatus.DRAFT, nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONType, default=dict)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (UniqueConstraint("code", "version", name="uq_ontology_scheme_version"),)

    nodes: Mapped[List["OntologyNode"]] = relationship(
        "OntologyNode", back_populates="scheme", cascade="all, delete-orphan"
    )


class OntologyNode(Base):
    __tablename__ = "ontology_nodes"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    scheme_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("ontology_schemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(150), nullable=False)
    preferred_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    node_type: Mapped[OntologyNodeType] = mapped_column(make_enum(OntologyNodeType), nullable=False, index=True)
    parent_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("ontology_nodes.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[OntologyNodeStatus] = mapped_column(
        make_enum(OntologyNodeStatus), default=OntologyNodeStatus.DRAFT, nullable=False, index=True
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONType, default=dict)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    valid_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("scheme_id", "code", name="uq_ontology_node_scheme_code"),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_ontology_node_not_self_parent"),
        CheckConstraint("valid_to IS NULL OR valid_to > valid_from", name="ck_ontology_node_valid_range"),
    )

    scheme: Mapped["OntologyScheme"] = relationship("OntologyScheme", back_populates="nodes")
    parent: Mapped[Optional["OntologyNode"]] = relationship(
        "OntologyNode", remote_side="OntologyNode.id", back_populates="children"
    )
    children: Mapped[List["OntologyNode"]] = relationship("OntologyNode", back_populates="parent")
    aliases: Mapped[List["OntologyAlias"]] = relationship(
        "OntologyAlias", back_populates="node", cascade="all, delete-orphan"
    )


class OntologyAlias(Base):
    __tablename__ = "ontology_aliases"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    node_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("ontology_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    alias_type: Mapped[str] = mapped_column(String(50), default="SYNONYM", nullable=False)
    language: Mapped[str] = mapped_column(String(20), default="en", nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        make_enum(VerificationStatus), default=VerificationStatus.AI_SUGGESTED, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("node_id", "alias", "language", name="uq_ontology_alias_node_text_language"),
    )

    node: Mapped["OntologyNode"] = relationship("OntologyNode", back_populates="aliases")


class OntologyRelationship(Base):
    __tablename__ = "ontology_relationships"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_node_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("ontology_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type: Mapped[OntologyRelationshipType] = mapped_column(
        make_enum(OntologyRelationshipType), nullable=False, index=True
    )
    target_node_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("ontology_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    qualifier: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    polarity: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    frequency: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    diagnostic_weight: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        make_enum(VerificationStatus), default=VerificationStatus.AI_SUGGESTED, nullable=False, index=True
    )
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "source_node_id",
            "relationship_type",
            "target_node_id",
            name="uq_ontology_relationship_triple",
        ),
        CheckConstraint("source_node_id <> target_node_id", name="ck_ontology_relationship_not_self"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_ontology_relationship_confidence"),
    )

    source_node: Mapped["OntologyNode"] = relationship("OntologyNode", foreign_keys=[source_node_id])
    target_node: Mapped["OntologyNode"] = relationship("OntologyNode", foreign_keys=[target_node_id])
    evidence_items: Mapped[List["OntologyEvidence"]] = relationship(
        "OntologyEvidence", back_populates="ontology_relationship", cascade="all, delete-orphan"
    )


class OntologyEvidence(Base):
    __tablename__ = "ontology_evidence"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    node_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("ontology_nodes.id", ondelete="CASCADE"), nullable=True, index=True
    )
    relationship_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("ontology_relationships.id", ondelete="CASCADE"), nullable=True, index=True
    )
    source_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    document_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("source_documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    chunk_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    chapter: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    section: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    page_range: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        make_enum(VerificationStatus), default=VerificationStatus.AI_SUGGESTED, nullable=False, index=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint(
            "(node_id IS NOT NULL AND relationship_id IS NULL) OR "
            "(node_id IS NULL AND relationship_id IS NOT NULL)",
            name="ck_ontology_evidence_exactly_one_target",
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_ontology_evidence_confidence"),
    )

    node: Mapped[Optional["OntologyNode"]] = relationship("OntologyNode")
    ontology_relationship: Mapped[Optional["OntologyRelationship"]] = relationship(
        "OntologyRelationship", back_populates="evidence_items"
    )
    source: Mapped["Source"] = relationship("Source")
    document: Mapped[Optional["SourceDocument"]] = relationship("SourceDocument")
    chunk: Mapped[Optional["DocumentChunk"]] = relationship("DocumentChunk")


class QuestionOntologyMapping(Base):
    __tablename__ = "question_ontology_mappings"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("ontology_nodes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    mapping_role: Mapped[OntologyMappingRole] = mapped_column(
        make_enum(OntologyMappingRole), default=OntologyMappingRole.PRIMARY, nullable=False, index=True
    )
    mapping_method: Mapped[OntologyMappingMethod] = mapped_column(
        make_enum(OntologyMappingMethod), default=OntologyMappingMethod.RULE, nullable=False, index=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        make_enum(VerificationStatus), default=VerificationStatus.AI_SUGGESTED, nullable=False, index=True
    )
    ontology_version: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    supersedes_mapping_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("question_ontology_mappings.id", ondelete="SET NULL"), nullable=True
    )
    mapping_run_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("ontology_mapping_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    match_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    mapped_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_question_ontology_mapping_confidence"),
    )

    question: Mapped["Question"] = relationship("Question", back_populates="ontology_mappings")
    node: Mapped["OntologyNode"] = relationship("OntologyNode")
    supersedes_mapping: Mapped[Optional["QuestionOntologyMapping"]] = relationship(
        "QuestionOntologyMapping", remote_side="QuestionOntologyMapping.id"
    )
    mapping_run: Mapped[Optional["OntologyMappingRun"]] = relationship(
        "OntologyMappingRun", back_populates="mappings"
    )


class OntologyMappingRun(Base):
    __tablename__ = "ontology_mapping_runs"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    scheme_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("ontology_schemes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    ontology_version: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    rule_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[OntologyMappingRunStatus] = mapped_column(
        make_enum(OntologyMappingRunStatus), nullable=False, index=True
    )
    configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    question_filter: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    input_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ambiguous_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unmapped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_mapping_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False, default="m14_mapping_rule")
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rolled_back_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    scheme: Mapped["OntologyScheme"] = relationship("OntologyScheme")
    mappings: Mapped[List["QuestionOntologyMapping"]] = relationship(
        "QuestionOntologyMapping", back_populates="mapping_run"
    )


# -----------------------------------------------------------------------------
# 5. Source Model (Authoritative Knowledge Corpus / Works)
# -----------------------------------------------------------------------------
class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    short_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    edition: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    publisher: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_type: Mapped[SourceType] = mapped_column(
        make_enum(SourceType), default=SourceType.TEXTBOOK, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    documents: Mapped[List["SourceDocument"]] = relationship("SourceDocument", back_populates="source", cascade="all, delete-orphan")
    evidence_items: Mapped[List["QuestionEvidence"]] = relationship("QuestionEvidence", back_populates="source")


# -----------------------------------------------------------------------------
# 6. Source Document Model (Specific Editions, Volumes, Chapters, PDFs)
# -----------------------------------------------------------------------------
class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id: Mapped[str] = mapped_column(GUID(), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    edition: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    volume: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    chapter_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    source: Mapped["Source"] = relationship("Source", back_populates="documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    evidence_links: Mapped[List["QuestionEvidence"]] = relationship("QuestionEvidence", back_populates="document")


# -----------------------------------------------------------------------------
# 7. Document Chunk Model (Extracted text chunks & vector embeddings)
# -----------------------------------------------------------------------------
class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(GUID(), ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    slice_id: Mapped[Optional[str]] = mapped_column(String(150), nullable=True, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pdf_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    textbook_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Backward compat with pdf_page
    chapter_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    section_heading: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSONType, nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    document: Mapped["SourceDocument"] = relationship("SourceDocument", back_populates="chunks")
    evidence_links: Mapped[List["QuestionEvidence"]] = relationship("QuestionEvidence", back_populates="chunk")
    embedding_records: Mapped[List["DocumentChunkEmbedding"]] = relationship(
        "DocumentChunkEmbedding",
        back_populates="chunk",
        cascade="all, delete-orphan",
    )


# -----------------------------------------------------------------------------
# 7A. Versioned embedding runs and immutable chunk vectors
# -----------------------------------------------------------------------------
class EmbeddingRun(Base):
    __tablename__ = "embedding_runs"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False, default=768)
    document_task_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="RETRIEVAL_DOCUMENT"
    )
    query_task_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="RETRIEVAL_QUERY"
    )
    chunking_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[EmbeddingRunStatus] = mapped_column(
        make_enum(EmbeddingRunStatus),
        nullable=False,
        default=EmbeddingRunStatus.CREATED,
        index=True,
    )
    expected_chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    embeddings: Mapped[List["DocumentChunkEmbedding"]] = relationship(
        "DocumentChunkEmbedding",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class DocumentChunkEmbedding(Base):
    __tablename__ = "document_chunk_embeddings"
    __table_args__ = (
        UniqueConstraint("run_id", "chunk_id", name="uq_document_chunk_embedding_run_chunk"),
    )

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("embedding_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    embedding: Mapped[List[float]] = mapped_column(EmbeddingVectorType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    run: Mapped["EmbeddingRun"] = relationship("EmbeddingRun", back_populates="embeddings")
    chunk: Mapped["DocumentChunk"] = relationship(
        "DocumentChunk", back_populates="embedding_records"
    )


# -----------------------------------------------------------------------------
# 8. Question Model (Core MCQ Domain Model)
# -----------------------------------------------------------------------------
class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_source: Mapped[str] = mapped_column(String(50), default="medmcqa", nullable=False)
    external_source_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    source_exam_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    speciality: Mapped[str] = mapped_column(String(100), default="Pathology", nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(100), default="Pathology", nullable=False, index=True)

    # Decoupled Topic System
    topic_name_original: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    topic_name_normalized: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    topic_mapping_status: Mapped[TopicMappingStatus] = mapped_column(
        make_enum(TopicMappingStatus), default=TopicMappingStatus.UNMAPPED, nullable=False, index=True
    )
    primary_topic_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("curriculum_topics.id", ondelete="SET NULL"), nullable=True, index=True
    )
    learning_objective: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Content
    question_type: Mapped[QuestionType] = mapped_column(
        make_enum(QuestionType), default=QuestionType.SINGLE_BEST_ANSWER, nullable=False
    )
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[List[Dict[str, Any]]] = mapped_column(JSONType, nullable=False)
    correct_option: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    correct_index: Mapped[int] = mapped_column(Integer, default=-1, nullable=False)
    is_labeled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Assessment & Evaluation
    difficulty: Mapped[Optional[DifficultyLevel]] = mapped_column(
        make_enum(DifficultyLevel), nullable=True
    )
    cognitive_level: Mapped[Optional[CognitiveLevel]] = mapped_column(
        make_enum(CognitiveLevel), nullable=True
    )
    educational_level: Mapped[Optional[EducationalLevel]] = mapped_column(
        make_enum(EducationalLevel), nullable=True, index=True
    )
    target_exam_levels: Mapped[List[str]] = mapped_column(JSONType, default=list, nullable=False)
    status: Mapped[QuestionStatus] = mapped_column(
        make_enum(QuestionStatus), default=QuestionStatus.IMPORTED, nullable=False, index=True
    )
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Classification & Provenance
    classification_source: Mapped[ClassificationSource] = mapped_column(
        make_enum(ClassificationSource), default=ClassificationSource.UNKNOWN, nullable=False, index=True
    )
    classification_status: Mapped[ClassificationStatus] = mapped_column(
        make_enum(ClassificationStatus), default=ClassificationStatus.UNCLASSIFIED, nullable=False
    )
    classification_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    knowledge_era: Mapped[str] = mapped_column(String(50), default="CURRENT", nullable=False)
    source_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Cohort & Taxonomy Tagging (e.g. OLD_MCQ vs NEW_MCQ vs MULTIMODAL_IMAGE_MCQ)
    origin_cohort: Mapped[str] = mapped_column(String(50), default="OLD_MCQ", nullable=False, index=True)
    tags: Mapped[List[str]] = mapped_column(JSONType, default=list, nullable=False)

    # Multimodal Pathology Image Attachments
    has_images: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    image_assets: Mapped[List[Dict[str, Any]]] = mapped_column(JSONType, default=list, nullable=False)

    # Similarity & Deduplication Hashes
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    exact_stem_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    norm_stem_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    duplicate_signals: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)

    # Metadata & Audit
    metadata_json: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONType, default=dict)
    created_by: Mapped[str] = mapped_column(String(100), default="system_import", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    primary_topic: Mapped[Optional["CurriculumTopic"]] = relationship("CurriculumTopic", back_populates="primary_questions")
    evidence_links: Mapped[List["QuestionEvidence"]] = relationship(
        "QuestionEvidence", back_populates="question", cascade="all, delete-orphan"
    )
    reviews: Mapped[List["QuestionReview"]] = relationship(
        "QuestionReview", back_populates="question", cascade="all, delete-orphan"
    )
    revisions: Mapped[List["QuestionRevision"]] = relationship(
        "QuestionRevision", back_populates="question", cascade="all, delete-orphan"
    )
    reports: Mapped[List["QuestionReport"]] = relationship(
        "QuestionReport", back_populates="question", cascade="all, delete-orphan"
    )
    ontology_mappings: Mapped[List["QuestionOntologyMapping"]] = relationship(
        "QuestionOntologyMapping", back_populates="question", cascade="all, delete-orphan"
    )


# -----------------------------------------------------------------------------
# 8a. Question Revision Model (immutable editorial snapshots)
# -----------------------------------------------------------------------------
class QuestionRevision(Base):
    __tablename__ = "question_revisions"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    editor_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[Dict[str, Any]] = mapped_column(JSONType, nullable=False)
    changed_fields: Mapped[List[str]] = mapped_column(JSONType, default=list, nullable=False)
    edit_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    question: Mapped["Question"] = relationship("Question", back_populates="revisions")

    __table_args__ = (
        UniqueConstraint("question_id", "revision_number", name="uq_question_revision_number"),
    )


# -----------------------------------------------------------------------------
# 9. Question Evidence Model (Linkage to Source, Document, and Chunk)
# -----------------------------------------------------------------------------
class QuestionEvidence(Base):
    __tablename__ = "question_evidence"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    document_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("source_documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    chunk_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    volume: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    chapter: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    page_range: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    section: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        make_enum(VerificationStatus), default=VerificationStatus.AI_SUGGESTED, nullable=False, index=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    verified_by: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="evidence_links")
    source: Mapped["Source"] = relationship("Source", back_populates="evidence_items")
    document: Mapped[Optional["SourceDocument"]] = relationship("SourceDocument", back_populates="evidence_links")
    chunk: Mapped[Optional["DocumentChunk"]] = relationship("DocumentChunk", back_populates="evidence_links")


# -----------------------------------------------------------------------------
# 10. Question Review Model
# -----------------------------------------------------------------------------
class QuestionReview(Base):
    __tablename__ = "question_reviews"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reviewer_type: Mapped[ReviewerType] = mapped_column(
        make_enum(ReviewerType), default=ReviewerType.HUMAN, nullable=False
    )
    previous_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    signals: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="reviews")


# -----------------------------------------------------------------------------
# 11. Question Report Model
# -----------------------------------------------------------------------------
class QuestionReport(Base):
    __tablename__ = "question_reports"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reporter_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[ReportCategory] = mapped_column(
        make_enum(ReportCategory), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_correction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        make_enum(ReportStatus), default=ReportStatus.OPEN, nullable=False, index=True
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="reports")


# -----------------------------------------------------------------------------
# 12. Marking Scheme Model
# -----------------------------------------------------------------------------
class MarkingScheme(Base):
    __tablename__ = "marking_schemes"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    correct_marks: Mapped[float] = mapped_column(Float, default=4.0, nullable=False)
    penalty_marks: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    unanswered_marks: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


# -----------------------------------------------------------------------------
# 13. Assessment Model
# -----------------------------------------------------------------------------
class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    type: Mapped[AssessmentType] = mapped_column(
        make_enum(AssessmentType), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    marking_scheme_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("marking_schemes.id"), nullable=False
    )
    navigation_policy: Mapped[NavigationPolicy] = mapped_column(
        make_enum(NavigationPolicy), default=NavigationPolicy.FREE, nullable=False
    )
    blueprint: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    marking_scheme: Mapped["MarkingScheme"] = relationship("MarkingScheme")
    sections: Mapped[List["AssessmentSection"]] = relationship(
        "AssessmentSection", back_populates="assessment", cascade="all, delete-orphan", order_by="AssessmentSection.section_order"
    )
    assessment_questions: Mapped[List["AssessmentQuestion"]] = relationship(
        "AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan", order_by="AssessmentQuestion.sequence"
    )
    attempts: Mapped[List["AssessmentAttempt"]] = relationship(
        "AssessmentAttempt", back_populates="assessment", cascade="all, delete-orphan"
    )


# -----------------------------------------------------------------------------
# 14. Assessment Section Model
# -----------------------------------------------------------------------------
class AssessmentSection(Base):
    __tablename__ = "assessment_sections"
    __table_args__ = (
        UniqueConstraint("assessment_id", "section_order", name="uq_assessment_section_order"),
    )

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    navigation_policy: Mapped[NavigationPolicy] = mapped_column(
        make_enum(NavigationPolicy), default=NavigationPolicy.FREE, nullable=False
    )

    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="sections")
    questions: Mapped[List["AssessmentQuestion"]] = relationship("AssessmentQuestion", back_populates="section")


# -----------------------------------------------------------------------------
# 15. Assessment Question Snapshot Model
# -----------------------------------------------------------------------------
class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"
    __table_args__ = (
        UniqueConstraint("assessment_id", "sequence", name="uq_assessment_question_seq"),
    )

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("assessment_sections.id", ondelete="SET NULL"), nullable=True, index=True
    )
    question_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[Dict[str, Any]] = mapped_column(JSONType, nullable=False)

    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="assessment_questions")
    section: Mapped[Optional["AssessmentSection"]] = relationship("AssessmentSection", back_populates="questions")
    question: Mapped["Question"] = relationship("Question")


# -----------------------------------------------------------------------------
# 16. Assessment Attempt Model
# -----------------------------------------------------------------------------
class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    guest_session_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("guest_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[AttemptStatus] = mapped_column(
        make_enum(AttemptStatus), default=AttemptStatus.IN_PROGRESS, nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incorrect_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unanswered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="attempts")
    user: Mapped[Optional["User"]] = relationship("User")
    guest_session: Mapped[Optional["GuestSession"]] = relationship("GuestSession", back_populates="attempts")
    attempt_questions: Mapped[List["AttemptQuestion"]] = relationship(
        "AttemptQuestion", back_populates="attempt", cascade="all, delete-orphan"
    )


# -----------------------------------------------------------------------------
# 17. Attempt Question Response Model
# -----------------------------------------------------------------------------
class AttemptQuestion(Base):
    __tablename__ = "attempt_questions"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question"),
    )

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    attempt_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    selected_answer: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    correct_answer: Mapped[str] = mapped_column(String(10), nullable=False)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    marks_awarded: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    marked_for_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    question_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSONType, nullable=False)

    # Relationships
    attempt: Mapped["AssessmentAttempt"] = relationship("AssessmentAttempt", back_populates="attempt_questions")
    question: Mapped["Question"] = relationship("Question")


# -----------------------------------------------------------------------------
# 18. User Question Interaction History (Raw behavioral dataset)
# -----------------------------------------------------------------------------
class UserQuestionHistory(Base):
    __tablename__ = "user_question_history"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    selected_answer: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, index=True)
    marks_awarded: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence_level: Mapped[Optional[ConfidenceLevel]] = mapped_column(
        make_enum(ConfidenceLevel), nullable=True
    )
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    question: Mapped["Question"] = relationship("Question")
    attempt: Mapped["AssessmentAttempt"] = relationship("AssessmentAttempt")


# -----------------------------------------------------------------------------
# 19. User Mastery Model (Unified relational learner model on CurriculumTopic)
# -----------------------------------------------------------------------------
class UserMastery(Base):
    __tablename__ = "user_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "curriculum_node_id", name="uq_user_curriculum_mastery"),
    )

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    curriculum_node_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("curriculum_topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    smoothed_accuracy: Mapped[float] = mapped_column(Float, default=50.0, nullable=False, index=True)
    attempted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incorrect_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exposure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_time_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    curriculum_node: Mapped["CurriculumTopic"] = relationship("CurriculumTopic")


# -----------------------------------------------------------------------------
# 20. Guest Session Model (Anonymous Diagnostic Funnel)
# -----------------------------------------------------------------------------
class GuestSession(Base):
    __tablename__ = "guest_sessions"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    converted_user_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    merged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    converted_user: Mapped[Optional["User"]] = relationship("User")
    attempts: Mapped[List["AssessmentAttempt"]] = relationship("AssessmentAttempt", back_populates="guest_session")


# -----------------------------------------------------------------------------
# 21. User Session Model (Refresh Token & Multi-Device Audit)
# -----------------------------------------------------------------------------
class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    device_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user: Mapped["User"] = relationship("User")


# -----------------------------------------------------------------------------
# 22. Auth Audit Log Model
# -----------------------------------------------------------------------------
class AuthAuditLog(Base):
    __tablename__ = "auth_audit_logs"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User")


# -----------------------------------------------------------------------------
# 23. Admin Audit Log Model
# -----------------------------------------------------------------------------
class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    changes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    admin: Mapped["User"] = relationship("User")


# -----------------------------------------------------------------------------
# 24. Published server-driven mobile screen documents
# -----------------------------------------------------------------------------
class MobileScreenConfiguration(Base):
    __tablename__ = "mobile_screen_configurations"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    screen_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    document: Mapped[Dict[str, Any]] = mapped_column(JSONType, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    published_by: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("screen_key", "version", name="uq_mobile_screen_version"),
        Index("ix_mobile_screen_active", "screen_key", "is_active"),
    )
