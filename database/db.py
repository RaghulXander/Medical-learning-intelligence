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
    """Creates a SQLAlchemy engine."""
    url = database_url or get_default_db_url()
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(url, echo=echo, connect_args=connect_args)
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

