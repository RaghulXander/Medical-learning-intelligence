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


def init_db(database_url: Optional[str] = None, engine: Optional[Engine] = None) -> Engine:
    """Initializes all database tables defined in models.Base."""
    eng = engine or get_engine(database_url)
    Base.metadata.create_all(bind=eng)
    return eng
