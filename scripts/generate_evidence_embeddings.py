"""Create an immutable, reproducible DocumentChunk embedding run.

The command is read-only by default. ``--execute`` is required to call a model
and persist vectors. It never writes the legacy JSON embedding columns.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()

from backend.services.embedding_service import (
    DEFAULT_EMBEDDING_DIM,
    DEFAULT_EMBEDDING_MODEL,
    DeterministicMockEmbeddingProvider,
    GeminiEmbeddingProvider,
)
from database.db import get_default_db_url
from database.models import (
    DocumentChunk,
    DocumentChunkEmbedding,
    EmbeddingRun,
    EmbeddingRunStatus,
    Source,
    SourceDocument,
)


DEFAULT_SOURCES = (
    "robbins_pathologic_basis_11th",
    "robbins_review",
    "sternberg_review_2nd",
)
PROVENANCE_MANIFEST_DIR = Path("data/processed/reference_documents/provenance_manifests")
logger = logging.getLogger(__name__)


def _strict_postgres_engine():
    engine = create_engine(get_default_db_url(), hide_parameters=True)
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Embedding runs require the configured PostgreSQL database")
    with engine.connect():
        pass
    return engine


def _corpus_query(session, source_names: Sequence[str]):
    return (
        session.query(DocumentChunk)
        .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
        .join(Source, SourceDocument.source_id == Source.id)
        .filter(Source.short_name.in_(tuple(source_names)))
        .options(joinedload(DocumentChunk.document).joinedload(SourceDocument.source))
        .order_by(DocumentChunk.id)
    )


def _configuration_hash(chunks, *, provider: str, model_id: str, chunking_version: str) -> str:
    manifest_hash = hashlib.sha256()
    for chunk in chunks:
        manifest_hash.update(f"{chunk.id}:{chunk.content_hash}\n".encode("utf-8"))
    config = {
        "provider": provider,
        "model_id": model_id,
        "dimension": DEFAULT_EMBEDDING_DIM,
        "document_task_type": "RETRIEVAL_DOCUMENT",
        "query_task_type": "RETRIEVAL_QUERY",
        "auto_truncate": False,
        "chunking_version": chunking_version,
        "corpus_manifest_hash": manifest_hash.hexdigest(),
    }
    payload = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _provenance_ready(documents) -> bool:
    for document in documents.values():
        source = document.source
        path = PROVENANCE_MANIFEST_DIR / f"{source.short_name}_provenance_manifest.json"
        if not path.is_file():
            return False
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        checks = (
            manifest.get("short_name") == source.short_name,
            manifest.get("status") == "PASSED",
            manifest.get("is_ready_for_embedding") is True,
            manifest.get("rights_verified") is True,
            manifest.get("missing_pages") == [],
            manifest.get("failed_chunks") == [],
            manifest.get("duplicate_pages") == [],
            manifest.get("processing_modes") == ["LIVE_DOCAI"],
            len(manifest.get("processor_version_ids") or []) == 1,
            bool(document.file_hash),
            manifest.get("sha256") == document.file_hash,
        )
        if not all(checks):
            return False
    return True


def create_embedding_run(
    *,
    execute: bool,
    source_names: Sequence[str],
    batch_size: int,
    chunking_version: str,
    allow_test_mock_run: bool,
) -> str | None:
    engine = _strict_postgres_engine()
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    provider_name = "mock_test_only" if allow_test_mock_run else "google_vertex_ai"
    model_id = (
        "mock-deterministic-embedding-768"
        if allow_test_mock_run
        else DEFAULT_EMBEDDING_MODEL
    )

    with session_factory() as session:
        chunks = _corpus_query(session, source_names).all()
    if not chunks:
        raise RuntimeError("No chunks matched the requested source names")
    if any(not chunk.content.strip() for chunk in chunks):
        raise RuntimeError("The selected corpus contains empty evidence chunks")
    if len({chunk.id for chunk in chunks}) != len(chunks):
        raise RuntimeError("The selected corpus contains duplicate chunk IDs")
    documents = {chunk.document_id: chunk.document for chunk in chunks}
    provenance_ready = _provenance_ready(documents)

    config_hash = _configuration_hash(
        chunks,
        provider=provider_name,
        model_id=model_id,
        chunking_version=chunking_version,
    )
    logger.info(
        "Embedding plan: chunks=%d provider=%s model=%s dimension=%d provenance_ready=%s config=%s",
        len(chunks),
        provider_name,
        model_id,
        DEFAULT_EMBEDDING_DIM,
        provenance_ready,
        config_hash,
    )
    if not execute:
        logger.info("DRY RUN only; use --execute after provenance and cost approval")
        return None
    if not allow_test_mock_run and not provenance_ready:
        raise RuntimeError(
            "Real embeddings are blocked until every selected document has a matching, "
            "fully passed M15 provenance manifest"
        )

    provider = (
        DeterministicMockEmbeddingProvider(DEFAULT_EMBEDDING_DIM)
        if allow_test_mock_run
        else GeminiEmbeddingProvider(
            model_name=model_id,
            dimension=DEFAULT_EMBEDDING_DIM,
            task_type="RETRIEVAL_DOCUMENT",
            vertex_ai=True,
        )
    )
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with session_factory() as session:
        session.add(
            EmbeddingRun(
                id=run_id,
                provider=provider_name,
                model_id=model_id,
                dimension=DEFAULT_EMBEDDING_DIM,
                document_task_type="RETRIEVAL_DOCUMENT",
                query_task_type="RETRIEVAL_QUERY",
                chunking_version=chunking_version,
                status=EmbeddingRunStatus.RUNNING,
                expected_chunk_count=len(chunks),
                config_hash=config_hash,
                started_at=now,
            )
        )
        session.commit()

    completed = 0
    try:
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            vectors = provider.embed_batch([chunk.content for chunk in batch])
            if len(vectors) != len(batch):
                raise RuntimeError("Provider result count did not match the requested batch")
            with session_factory() as session:
                for chunk, vector in zip(batch, vectors):
                    if len(vector) != DEFAULT_EMBEDDING_DIM:
                        raise RuntimeError("Provider returned an invalid vector dimension")
                    session.add(
                        DocumentChunkEmbedding(
                            id=str(uuid.uuid4()),
                            run_id=run_id,
                            chunk_id=chunk.id,
                            content_hash=chunk.content_hash,
                            embedding=vector,
                        )
                    )
                completed += len(batch)
                run = session.get(EmbeddingRun, run_id)
                run.completed_chunk_count = completed
                session.commit()
            logger.info("Embedded %d/%d chunks", completed, len(chunks))
    except Exception as exc:
        with session_factory() as session:
            run = session.get(EmbeddingRun, run_id)
            run.status = EmbeddingRunStatus.FAILED
            run.failed_chunk_count = len(chunks) - completed
            run.error_summary = type(exc).__name__
            run.completed_at = datetime.now(timezone.utc)
            session.commit()
        raise

    with session_factory() as session:
        run = session.get(EmbeddingRun, run_id)
        run.status = EmbeddingRunStatus.COMPLETED
        run.completed_at = datetime.now(timezone.utc)
        session.commit()
    logger.info("Embedding run completed: %s", run_id)
    return run_id


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Call the provider and persist a new run")
    parser.add_argument("--source", action="append", dest="sources", help="Source short name; repeatable")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--chunking-version", default="promoted-page-chunks-v1")
    parser.add_argument(
        "--allow-test-mock-run",
        action="store_true",
        help="Persist an isolated mock_test_only run; never valid for retrieval acceptance",
    )
    args = parser.parse_args()
    if args.batch_size < 1 or args.batch_size > 100:
        parser.error("--batch-size must be between 1 and 100")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    create_embedding_run(
        execute=args.execute,
        source_names=tuple(args.sources or DEFAULT_SOURCES),
        batch_size=args.batch_size,
        chunking_version=args.chunking_version,
        allow_test_mock_run=args.allow_test_mock_run,
    )


if __name__ == "__main__":
    main()
