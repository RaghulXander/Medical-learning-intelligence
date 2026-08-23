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
    ADMIN = "ADMIN"
    USER = "USER"
    REVIEWER = "REVIEWER"
    EDUCATOR = "EDUCATOR"


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


class ReviewerType(str, enum.Enum):
    HUMAN = "human"
    AI_EVALUATOR = "ai_evaluator"
    PUBMEDBERT = "pubmedbert"


class ReportCategory(str, enum.Enum):
    INCORRECT_ANSWER = "incorrect_answer"
    INCORRECT_EXPLANATION = "incorrect_explanation"
    AMBIGUOUS_QUESTION = "ambiguous_question"
    MULTIPLE_POSSIBLE_ANSWERS = "multiple_possible_answers"
    POOR_WORDING = "poor_wording"
    WRONG_TOPIC = "wrong_topic"
    WRONG_DIFFICULTY = "wrong_difficulty"
    OUTDATED_INFORMATION = "outdated_information"
    SOURCE_REFERENCE_PROBLEM = "source_reference_problem"
    OTHER = "other"


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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    section_heading: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    document: Mapped["SourceDocument"] = relationship("SourceDocument", back_populates="chunks")
    evidence_links: Mapped[List["QuestionEvidence"]] = relationship("QuestionEvidence", back_populates="chunk")


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
    status: Mapped[QuestionStatus] = mapped_column(
        make_enum(QuestionStatus), default=QuestionStatus.IMPORTED, nullable=False, index=True
    )
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

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
    reports: Mapped[List["QuestionReport"]] = relationship(
        "QuestionReport", back_populates="question", cascade="all, delete-orphan"
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
