"""
database/db.py

Database connection manager and session utilities.
Defaults to DATABASE_URL environment variable or local SQLite file (data/medical_exam.db).
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from dotenv import load_dotenv

# Automatically load environment variables from .env if present
load_dotenv()

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

from database.models import Base

DEFAULT_SQLITE_PATH = Path("data/medical_exam.db")


def get_default_db_url() -> str:
    """Returns DATABASE_URL from environment or fallback to SQLite."""
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DEFAULT_SQLITE_PATH.resolve()}"


def get_engine(database_url: Optional[str] = None, echo: bool = False) -> Engine:
    """Creates a SQLAlchemy engine with graceful SQLite fallback if PostgreSQL is unreachable."""
    url = database_url or get_default_db_url()
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(url, echo=echo, connect_args=connect_args)
    if not url.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                pass
        except Exception:
            DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
            fallback_url = f"sqlite:///{DEFAULT_SQLITE_PATH.resolve()}"
            engine = create_engine(fallback_url, echo=echo, connect_args={"check_same_thread": False})
    return engine


_engine_cache: Optional[Engine] = None
_sessionmaker_cache: Optional[sessionmaker[Session]] = None


def get_session_factory(engine: Optional[Engine] = None) -> sessionmaker[Session]:
    """Returns cached sessionmaker for engine."""
    global _engine_cache, _sessionmaker_cache
    if engine is None:
        if _engine_cache is None:
            _engine_cache = get_engine()
        engine = _engine_cache

    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def session_scope(engine: Optional[Engine] = None) -> Generator[Session, None, None]:
    """Transactional scope context manager for DB sessions."""
    factory = get_session_factory(engine)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


from sqlalchemy import text


def _ensure_missing_question_columns(engine: Engine) -> None:
    """Adds any newly introduced columns to existing questions tables."""
    with engine.connect() as conn:
        if engine.url.drivername.startswith("sqlite"):
            try:
                rows = conn.exec_driver_sql("PRAGMA table_info(questions)").fetchall()
            except Exception:
                return
            existing_columns = {row[1] for row in rows}
            column_specs = {
                "source_exam_id": "TEXT",
                "topic_name_original": "TEXT",
                "topic_name_normalized": "TEXT",
                "topic_mapping_status": "TEXT",
                "primary_topic_id": "TEXT",
                "learning_objective": "TEXT",
                "correct_index": "INTEGER",
                "is_labeled": "BOOLEAN",
                "difficulty": "TEXT",
                "educational_level": "TEXT",
                "target_exam_levels": "TEXT DEFAULT '[]'",
                "classification_source": "TEXT",
                "classification_status": "TEXT",
                "classification_confidence": "REAL",
                "knowledge_era": "TEXT",
                "source_version": "TEXT",
                "exact_stem_hash": "TEXT",
                "norm_stem_hash": "TEXT",
                "duplicate_signals": "TEXT",
                "created_by": "TEXT",
                "updated_at": "DATETIME",
            }
            for column_name, column_type in column_specs.items():
                if column_name not in existing_columns:
                    conn.exec_driver_sql(f"ALTER TABLE questions ADD COLUMN {column_name} {column_type};")
            conn.commit()
            return

        try:
            existing_rows = conn.exec_driver_sql(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = 'questions'"
            ).fetchall()
        except Exception:
            return
        existing_columns = {row[0] for row in existing_rows}
        column_specs = {
            "source_exam_id": "VARCHAR(100)",
            "topic_name_original": "VARCHAR(255)",
            "topic_name_normalized": "VARCHAR(255)",
            "topic_mapping_status": "VARCHAR(32)",
            "primary_topic_id": "UUID",
            "learning_objective": "TEXT",
            "correct_index": "INTEGER DEFAULT -1",
            "is_labeled": "BOOLEAN DEFAULT TRUE",
            "difficulty": "VARCHAR(20)",
            "educational_level": "VARCHAR(32)",
            "target_exam_levels": "JSONB DEFAULT '[]'::jsonb",
            "classification_source": "VARCHAR(32)",
            "classification_status": "VARCHAR(32)",
            "classification_confidence": "FLOAT DEFAULT 1.0",
            "knowledge_era": "VARCHAR(50) DEFAULT 'CURRENT'",
            "source_version": "VARCHAR(100)",
            "exact_stem_hash": "VARCHAR(64)",
            "norm_stem_hash": "VARCHAR(64)",
            "duplicate_signals": "JSONB",
            "created_by": "VARCHAR(100) DEFAULT 'system_import'",
            "updated_at": "TIMESTAMPTZ",
        }
        for column_name, column_type in column_specs.items():
            if column_name not in existing_columns:
                conn.execute(text(f"ALTER TABLE questions ADD COLUMN IF NOT EXISTS {column_name} {column_type};"))
        conn.commit()


def _ensure_missing_document_chunk_columns(engine: Engine) -> None:
    """Adds newly introduced columns to existing document_chunks table."""
    with engine.connect() as conn:
        if engine.url.drivername.startswith("sqlite"):
            try:
                rows = conn.exec_driver_sql("PRAGMA table_info(document_chunks)").fetchall()
            except Exception:
                return
            existing_columns = {row[1] for row in rows}
            column_specs = {
                "slice_id": "TEXT",
                "pdf_page": "INTEGER",
                "textbook_page": "INTEGER",
                "chapter_name": "TEXT",
                "word_count": "INTEGER DEFAULT 0",
                "embedding": "TEXT",
                "embedding_model": "TEXT",
            }
            for column_name, column_type in column_specs.items():
                if column_name not in existing_columns:
                    conn.exec_driver_sql(f"ALTER TABLE document_chunks ADD COLUMN {column_name} {column_type};")
            conn.commit()
            return

        try:
            existing_rows = conn.exec_driver_sql(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = 'document_chunks'"
            ).fetchall()
        except Exception:
            return
        existing_columns = {row[0] for row in existing_rows}
        column_specs = {
            "slice_id": "VARCHAR(150)",
            "pdf_page": "INTEGER",
            "textbook_page": "INTEGER",
            "chapter_name": "VARCHAR(255)",
            "word_count": "INTEGER DEFAULT 0",
            "embedding": "JSONB",
            "embedding_model": "VARCHAR(100)",
        }
        for column_name, column_type in column_specs.items():
            if column_name not in existing_columns:
                conn.execute(text(f"ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS {column_name} {column_type};"))
        conn.commit()


def init_db(engine: Optional[Engine] = None, database_url: Optional[str] = None) -> Engine:
    """Initializes all database tables and ensures newly added schema columns exist."""
    if isinstance(engine, str) and database_url is None:
        database_url = engine
        engine = None
    eng = engine or get_engine(database_url)
    Base.metadata.create_all(bind=eng)

    # Automatically synchronize new columns on existing database tables (Postgres / SQLite)
    is_sqlite = eng.url.drivername.startswith("sqlite")
    alter_queries = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_email_verified BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS target_exam VARCHAR(100);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS target_year INTEGER;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS medical_college VARCHAR(255);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS residency_stage VARCHAR(100);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS primary_speciality VARCHAR(150);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS current_streak INTEGER DEFAULT 0;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS longest_streak INTEGER DEFAULT 0;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active_date DATE;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_subscribed BOOLEAN DEFAULT FALSE NOT NULL;",
    ]

    if not is_sqlite:
        with eng.connect() as conn:
            try:
                conn.execution_options(isolation_level="AUTOCOMMIT").execute(
                    text("ALTER TYPE user_role_enum ADD VALUE IF NOT EXISTS 'SUPER_ADMIN';")
                )
            except Exception:
                pass

            for q in alter_queries:
                try:
                    conn.execute(text(q))
                    conn.commit()
                except Exception:
                    pass

    # `create_all()` never adds fields to an existing table. Keep this explicit
    # compatibility upgrade until M9 replaces runtime synchronization with Alembic.
    # Add newly introduced columns to existing tables
    _ensure_missing_question_columns(eng)
    _ensure_missing_document_chunk_columns(eng)

    # Ensure permanent Super Admin users are guaranteed in database table
    try:
        import uuid
        from datetime import datetime, timezone
        from database.models import User, UserRole

        super_admins = [
            {"email": "raghuldpi95@gmail.com", "name": "Dr. Raghul Xander"},
            {"email": "raghuljayan@gmail.com", "name": "Dr. Raghul Jayan"},
        ]

        factory = sessionmaker(bind=eng, autoflush=False, autocommit=False)
        with factory() as session:
            for sa in super_admins:
                user = session.query(User).filter(User.email == sa["email"]).first()
                if not user:
                    user = User(
                        id=str(uuid.uuid4()),
                        email=sa["email"],
                        name=sa["name"],
                        role=UserRole.SUPER_ADMIN,
                        is_email_verified=True,
                        is_active=True,
                        target_exam="NEET_SS",
                        primary_speciality="Oncopathology",
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    session.add(user)
                else:
                    user.role = UserRole.SUPER_ADMIN
                    user.is_email_verified = True
                    user.is_active = True
            session.commit()
    except Exception:
        pass

    return eng
