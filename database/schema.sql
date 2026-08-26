-- ============================================================================
-- Medical Exam AI — PostgreSQL 16 Production Schema
-- ============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ----------------------------------------------------------------------------
-- Custom ENUM Types
-- ----------------------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE user_role_enum AS ENUM ('ADMIN', 'USER', 'REVIEWER', 'EDUCATOR');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE curriculum_level_enum AS ENUM ('speciality', 'subject', 'topic', 'subtopic', 'learning_objective');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE depth_level_enum AS ENUM ('undergraduate', 'postgraduate', 'super_specialty', 'general');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE topic_mapping_status_enum AS ENUM ('UNMAPPED', 'RAW_ONLY', 'MAPPED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE question_type_enum AS ENUM ('single_best_answer', 'multiple_choice', 'case_based');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE difficulty_enum AS ENUM ('easy', 'medium', 'hard');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE cognitive_level_enum AS ENUM ('recall', 'understanding', 'application', 'analysis');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE question_status_enum AS ENUM (
        'IMPORTED',
        'GENERATED',
        'AI_REVIEW',
        'HUMAN_REVIEW',
        'APPROVED',
        'REJECTED',
        'REPORTED',
        'RETIRED'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE source_type_enum AS ENUM ('textbook', 'who_classification', 'guideline', 'journal_article');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE verification_status_enum AS ENUM ('AI_SUGGESTED', 'HUMAN_VERIFIED', 'REJECTED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE reviewer_type_enum AS ENUM ('human', 'ai_evaluator', 'pubmedbert');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE report_category_enum AS ENUM (
        'incorrect_answer',
        'incorrect_explanation',
        'ambiguous_question',
        'multiple_possible_answers',
        'poor_wording',
        'wrong_topic',
        'wrong_difficulty',
        'outdated_information',
        'source_reference_problem',
        'other'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE report_status_enum AS ENUM ('OPEN', 'UNDER_REVIEW', 'RESOLVED', 'DISMISSED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ----------------------------------------------------------------------------
-- 1. Users Table
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    role user_role_enum NOT NULL DEFAULT 'USER',
    password_hash VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 2. Courses Table (Academic Programs & Examinations)
-- e.g. MBBS, MD Pathology, DM Oncopathology, NEET-PG
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    target_audience VARCHAR(100),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_courses_code ON courses(code);

-- ----------------------------------------------------------------------------
-- 3. Canonical Knowledge Domain Hierarchy (Independent of single course)
-- Speciality -> Subject -> Topic -> Subtopic -> Learning Objective
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS curriculum_topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID REFERENCES curriculum_topics(id) ON DELETE CASCADE,
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    level curriculum_level_enum NOT NULL DEFAULT 'topic',
    display_order INT NOT NULL DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_curriculum_topics_parent ON curriculum_topics(parent_id);
CREATE INDEX IF NOT EXISTS idx_curriculum_topics_level ON curriculum_topics(level);

-- ----------------------------------------------------------------------------
-- 4. Course Curriculum Mappings (Cross-course topic sharing & depth expectations)
-- Maps shared knowledge domain topics into MBBS, MD, DM, NEET-PG with specific depth/weightage
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS course_curriculum_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    topic_id UUID NOT NULL REFERENCES curriculum_topics(id) ON DELETE CASCADE,
    depth_level depth_level_enum NOT NULL DEFAULT 'postgraduate',
    exam_weightage FLOAT DEFAULT 0.0,
    is_core BOOLEAN NOT NULL DEFAULT TRUE,
    competency_code VARCHAR(100),
    learning_objectives JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_course_topic UNIQUE (course_id, topic_id)
);

CREATE INDEX IF NOT EXISTS idx_ccm_course ON course_curriculum_mappings(course_id);
CREATE INDEX IF NOT EXISTS idx_ccm_topic ON course_curriculum_mappings(topic_id);

-- ----------------------------------------------------------------------------
-- 5. Sources (Authoritative Reference Corpus / Authors & Works)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    short_name VARCHAR(100) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255),
    edition VARCHAR(50),
    year INT,
    publisher VARCHAR(100),
    source_type source_type_enum NOT NULL DEFAULT 'textbook',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 6. Source Documents (Specific Editions, Volumes, Chapters, PDFs)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS source_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    edition VARCHAR(50),
    volume VARCHAR(50),
    chapter_number INT,
    page_start INT,
    page_end INT,
    file_path VARCHAR(500),
    file_hash VARCHAR(64),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_source_documents_source ON source_documents(source_id);

-- ----------------------------------------------------------------------------
-- 7. Document Chunks (Granular Extracted Text & Vector Embeddings for RAG)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES source_documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL DEFAULT 0,
    section_heading VARCHAR(255),
    page_number INT,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_chunks_doc ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_hash ON document_chunks(content_hash);

-- ----------------------------------------------------------------------------
-- 8. Questions Table (Core Domain Model)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_source VARCHAR(50) NOT NULL DEFAULT 'medmcqa',
    external_source_id VARCHAR(100) NOT NULL UNIQUE,
    source_exam_id VARCHAR(100),
    speciality VARCHAR(100) NOT NULL DEFAULT 'Pathology',
    subject VARCHAR(100) NOT NULL DEFAULT 'Pathology',

    -- Topic Decoupling
    topic_name_original VARCHAR(255),
    topic_name_normalized VARCHAR(255),
    topic_mapping_status topic_mapping_status_enum NOT NULL DEFAULT 'UNMAPPED',
    primary_topic_id UUID REFERENCES curriculum_topics(id) ON DELETE SET NULL,
    learning_objective TEXT,

    -- Content
    question_type question_type_enum NOT NULL DEFAULT 'single_best_answer',
    stem TEXT NOT NULL,
    options JSONB NOT NULL,
    correct_option CHAR(1),
    correct_index INT NOT NULL DEFAULT -1,
    is_labeled BOOLEAN NOT NULL DEFAULT TRUE,
    explanation TEXT,

    -- Difficulty & Assessment
    difficulty difficulty_enum,
    cognitive_level cognitive_level_enum,
    educational_level VARCHAR(32),
    target_exam_levels JSONB NOT NULL DEFAULT '[]'::jsonb,
    status question_status_enum NOT NULL DEFAULT 'IMPORTED',
    quality_score FLOAT,

    -- Classification & Provenance
    classification_source VARCHAR(32) NOT NULL DEFAULT 'UNKNOWN',
    classification_status VARCHAR(32) NOT NULL DEFAULT 'UNCLASSIFIED',
    classification_confidence FLOAT NOT NULL DEFAULT 1.0,
    knowledge_era VARCHAR(50) NOT NULL DEFAULT 'CURRENT',
    source_version VARCHAR(100),

    -- Deduplication & Similarity Tracking
    content_hash CHAR(64) NOT NULL,
    exact_stem_hash CHAR(64) NOT NULL,
    norm_stem_hash CHAR(64) NOT NULL,
    duplicate_signals JSONB,

    -- Audit & Raw Metadata
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by VARCHAR(100) NOT NULL DEFAULT 'system_import',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Question Table Indexes
CREATE INDEX IF NOT EXISTS idx_questions_status ON questions(status);
CREATE INDEX IF NOT EXISTS idx_questions_source_exam ON questions(source_exam_id);
CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject);
CREATE INDEX IF NOT EXISTS idx_questions_primary_topic ON questions(primary_topic_id);
CREATE INDEX IF NOT EXISTS idx_questions_topic_status ON questions(topic_mapping_status);
CREATE INDEX IF NOT EXISTS idx_questions_content_hash ON questions(content_hash);
CREATE INDEX IF NOT EXISTS idx_questions_norm_stem_hash ON questions(norm_stem_hash);
CREATE INDEX IF NOT EXISTS idx_questions_created_at ON questions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_questions_options_gin ON questions USING GIN (options);
CREATE INDEX IF NOT EXISTS idx_questions_metadata_gin ON questions USING GIN (metadata);

-- ----------------------------------------------------------------------------
-- 9. Question Evidence (Provenance Linkage to Source, Document, and Chunk)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS question_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    document_id UUID REFERENCES source_documents(id) ON DELETE SET NULL,
    chunk_id UUID REFERENCES document_chunks(id) ON DELETE SET NULL,
    volume VARCHAR(50),
    chapter VARCHAR(100),
    page_range VARCHAR(50),
    section VARCHAR(150),
    excerpt TEXT,
    verification_status verification_status_enum NOT NULL DEFAULT 'AI_SUGGESTED',
    confidence FLOAT NOT NULL DEFAULT 1.0,
    verified_by UUID REFERENCES users(id) ON DELETE SET NULL,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_question ON question_evidence(question_id);
CREATE INDEX IF NOT EXISTS idx_evidence_source ON question_evidence(source_id);
CREATE INDEX IF NOT EXISTS idx_evidence_doc ON question_evidence(document_id);
CREATE INDEX IF NOT EXISTS idx_evidence_chunk ON question_evidence(chunk_id);
CREATE INDEX IF NOT EXISTS idx_evidence_status ON question_evidence(verification_status);

-- ----------------------------------------------------------------------------
-- 10. Question Reviews (Human & AI Evaluation Audit Log)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS question_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    reviewer_id UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewer_type reviewer_type_enum NOT NULL DEFAULT 'human',
    previous_status VARCHAR(50),
    new_status VARCHAR(50),
    review_notes TEXT,
    quality_score FLOAT,
    signals JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reviews_question ON question_reviews(question_id);
CREATE INDEX IF NOT EXISTS idx_reviews_reviewer ON question_reviews(reviewer_id);

-- ----------------------------------------------------------------------------
-- 11. Question Reports (User Feedback & Error Resolution)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS question_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    reporter_id UUID REFERENCES users(id) ON DELETE SET NULL,
    category report_category_enum NOT NULL,
    description TEXT NOT NULL,
    suggested_correction TEXT,
    status report_status_enum NOT NULL DEFAULT 'OPEN',
    resolution_notes TEXT,
    resolved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_question ON question_reports(question_id);
CREATE INDEX IF NOT EXISTS idx_reports_status ON question_reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_category ON question_reports(category);

-- ----------------------------------------------------------------------------
-- 12. Assessment Engine & Marking Schemes
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS marking_schemes (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    correct_marks FLOAT NOT NULL DEFAULT 4.0,
    penalty_marks FLOAT NOT NULL DEFAULT 1.0,
    unanswered_marks FLOAT NOT NULL DEFAULT 0.0
);

INSERT INTO marking_schemes (id, name, correct_marks, penalty_marks, unanswered_marks) VALUES
('NEET_4_1', 'NEET Standard (+4, -1)', 4.0, 1.0, 0.0),
('INICET_1_033', 'INI-CET Standard (+1, -0.333)', 1.0, 0.3333, 0.0),
('PROPORTIONAL_1_025', 'Proportional (+1, -0.25)', 1.0, 0.25, 0.0),
('ZERO_PENALTY', 'Learning Mode (+1, 0)', 1.0, 0.0, 0.0)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL, -- 'MOCK', 'SUBJECT', 'TOPIC', 'SUBTOPIC', 'DAILY', 'CUSTOM'
    title VARCHAR(255) NOT NULL,
    question_count INT NOT NULL,
    duration_seconds INT NOT NULL,
    marking_scheme_id VARCHAR(50) NOT NULL REFERENCES marking_schemes(id),
    navigation_policy VARCHAR(50) NOT NULL DEFAULT 'FREE', -- 'FREE', 'SECTION_LOCKED', 'LINEAR'
    blueprint JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assessment_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    section_order INT NOT NULL DEFAULT 1,
    name VARCHAR(150) NOT NULL,
    question_count INT NOT NULL,
    duration_seconds INT,
    navigation_policy VARCHAR(50) DEFAULT 'FREE',
    CONSTRAINT uq_assessment_section_order UNIQUE (assessment_id, section_order)
);

CREATE TABLE IF NOT EXISTS assessment_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    section_id UUID REFERENCES assessment_sections(id) ON DELETE SET NULL,
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE RESTRICT,
    sequence INT NOT NULL,
    snapshot JSONB NOT NULL,
    CONSTRAINT uq_assessment_question_seq UNIQUE (assessment_id, sequence)
);

CREATE TABLE IF NOT EXISTS assessment_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    status VARCHAR(50) NOT NULL DEFAULT 'IN_PROGRESS', -- 'IN_PROGRESS', 'SUBMITTED', 'TIMED_OUT', 'ABANDONED'
    score FLOAT DEFAULT 0.0,
    max_score FLOAT DEFAULT 0.0,
    percentage FLOAT DEFAULT 0.0,
    correct_count INT DEFAULT 0,
    incorrect_count INT DEFAULT 0,
    unanswered_count INT DEFAULT 0,
    time_spent_seconds INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS attempt_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id UUID NOT NULL REFERENCES assessment_attempts(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE RESTRICT,
    selected_answer VARCHAR(10),
    correct_answer VARCHAR(10) NOT NULL,
    is_correct BOOLEAN,
    marks_awarded FLOAT DEFAULT 0.0,
    time_spent_seconds INT DEFAULT 0,
    marked_for_review BOOLEAN DEFAULT FALSE,
    question_snapshot JSONB NOT NULL,
    CONSTRAINT uq_attempt_question UNIQUE (attempt_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_assessment_attempts_user ON assessment_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_assessment_questions_assessment ON assessment_questions(assessment_id);
CREATE INDEX IF NOT EXISTS idx_attempt_questions_attempt ON attempt_questions(attempt_id);

