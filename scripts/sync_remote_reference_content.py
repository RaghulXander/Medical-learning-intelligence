"""Copy reference-document text from remote PostgreSQL into local SQLite.

The remote transaction is explicitly read-only. Only Source, SourceDocument, and
DocumentChunk rows are copied; embeddings are intentionally omitted so they can
be generated for the local environment in a later milestone.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from dotenv import dotenv_values
from sqlalchemy import Engine, create_engine, func, select, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.models import Base, DocumentChunk, Source, SourceDocument


DEFAULT_DOCUMENTS = (
    "robbins_review",
    "robbins_pathologic_basis_11th",
)
DEFAULT_LOCAL_DB = PROJECT_ROOT / "data" / "medical_exam.db"


def _batched(rows: list[dict[str, Any]], size: int = 200) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _load_remote_url(env_file: Path) -> str:
    url = (dotenv_values(env_file).get("DATABASE_URL") or "").strip()
    if not url:
        raise RuntimeError(f"DATABASE_URL is missing from {env_file}")
    if url.startswith("sqlite"):
        raise RuntimeError("DATABASE_URL must identify the remote PostgreSQL database")
    return url


def _fetch_remote_rows(
    remote_engine: Engine,
    document_short_names: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    with remote_engine.connect() as remote:
        if remote_engine.dialect.name != "postgresql":
            raise RuntimeError("Remote source must be PostgreSQL; refusing fallback database")
        remote.execute(text("SET TRANSACTION READ ONLY"))

        source_rows = [
            dict(row)
            for row in remote.execute(
                select(Source.__table__).where(Source.short_name.in_(document_short_names))
            ).mappings()
        ]
        found = {row["short_name"] for row in source_rows}
        missing = sorted(set(document_short_names) - found)
        if missing:
            raise RuntimeError(f"Remote source records not found: {', '.join(missing)}")

        source_ids = [row["id"] for row in source_rows]
        document_rows = [
            dict(row)
            for row in remote.execute(
                select(SourceDocument.__table__).where(
                    SourceDocument.source_id.in_(source_ids)
                )
            ).mappings()
        ]
        if len(document_rows) != len(document_short_names):
            raise RuntimeError(
                "Expected one source document per requested book; "
                f"found {len(document_rows)} for {len(document_short_names)} books"
            )

        document_ids = [row["id"] for row in document_rows]
        chunk_rows = [
            dict(row)
            for row in remote.execute(
                select(DocumentChunk.__table__)
                .where(DocumentChunk.document_id.in_(document_ids))
                .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
            ).mappings()
        ]
        remote.rollback()

    if not chunk_rows:
        raise RuntimeError("Remote database contains no reference text chunks")
    if any(not str(row.get("content") or "").strip() for row in chunk_rows):
        raise RuntimeError("Remote database contains an empty reference text chunk")
    if len({row["id"] for row in chunk_rows}) != len(chunk_rows):
        raise RuntimeError("Remote database contains duplicate chunk IDs")
    if len({row["content_hash"] for row in chunk_rows}) != len(chunk_rows):
        raise RuntimeError("Remote database contains duplicate chunk content hashes")

    # Remote file-system paths do not identify files on the local machine.
    for row in document_rows:
        row["file_path"] = None
    # This is a text-only sync. Embeddings will be generated deliberately later.
    for row in chunk_rows:
        row["embedding"] = None
        row["embedding_model"] = None

    return source_rows, document_rows, chunk_rows


def sync_reference_content(
    remote_engine: Engine,
    local_db_path: Path,
    document_short_names: tuple[str, ...] = DEFAULT_DOCUMENTS,
    replace: bool = False,
) -> dict[str, Any]:
    """Create a verified local SQLite copy and atomically install it."""
    local_db_path = local_db_path.resolve()
    local_db_path.parent.mkdir(parents=True, exist_ok=True)
    if local_db_path.exists() and not replace:
        raise FileExistsError(
            f"Local database already exists at {local_db_path}; pass --replace to back it up and replace it"
        )

    sources, documents, chunks = _fetch_remote_rows(
        remote_engine, document_short_names
    )

    temp_path = local_db_path.with_suffix(local_db_path.suffix + ".syncing")
    if temp_path.exists():
        temp_path.unlink()
    local_engine = create_engine(
        f"sqlite:///{temp_path}", connect_args={"check_same_thread": False}
    )

    try:
        Base.metadata.create_all(bind=local_engine)
        with local_engine.begin() as local:
            local.execute(Source.__table__.insert(), sources)
            local.execute(SourceDocument.__table__.insert(), documents)
            for batch in _batched(chunks):
                local.execute(DocumentChunk.__table__.insert(), batch)
            # SQLAlchemy JSON serializes Python None as JSON ``null`` by default.
            # Use SQL NULL so the application's ``embedding IS NULL`` queue finds
            # every newly synced text chunk on SQLite.
            local.execute(
                text(
                    "UPDATE document_chunks "
                    "SET embedding = NULL, embedding_model = NULL"
                )
            )

        with local_engine.connect() as local:
            local_counts = {
                "sources": local.execute(
                    select(func.count()).select_from(Source)
                ).scalar_one(),
                "source_documents": local.execute(
                    select(func.count()).select_from(SourceDocument)
                ).scalar_one(),
                "document_chunks": local.execute(
                    select(func.count()).select_from(DocumentChunk)
                ).scalar_one(),
                "embedded_chunks": local.execute(
                    select(func.count())
                    .select_from(DocumentChunk)
                    .where(DocumentChunk.embedding.is_not(None))
                ).scalar_one(),
            }
            local_hashes = set(
                local.execute(select(DocumentChunk.content_hash)).scalars()
            )

        expected_counts = {
            "sources": len(sources),
            "source_documents": len(documents),
            "document_chunks": len(chunks),
            "embedded_chunks": 0,
        }
        if local_counts != expected_counts:
            raise RuntimeError(
                f"Local verification failed: expected {expected_counts}, found {local_counts}"
            )
        if local_hashes != {row["content_hash"] for row in chunks}:
            raise RuntimeError("Local chunk hashes do not match the remote source")
    except Exception:
        local_engine.dispose()
        if temp_path.exists():
            temp_path.unlink()
        raise
    else:
        local_engine.dispose()

    backup_path = None
    if local_db_path.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = local_db_path.with_suffix(local_db_path.suffix + f".{stamp}.bak")
        shutil.copy2(local_db_path, backup_path)
    os.replace(temp_path, local_db_path)

    return {
        **expected_counts,
        "documents": list(document_short_names),
        "local_db": str(local_db_path),
        "backup": str(backup_path) if backup_path else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync remote PostgreSQL reference text to a local SQLite database"
    )
    parser.add_argument("--env-file", type=Path, default=PROJECT_ROOT / ".env")
    parser.add_argument("--local-db", type=Path, default=DEFAULT_LOCAL_DB)
    parser.add_argument(
        "--doc",
        action="append",
        dest="documents",
        help="Source short name to sync; repeat for multiple books",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Back up and replace an existing local database",
    )
    args = parser.parse_args()

    remote_url = _load_remote_url(args.env_file)
    remote_engine = create_engine(remote_url, pool_pre_ping=True)
    try:
        result = sync_reference_content(
            remote_engine=remote_engine,
            local_db_path=args.local_db,
            document_short_names=tuple(args.documents or DEFAULT_DOCUMENTS),
            replace=args.replace,
        )
    finally:
        remote_engine.dispose()

    print("Reference text sync completed")
    print(f"  Documents: {', '.join(result['documents'])}")
    print(f"  Sources: {result['sources']}")
    print(f"  Source documents: {result['source_documents']}")
    print(f"  Text chunks: {result['document_chunks']}")
    print(f"  Embeddings copied: {result['embedded_chunks']}")
    print(f"  Local database: {result['local_db']}")
    if result["backup"]:
        print(f"  Previous local backup: {result['backup']}")


if __name__ == "__main__":
    main()
