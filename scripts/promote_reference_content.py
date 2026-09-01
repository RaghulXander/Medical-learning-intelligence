"""Promote the private SQLite reference corpus into configured PostgreSQL.

The operation is additive, idempotent, and transactional. Existing unrelated
application data is preserved, while ID or content-hash conflicts fail closed.
No book text is printed or written to the promotion receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from dotenv import dotenv_values
from sqlalchemy import Engine, create_engine, inspect, or_, select

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.models import DocumentChunk, Source, SourceDocument


DEFAULT_SOURCE_DB = PROJECT_ROOT / "data" / "medical_exam.db"
DEFAULT_RECEIPT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "reference_documents"
    / "promotion_receipts"
)
DEFAULT_DOCUMENTS = (
    "robbins_review",
    "robbins_pathologic_basis_11th",
)
PENDING_PAGE_RECEIPTS = {
    "robbins_pathologic_basis_11th": [4, 6, 16, 1226],
    "robbins_review": [],
}


class PromotionConflictError(RuntimeError):
    """Raised when target rows disagree with stable source identity or hashes."""


def _assert_target_schema(target_engine: Engine) -> None:
    """Fail before reading content when required ingestion columns are absent."""
    inspector = inspect(target_engine)
    required = {
        "slice_id",
        "pdf_page",
        "textbook_page",
        "chapter_name",
        "word_count",
        "embedding",
        "embedding_model",
    }
    present = {column["name"] for column in inspector.get_columns("document_chunks")}
    missing = sorted(required - present)
    if missing:
        raise RuntimeError(
            "Target document_chunks schema is outdated; missing columns: "
            + ", ".join(missing)
            + ". Run the local schema initialization/migration before promotion."
        )


def _batched(rows: list[dict[str, Any]], size: int = 200) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _load_target_url(env_file: Path) -> str:
    url = (dotenv_values(env_file).get("DATABASE_URL") or "").strip()
    if not url:
        raise RuntimeError(f"DATABASE_URL is missing from {env_file}")
    if not url.startswith("postgresql"):
        raise RuntimeError("DATABASE_URL must identify local PostgreSQL")
    return url


def _load_source_rows(
    source_engine: Engine,
    short_names: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    with source_engine.connect() as source:
        source_rows = [
            dict(row)
            for row in source.execute(
                select(Source.__table__).where(Source.short_name.in_(short_names))
            ).mappings()
        ]
        found = {row["short_name"] for row in source_rows}
        missing = sorted(set(short_names) - found)
        if missing:
            raise RuntimeError(f"Source records not found: {', '.join(missing)}")

        source_ids = [row["id"] for row in source_rows]
        document_rows = [
            dict(row)
            for row in source.execute(
                select(SourceDocument.__table__).where(
                    SourceDocument.source_id.in_(source_ids)
                )
            ).mappings()
        ]
        if len(document_rows) != len(short_names):
            raise RuntimeError(
                "Expected exactly one source document per requested book; "
                f"found {len(document_rows)} for {len(short_names)} books"
            )

        document_ids = [row["id"] for row in document_rows]
        chunk_rows = [
            dict(row)
            for row in source.execute(
                select(DocumentChunk.__table__)
                .where(DocumentChunk.document_id.in_(document_ids))
                .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
            ).mappings()
        ]

    if not chunk_rows:
        raise RuntimeError("Source SQLite database contains no requested text chunks")
    if any(not str(row.get("content") or "").strip() for row in chunk_rows):
        raise RuntimeError("Source SQLite database contains an empty text chunk")
    if len({row["id"] for row in chunk_rows}) != len(chunk_rows):
        raise RuntimeError("Source SQLite database contains duplicate chunk IDs")
    if len({row["content_hash"] for row in chunk_rows}) != len(chunk_rows):
        raise RuntimeError("Source SQLite database contains duplicate content hashes")

    for row in document_rows:
        row["file_path"] = None
    for row in chunk_rows:
        # Omit these columns entirely so PostgreSQL stores SQL NULL, never a
        # JSON null that could be mistaken for a completed embedding.
        row.pop("embedding", None)
        row.pop("embedding_model", None)

    return source_rows, document_rows, chunk_rows


def _assert_source_compatible(target: Any, row: dict[str, Any]) -> bool:
    existing = target.execute(
        select(Source.id, Source.short_name, Source.title, Source.edition).where(
            or_(Source.id == row["id"], Source.short_name == row["short_name"])
        )
    ).mappings().all()
    if not existing:
        return False
    if len(existing) != 1:
        raise PromotionConflictError(
            f"Multiple target source identities match {row['short_name']}"
        )
    current = existing[0]
    if (
        str(current["id"]) != str(row["id"])
        or current["short_name"] != row["short_name"]
        or current["title"] != row["title"]
        or current["edition"] != row["edition"]
    ):
        raise PromotionConflictError(
            f"Target source conflicts with stable identity for {row['short_name']}"
        )
    return True


def _assert_document_compatible(target: Any, row: dict[str, Any]) -> bool:
    existing = target.execute(
        select(
            SourceDocument.id,
            SourceDocument.source_id,
            SourceDocument.file_hash,
            SourceDocument.page_start,
            SourceDocument.page_end,
        ).where(
            or_(
                SourceDocument.id == row["id"],
                SourceDocument.source_id == row["source_id"],
            )
        )
    ).mappings().all()
    if not existing:
        return False
    if len(existing) != 1:
        raise PromotionConflictError(
            f"Multiple target documents match source {row['source_id']}"
        )
    current = existing[0]
    if (
        str(current["id"]) != str(row["id"])
        or str(current["source_id"]) != str(row["source_id"])
        or current["file_hash"] != row["file_hash"]
        or current["page_start"] != row["page_start"]
        or current["page_end"] != row["page_end"]
    ):
        raise PromotionConflictError(
            f"Target document conflicts with stable identity {row['id']}"
        )
    return True


def _partition_chunks(
    target: Any,
    chunk_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    ids = [row["id"] for row in chunk_rows]
    hashes = [row["content_hash"] for row in chunk_rows]
    existing = target.execute(
        select(DocumentChunk.id, DocumentChunk.content_hash).where(
            or_(DocumentChunk.id.in_(ids), DocumentChunk.content_hash.in_(hashes))
        )
    ).mappings().all()
    by_id = {str(row["id"]): row["content_hash"] for row in existing}
    by_hash = {row["content_hash"]: str(row["id"]) for row in existing}

    inserts: list[dict[str, Any]] = []
    skipped = 0
    for row in chunk_rows:
        chunk_id = str(row["id"])
        content_hash = row["content_hash"]
        existing_hash = by_id.get(chunk_id)
        existing_id = by_hash.get(content_hash)
        if existing_hash is not None:
            if existing_hash != content_hash:
                raise PromotionConflictError(
                    f"Target chunk ID has a conflicting content hash: {chunk_id}"
                )
            skipped += 1
            continue
        if existing_id is not None and existing_id != chunk_id:
            raise PromotionConflictError(
                f"Target content hash belongs to a different chunk ID: {content_hash}"
            )
        inserts.append(row)
    return inserts, skipped


def promote_reference_content(
    source_engine: Engine,
    target_engine: Engine,
    short_names: tuple[str, ...] = DEFAULT_DOCUMENTS,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Merge the requested corpus into a target database transactionally."""
    _assert_target_schema(target_engine)
    source_rows, document_rows, chunk_rows = _load_source_rows(
        source_engine, short_names
    )
    source_hashes = {row["content_hash"] for row in chunk_rows}
    source_document_by_id = {str(row["id"]): row for row in document_rows}
    source_name_by_id = {str(row["id"]): row["short_name"] for row in source_rows}

    connection = target_engine.connect()
    transaction = connection.begin()
    try:
        new_sources = [
            row for row in source_rows if not _assert_source_compatible(connection, row)
        ]
        new_documents = [
            row
            for row in document_rows
            if not _assert_document_compatible(connection, row)
        ]
        new_chunks, skipped_chunks = _partition_chunks(connection, chunk_rows)

        if not dry_run:
            if new_sources:
                connection.execute(Source.__table__.insert(), new_sources)
            if new_documents:
                connection.execute(SourceDocument.__table__.insert(), new_documents)
            for batch in _batched(new_chunks):
                connection.execute(DocumentChunk.__table__.insert(), batch)

            target_rows = connection.execute(
                select(
                    DocumentChunk.id,
                    DocumentChunk.document_id,
                    DocumentChunk.content_hash,
                ).where(
                    DocumentChunk.document_id.in_(
                        [row["id"] for row in document_rows]
                    )
                )
            ).mappings().all()
            target_hashes = {row["content_hash"] for row in target_rows}
            if len(target_rows) != len(chunk_rows) or target_hashes != source_hashes:
                raise RuntimeError(
                    "PostgreSQL verification failed: promoted counts or hashes differ"
                )
            transaction.commit()
        else:
            transaction.rollback()
    except Exception:
        if transaction.is_active:
            transaction.rollback()
        raise
    finally:
        connection.close()

    per_document: dict[str, dict[str, Any]] = {}
    for document_id, document in source_document_by_id.items():
        short_name = source_name_by_id[str(document["source_id"])]
        rows = [row for row in chunk_rows if str(row["document_id"]) == document_id]
        per_document[short_name] = {
            "source_document_id": document_id,
            "file_hash": document["file_hash"],
            "declared_pdf_pages": document["page_end"],
            "chunk_count": len(rows),
            "distinct_pdf_pages": len(
                {row["pdf_page"] for row in rows if row["pdf_page"] is not None}
            ),
            "word_count": sum(int(row.get("word_count") or 0) for row in rows),
            "pending_page_receipts": PENDING_PAGE_RECEIPTS.get(short_name, []),
            "page_receipt_status": (
                "PENDING_VISUAL_CONFIRMATION"
                if PENDING_PAGE_RECEIPTS.get(short_name)
                else "TEXT_PAGE_COVERAGE_COMPLETE"
            ),
        }

    return {
        "receipt_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "documents": per_document,
        "source_count": len(source_rows),
        "source_document_count": len(document_rows),
        "chunk_count": len(chunk_rows),
        "inserted_sources": len(new_sources),
        "inserted_source_documents": len(new_documents),
        "inserted_chunks": len(new_chunks),
        "skipped_existing_chunks": skipped_chunks,
        "content_hash_manifest": hashlib.sha256(
            "\n".join(sorted(source_hashes)).encode("utf-8")
        ).hexdigest(),
        "status": "DRY_RUN_VALID" if dry_run else "PROMOTED_AND_VERIFIED",
    }


def _save_receipt(receipt: dict[str, Any], receipt_dir: Path) -> Path:
    receipt_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = receipt_dir / f"reference_content_promotion_{stamp}.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Promote private SQLite reference text into local PostgreSQL"
    )
    parser.add_argument("--source-db", type=Path, default=DEFAULT_SOURCE_DB)
    parser.add_argument("--env-file", type=Path, default=PROJECT_ROOT / ".env")
    parser.add_argument("--receipt-dir", type=Path, default=DEFAULT_RECEIPT_DIR)
    parser.add_argument("--doc", action="append", dest="documents")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.source_db.exists():
        raise FileNotFoundError(f"SQLite source database not found: {args.source_db}")
    target_url = _load_target_url(args.env_file)
    source_engine = create_engine(f"sqlite:///{args.source_db.resolve()}")
    target_engine = create_engine(
        target_url,
        pool_pre_ping=True,
        hide_parameters=True,
    )
    if target_engine.dialect.name != "postgresql":
        raise RuntimeError("Target engine is not PostgreSQL")

    try:
        receipt = promote_reference_content(
            source_engine=source_engine,
            target_engine=target_engine,
            short_names=tuple(args.documents or DEFAULT_DOCUMENTS),
            dry_run=args.dry_run,
        )
    finally:
        source_engine.dispose()
        target_engine.dispose()

    receipt_path = _save_receipt(receipt, args.receipt_dir)
    print(f"status={receipt['status']}")
    print(f"sources={receipt['source_count']}")
    print(f"source_documents={receipt['source_document_count']}")
    print(f"chunks={receipt['chunk_count']}")
    print(f"inserted_chunks={receipt['inserted_chunks']}")
    print(f"skipped_existing_chunks={receipt['skipped_existing_chunks']}")
    print(f"receipt={receipt_path}")


if __name__ == "__main__":
    main()
