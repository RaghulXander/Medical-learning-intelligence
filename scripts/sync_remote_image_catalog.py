"""Mirror private image-catalog metadata from remote PostgreSQL to local PostgreSQL.

The remote transaction is read-only. The command is a dry run unless
``--execute`` is supplied. It copies metadata and object references only; image
binaries and question candidates are never copied or generated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Sequence

from dotenv import dotenv_values
from sqlalchemy import Engine, create_engine, inspect, select, text, update
from sqlalchemy.engine import make_url

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.models import (
    DocumentChunk,
    ImageAsset,
    ImageOccurrence,
    ImageTextEvidenceLink,
    Source,
    SourceDocument,
)


DEFAULT_SOURCES = (
    "robbins_review",
    "robbins_pathologic_basis_11th",
    "sternberg_review_2nd",
)
CATALOG_TABLES = (
    ImageAsset.__table__,
    ImageOccurrence.__table__,
    ImageTextEvidenceLink.__table__,
)


class CatalogSyncConflict(RuntimeError):
    """Raised when stable remote identities disagree with local records."""


def _load_urls(env_file: Path) -> tuple[str, str]:
    values = dotenv_values(env_file)
    remote_url = (values.get("REMOTE_DATABASE_URL") or "").strip()
    local_url = (values.get("DATABASE_URL") or "").strip()
    if not remote_url or not local_url:
        raise RuntimeError("REMOTE_DATABASE_URL and DATABASE_URL are both required")
    if make_url(remote_url).get_backend_name() != "postgresql":
        raise RuntimeError("REMOTE_DATABASE_URL must identify PostgreSQL")
    if make_url(local_url).get_backend_name() != "postgresql":
        raise RuntimeError("DATABASE_URL must identify local PostgreSQL")
    remote_host = (make_url(remote_url).host or "").lower()
    local_host = (make_url(local_url).host or "").lower()
    if remote_host in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("REMOTE_DATABASE_URL must not identify localhost")
    if local_host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Refusing to write image catalog to a non-local DATABASE_URL")
    return remote_url, local_url


def _assert_tables(engine: Engine) -> None:
    present = set(inspect(engine).get_table_names())
    missing = [table.name for table in CATALOG_TABLES if table.name not in present]
    if missing:
        raise RuntimeError(
            "Image catalog schema is missing: "
            + ", ".join(missing)
            + ". Run `python -m alembic upgrade head` first."
        )


def _stable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _stable(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_stable(item) for item in value]
    return str(value) if value.__class__.__module__ == "uuid" else value


def _manifest_hash(rows_by_table: dict[str, list[dict[str, Any]]]) -> str:
    digest = hashlib.sha256()
    for table_name in sorted(rows_by_table):
        for row in sorted(rows_by_table[table_name], key=lambda item: str(item["id"])):
            payload = json.dumps(_stable(row), sort_keys=True, separators=(",", ":"))
            digest.update(f"{table_name}:{payload}\n".encode("utf-8"))
    return digest.hexdigest()


def _fetch_remote(
    engine: Engine,
    source_names: Sequence[str],
    *,
    require_postgres: bool = True,
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, str | None],
    dict[str, str],
]:
    with engine.connect() as connection:
        if require_postgres and engine.dialect.name != "postgresql":
            raise RuntimeError("Remote image catalog must be PostgreSQL")
        if engine.dialect.name == "postgresql":
            connection.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            )

        documents = connection.execute(
            select(SourceDocument.id, SourceDocument.file_hash)
            .join(Source, SourceDocument.source_id == Source.id)
            .where(Source.short_name.in_(tuple(source_names)))
        ).mappings().all()
        if len(documents) != len(source_names):
            raise RuntimeError(
                f"Expected one document for each of {len(source_names)} sources; "
                f"found {len(documents)}"
            )
        document_hashes = {str(row["id"]): row["file_hash"] for row in documents}
        document_ids = list(document_hashes)

        occurrence_rows = [
            dict(row)
            for row in connection.execute(
                select(ImageOccurrence.__table__)
                .where(ImageOccurrence.source_document_id.in_(document_ids))
                .order_by(ImageOccurrence.id)
            ).mappings()
        ]
        asset_ids = {str(row["image_asset_id"]) for row in occurrence_rows}
        asset_rows = [
            dict(row)
            for row in connection.execute(
                select(ImageAsset.__table__)
                .where(ImageAsset.id.in_(asset_ids))
                .order_by(ImageAsset.id)
            ).mappings()
        ]

        chunk_rows = connection.execute(
            select(DocumentChunk.id, DocumentChunk.content_hash).where(
                DocumentChunk.document_id.in_(document_ids)
            )
        ).mappings().all()
        chunk_hashes = {str(row["id"]): row["content_hash"] for row in chunk_rows}
        link_rows = [
            dict(row)
            for row in connection.execute(
                select(ImageTextEvidenceLink.__table__)
                .where(
                    ImageTextEvidenceLink.image_asset_id.in_(asset_ids),
                    ImageTextEvidenceLink.document_chunk_id.in_(tuple(chunk_hashes)),
                )
                .order_by(ImageTextEvidenceLink.id)
            ).mappings()
        ]
        connection.rollback()

    rows_by_table = {
        ImageAsset.__tablename__: asset_rows,
        ImageOccurrence.__tablename__: occurrence_rows,
        ImageTextEvidenceLink.__tablename__: link_rows,
    }
    if not asset_rows or not occurrence_rows:
        raise RuntimeError("Remote database contains no image catalog for the selected books")
    for table_name, rows in rows_by_table.items():
        ids = [str(row["id"]) for row in rows]
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"Remote {table_name} contains duplicate IDs")
    sha_ids = {row["sha256"]: str(row["id"]) for row in asset_rows}
    if len(sha_ids) != len(asset_rows):
        raise RuntimeError("Remote image_assets contains duplicate SHA-256 values")
    if any(str(row["image_asset_id"]) not in asset_ids for row in occurrence_rows):
        raise RuntimeError("Remote catalog contains an orphan image occurrence")
    if any(
        str(row["image_asset_id"]) not in asset_ids
        or str(row["document_chunk_id"]) not in chunk_hashes
        for row in link_rows
    ):
        raise RuntimeError("Remote catalog contains an orphan image evidence link")
    return rows_by_table, document_hashes, chunk_hashes


def _verify_local_references(
    connection,
    document_hashes: dict[str, str | None],
    chunk_hashes: dict[str, str],
) -> None:
    document_rows = connection.execute(
        select(SourceDocument.id, SourceDocument.file_hash)
    ).mappings().all()
    local_document_hashes = {
        str(row["id"]): row["file_hash"] for row in document_rows
    }
    chunk_rows = connection.execute(
        select(DocumentChunk.id, DocumentChunk.content_hash)
    ).mappings().all()
    local_chunk_hashes = {str(row["id"]): row["content_hash"] for row in chunk_rows}
    for reference_id, expected_hash in document_hashes.items():
        if local_document_hashes.get(reference_id) != expected_hash:
            raise CatalogSyncConflict(
                f"Local source document is missing or hash-conflicted: {reference_id}"
            )
    for reference_id, expected_hash in chunk_hashes.items():
        if local_chunk_hashes.get(reference_id) != expected_hash:
            raise CatalogSyncConflict(
                f"Local text reference is missing or hash-conflicted: {reference_id}"
            )


def _plan_table(connection, table, rows: list[dict[str, Any]]):
    existing = {
        str(row["id"]): dict(row)
        for row in connection.execute(select(table)).mappings().all()
    }
    inserts: list[dict[str, Any]] = []
    updates: list[dict[str, Any]] = []
    for row in rows:
        current = existing.get(str(row["id"]))
        if current is None:
            inserts.append(row)
        elif _stable(current) != _stable(row):
            updates.append(row)
    return inserts, updates


def sync_image_catalog(
    remote_engine: Engine,
    local_engine: Engine,
    *,
    source_names: Sequence[str] = DEFAULT_SOURCES,
    execute: bool = False,
    require_postgres: bool = True,
) -> dict[str, Any]:
    if require_postgres and local_engine.dialect.name != "postgresql":
        raise RuntimeError("Local image catalog target must be PostgreSQL")
    _assert_tables(remote_engine)
    _assert_tables(local_engine)
    remote_rows, document_hashes, chunk_hashes = _fetch_remote(
        remote_engine, source_names, require_postgres=require_postgres
    )

    with local_engine.begin() as local:
        _verify_local_references(local, document_hashes, chunk_hashes)
        plans = {
            table.name: _plan_table(local, table, remote_rows[table.name])
            for table in CATALOG_TABLES
        }
        if execute:
            for table in CATALOG_TABLES:
                inserts, updates = plans[table.name]
                if inserts:
                    local.execute(table.insert(), inserts)
                for row in updates:
                    local.execute(
                        update(table).where(table.c.id == row["id"]).values(**row)
                    )

    if execute:
        with local_engine.connect() as local:
            local_rows = {
                table.name: [
                    dict(row)
                    for row in local.execute(
                        select(table).where(
                            table.c.id.in_([row["id"] for row in remote_rows[table.name]])
                        )
                    ).mappings()
                ]
                for table in CATALOG_TABLES
            }
        if _manifest_hash(local_rows) != _manifest_hash(remote_rows):
            raise RuntimeError("Post-sync local image catalog manifest does not match remote")

    return {
        "status": "SYNCED_AND_VERIFIED" if execute else "DRY_RUN_VALID",
        "manifest_sha256": _manifest_hash(remote_rows),
        "counts": {name: len(rows) for name, rows in remote_rows.items()},
        "inserts": {name: len(plan[0]) for name, plan in plans.items()},
        "updates": {name: len(plan[1]) for name, plan in plans.items()},
    }


def sync_storage_uris(
    remote_engine: Engine,
    local_engine: Engine,
    *,
    source_names: Sequence[str] = DEFAULT_SOURCES,
    execute: bool = False,
    require_postgres: bool = True,
) -> dict[str, Any]:
    """Refresh only mutable object references after the catalog is present."""
    if require_postgres and (
        remote_engine.dialect.name != "postgresql"
        or local_engine.dialect.name != "postgresql"
    ):
        raise RuntimeError("Storage URI refresh requires PostgreSQL")
    _assert_tables(remote_engine)
    _assert_tables(local_engine)

    with remote_engine.connect() as remote:
        if remote_engine.dialect.name == "postgresql":
            remote.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            )
        remote_rows = [
            dict(row)
            for row in remote.execute(
                select(ImageAsset.id, ImageAsset.sha256, ImageAsset.storage_uri)
                .join(ImageOccurrence, ImageOccurrence.image_asset_id == ImageAsset.id)
                .join(
                    SourceDocument,
                    SourceDocument.id == ImageOccurrence.source_document_id,
                )
                .join(Source, Source.id == SourceDocument.source_id)
                .where(Source.short_name.in_(tuple(source_names)))
                .distinct()
                .order_by(ImageAsset.id)
            ).mappings()
        ]
        remote.rollback()

    with local_engine.begin() as local:
        local_rows = {
            str(row["id"]): dict(row)
            for row in local.execute(
                select(ImageAsset.id, ImageAsset.sha256, ImageAsset.storage_uri).where(
                    ImageAsset.id.in_([row["id"] for row in remote_rows])
                )
            ).mappings()
        }
        if len(local_rows) != len(remote_rows):
            raise CatalogSyncConflict(
                "Local image catalog is incomplete; run the full catalog sync first"
            )
        updates = []
        for row in remote_rows:
            current = local_rows[str(row["id"])]
            if current["sha256"] != row["sha256"]:
                raise CatalogSyncConflict(
                    f"Local image SHA-256 conflicts with remote: {row['id']}"
                )
            if current["storage_uri"] != row["storage_uri"]:
                updates.append(row)
        if execute:
            for row in updates:
                local.execute(
                    update(ImageAsset)
                    .where(ImageAsset.id == row["id"])
                    .values(storage_uri=row["storage_uri"])
                )

    manifest_rows = {"image_asset_storage_uris": remote_rows}
    if execute:
        with local_engine.connect() as local:
            verified_rows = [
                dict(row)
                for row in local.execute(
                    select(ImageAsset.id, ImageAsset.sha256, ImageAsset.storage_uri)
                    .where(ImageAsset.id.in_([row["id"] for row in remote_rows]))
                    .order_by(ImageAsset.id)
                ).mappings()
            ]
        if _manifest_hash({"image_asset_storage_uris": verified_rows}) != _manifest_hash(
            manifest_rows
        ):
            raise RuntimeError("Post-sync local storage URI manifest does not match remote")
    return {
        "status": "SYNCED_AND_VERIFIED" if execute else "DRY_RUN_VALID",
        "manifest_sha256": _manifest_hash(manifest_rows),
        "counts": {"image_asset_storage_uris": len(remote_rows)},
        "inserts": {"image_asset_storage_uris": 0},
        "updates": {"image_asset_storage_uris": len(updates)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only remote to local PostgreSQL image catalog sync"
    )
    parser.add_argument("--env-file", type=Path, default=PROJECT_ROOT / ".env")
    parser.add_argument("--source", action="append", dest="sources")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--storage-uri-only",
        action="store_true",
        help="Refresh only image object references after a full catalog sync",
    )
    args = parser.parse_args()

    remote_url, local_url = _load_urls(args.env_file)
    remote_engine = create_engine(remote_url, pool_pre_ping=True)
    local_engine = create_engine(local_url, pool_pre_ping=True)
    try:
        sync_function = sync_storage_uris if args.storage_uri_only else sync_image_catalog
        result = sync_function(
            remote_engine,
            local_engine,
            source_names=tuple(args.sources or DEFAULT_SOURCES),
            execute=args.execute,
        )
    finally:
        remote_engine.dispose()
        local_engine.dispose()

    print(f"status={result['status']}")
    names = (
        ("image_asset_storage_uris",)
        if args.storage_uri_only
        else ("image_assets", "image_occurrences", "image_text_evidence_links")
    )
    for name in names:
        print(
            f"{name}={result['counts'][name]} "
            f"inserts={result['inserts'][name]} updates={result['updates'][name]}"
        )
    print(f"manifest_sha256={result['manifest_sha256']}")


if __name__ == "__main__":
    main()
