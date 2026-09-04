"""Run-scoped PostgreSQL hybrid retrieval with immutable evidence receipts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import func, literal_column
from sqlalchemy.orm import Session, joinedload

from backend.services.embedding_service import EmbeddingProvider, get_embedding_provider
from database.models import (
    DocumentChunk,
    DocumentChunkEmbedding,
    EmbeddingRun,
    EmbeddingRunStatus,
    Source,
    SourceDocument,
)


class RetrievalUnavailableError(RuntimeError):
    """Raised when measured hybrid retrieval cannot run safely."""


@dataclass(frozen=True)
class HybridRetrievalConfig:
    candidate_pool: int = 50
    rrf_k: int = 60
    dense_weight: float = 0.65
    lexical_weight: float = 0.35
    max_per_page: int = 2
    minimum_fused_score: float = 0.01
    minimum_dense_score: float = 0.65
    minimum_lexical_score: float = 0.01

    @property
    def configuration_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class HybridEvidenceReceipt:
    rank: int
    chunk_id: str
    content_hash: str
    source_id: str
    source_short_name: str
    source_title: str
    edition: Optional[str]
    pdf_page: Optional[int]
    textbook_page: Optional[int]
    chapter_name: Optional[str]
    section_heading: Optional[str]
    dense_score: Optional[float]
    lexical_score: Optional[float]
    fused_score: float
    embedding_run_id: str
    retrieval_configuration_hash: str
    content: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HybridRetrievalOutcome:
    status: str
    query: str
    embedding_run_id: str
    retrieval_configuration_hash: str
    results: List[HybridEvidenceReceipt]


class HybridRetrievalService:
    """Combines pgvector cosine and PostgreSQL full-text ranks using weighted RRF."""

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        config: Optional[HybridRetrievalConfig] = None,
    ) -> None:
        self.embedding_provider = embedding_provider or get_embedding_provider(
            task_type="RETRIEVAL_QUERY"
        )
        self.config = config or HybridRetrievalConfig()

    def _resolve_run(self, db: Session, run_id: Optional[str]) -> EmbeddingRun:
        query = db.query(EmbeddingRun).filter(
            EmbeddingRun.status == EmbeddingRunStatus.COMPLETED,
            EmbeddingRun.dimension == self.embedding_provider.dimension,
        )
        if run_id:
            query = query.filter(EmbeddingRun.id == run_id)
        run = query.order_by(EmbeddingRun.completed_at.desc(), EmbeddingRun.created_at.desc()).first()
        if not run:
            raise RetrievalUnavailableError(
                "No completed embedding run matches the requested run and query-vector dimension"
            )
        if run.query_task_type != "RETRIEVAL_QUERY":
            raise RetrievalUnavailableError("Embedding run has an incompatible query task type")
        return run

    @staticmethod
    def _apply_filters(query, *, source_short_name, edition, chapter, page_range):
        if source_short_name:
            query = query.filter(Source.short_name == source_short_name)
        if edition:
            query = query.filter(Source.edition == edition)
        if chapter:
            query = query.filter(DocumentChunk.chapter_name.ilike(f"%{chapter}%"))
        if page_range:
            query = query.filter(
                DocumentChunk.pdf_page >= page_range[0],
                DocumentChunk.pdf_page <= page_range[1],
            )
        return query

    def _dense_candidates(
        self,
        db: Session,
        *,
        run: EmbeddingRun,
        query_vector: List[float],
        source_short_name: Optional[str],
        edition: Optional[str],
        chapter: Optional[str],
        page_range: Optional[Tuple[int, int]],
    ) -> List[Tuple[str, float]]:
        distance = DocumentChunkEmbedding.embedding.cosine_distance(query_vector)
        query = (
            db.query(DocumentChunk.id, (1.0 - distance).label("score"))
            .join(DocumentChunkEmbedding, DocumentChunkEmbedding.chunk_id == DocumentChunk.id)
            .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
            .join(Source, SourceDocument.source_id == Source.id)
            .filter(
                DocumentChunkEmbedding.run_id == run.id,
                DocumentChunkEmbedding.content_hash == DocumentChunk.content_hash,
            )
        )
        query = self._apply_filters(
            query,
            source_short_name=source_short_name,
            edition=edition,
            chapter=chapter,
            page_range=page_range,
        )
        rows = query.order_by(distance.asc()).limit(self.config.candidate_pool).all()
        return [(str(row[0]), float(row[1])) for row in rows]

    def _lexical_candidates(
        self,
        db: Session,
        *,
        run: EmbeddingRun,
        query_text: str,
        source_short_name: Optional[str],
        edition: Optional[str],
        chapter: Optional[str],
        page_range: Optional[Tuple[int, int]],
    ) -> List[Tuple[str, float]]:
        english = literal_column("'english'")
        document_vector = func.to_tsvector(english, DocumentChunk.content)
        query_vector = func.websearch_to_tsquery(english, query_text)
        rank = func.ts_rank_cd(document_vector, query_vector)
        query = (
            db.query(DocumentChunk.id, rank.label("score"))
            .join(DocumentChunkEmbedding, DocumentChunkEmbedding.chunk_id == DocumentChunk.id)
            .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
            .join(Source, SourceDocument.source_id == Source.id)
            .filter(
                DocumentChunkEmbedding.run_id == run.id,
                DocumentChunkEmbedding.content_hash == DocumentChunk.content_hash,
                document_vector.op("@@")(query_vector),
            )
        )
        query = self._apply_filters(
            query,
            source_short_name=source_short_name,
            edition=edition,
            chapter=chapter,
            page_range=page_range,
        )
        rows = query.order_by(rank.desc()).limit(self.config.candidate_pool).all()
        return [(str(row[0]), float(row[1])) for row in rows]

    def _fuse(
        self,
        dense: Sequence[Tuple[str, float]],
        lexical: Sequence[Tuple[str, float]],
    ) -> List[Tuple[str, float, Optional[float], Optional[float]]]:
        dense_scores = dict(dense)
        lexical_scores = dict(lexical)
        fused: Dict[str, float] = {}
        maximum = 1.0 / (self.config.rrf_k + 1)
        for rank, (chunk_id, _score) in enumerate(dense, start=1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + (
                self.config.dense_weight / (self.config.rrf_k + rank)
            )
        for rank, (chunk_id, _score) in enumerate(lexical, start=1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + (
                self.config.lexical_weight / (self.config.rrf_k + rank)
            )
        return sorted(
            (
                (chunk_id, score / maximum, dense_scores.get(chunk_id), lexical_scores.get(chunk_id))
                for chunk_id, score in fused.items()
            ),
            key=lambda item: (-item[1], item[0]),
        )

    def search(
        self,
        db: Session,
        query: str,
        *,
        top_k: int = 5,
        embedding_run_id: Optional[str] = None,
        source_short_name: Optional[str] = None,
        edition: Optional[str] = None,
        chapter: Optional[str] = None,
        page_range: Optional[Tuple[int, int]] = None,
    ) -> HybridRetrievalOutcome:
        query_text = query.strip()
        if not query_text:
            raise ValueError("Retrieval query must not be empty")
        if db.bind is None or db.bind.dialect.name != "postgresql":
            raise RetrievalUnavailableError("Measured hybrid retrieval requires PostgreSQL with pgvector")

        run = self._resolve_run(db, embedding_run_id)
        query_vector = self.embedding_provider.embed_text(query_text)
        dense = self._dense_candidates(
            db,
            run=run,
            query_vector=query_vector,
            source_short_name=source_short_name,
            edition=edition,
            chapter=chapter,
            page_range=page_range,
        )
        lexical = self._lexical_candidates(
            db,
            run=run,
            query_text=query_text,
            source_short_name=source_short_name,
            edition=edition,
            chapter=chapter,
            page_range=page_range,
        )
        fused = self._fuse(dense, lexical)
        candidate_ids = [item[0] for item in fused]
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.id.in_(candidate_ids))
            .options(joinedload(DocumentChunk.document).joinedload(SourceDocument.source))
            .all()
            if candidate_ids
            else []
        )
        by_id = {chunk.id: chunk for chunk in chunks}

        results: List[HybridEvidenceReceipt] = []
        page_counts: Dict[Tuple[str, Optional[int]], int] = {}
        for chunk_id, fused_score, dense_score, lexical_score in fused:
            if fused_score < self.config.minimum_fused_score:
                continue
            dense_supported = (
                dense_score is not None and dense_score >= self.config.minimum_dense_score
            )
            lexical_supported = (
                lexical_score is not None and lexical_score >= self.config.minimum_lexical_score
            )
            if not dense_supported and not lexical_supported:
                continue
            chunk = by_id.get(chunk_id)
            if not chunk or not chunk.document or not chunk.document.source:
                continue
            page_key = (chunk.document_id, chunk.pdf_page)
            if page_counts.get(page_key, 0) >= self.config.max_per_page:
                continue
            page_counts[page_key] = page_counts.get(page_key, 0) + 1
            source = chunk.document.source
            results.append(
                HybridEvidenceReceipt(
                    rank=len(results) + 1,
                    chunk_id=chunk.id,
                    content_hash=chunk.content_hash,
                    source_id=source.id,
                    source_short_name=source.short_name,
                    source_title=source.title,
                    edition=source.edition,
                    pdf_page=chunk.pdf_page,
                    textbook_page=chunk.textbook_page,
                    chapter_name=chunk.chapter_name,
                    section_heading=chunk.section_heading,
                    dense_score=round(dense_score, 6) if dense_score is not None else None,
                    lexical_score=round(lexical_score, 6) if lexical_score is not None else None,
                    fused_score=round(fused_score, 6),
                    embedding_run_id=run.id,
                    retrieval_configuration_hash=self.config.configuration_hash,
                    content=chunk.content,
                )
            )
            if len(results) >= top_k:
                break

        return HybridRetrievalOutcome(
            status="OK" if results else "INSUFFICIENT_EVIDENCE",
            query=query_text,
            embedding_run_id=run.id,
            retrieval_configuration_hash=self.config.configuration_hash,
            results=results,
        )
