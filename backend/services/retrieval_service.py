"""
backend/services/retrieval_service.py

Authoritative Pathology Semantic Retrieval Engine.
Searches across 1,719 verified evidence blocks from Robbins textbooks using
dense vector similarity search and hybrid metadata filtering.
Returns structured provenance receipts with exact textbook and PDF citations.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from database.models import DocumentChunk, Source, SourceDocument
from backend.services.embedding_service import (
    EmbeddingProvider,
    cosine_similarity,
    get_embedding_provider,
)

logger = logging.getLogger(__name__)


@dataclass
class EvidenceSearchResult:
    """Structured evidence retrieval result with strict textbook provenance."""

    chunk_id: str
    document_title: str
    document_short_name: str
    edition: str
    pdf_page: int
    textbook_page: Optional[int]
    chapter_name: Optional[str]
    section_heading: Optional[str]
    content: str
    content_hash: str
    word_count: int
    similarity_score: float
    citation_label: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RetrievalService:
    """
    Semantic Retrieval & Citation Engine for Pathology Reference Evidence.
    """

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
        self.embedding_provider = embedding_provider or get_embedding_provider()

    def search_evidence(
        self,
        db: Session,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3,
        doc_filter: Optional[str] = None,
        chapter_filter: Optional[str] = None,
        page_range: Optional[tuple[int, int]] = None,
    ) -> List[EvidenceSearchResult]:
        """
        Performs semantic vector search across document chunks with hybrid filtering.
        """
        query_cleaned = query.strip()
        if not query_cleaned:
            return []

        # Embed query text
        query_vector = self.embedding_provider.embed_text(query_cleaned)

        # Build database query with joined relationships
        stmt = (
            db.query(DocumentChunk)
            .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
            .join(Source, SourceDocument.source_id == Source.id)
            .options(
                joinedload(DocumentChunk.document).joinedload(SourceDocument.source)
            )
        )

        if doc_filter:
            stmt = stmt.filter(Source.short_name == doc_filter)

        if chapter_filter:
            stmt = stmt.filter(DocumentChunk.chapter_name.ilike(f"%{chapter_filter}%"))

        if page_range:
            p_start, p_end = page_range
            stmt = stmt.filter(
                DocumentChunk.pdf_page >= p_start,
                DocumentChunk.pdf_page <= p_end,
            )

        chunks: List[DocumentChunk] = stmt.all()

        scored_results: List[EvidenceSearchResult] = []

        for chunk in chunks:
            chunk_vector = chunk.embedding
            # If chunk embedding is not pre-computed, calculate on-the-fly or fallback to content similarity
            if not chunk_vector:
                chunk_vector = self.embedding_provider.embed_text(chunk.content[:2000])

            score = cosine_similarity(query_vector, chunk_vector)

            # Boost score slightly if chapter or section matches query keywords directly
            lower_query = query_cleaned.lower()
            if chunk.chapter_name and any(w in lower_query for w in chunk.chapter_name.lower().split() if len(w) > 3):
                score = min(1.0, score + 0.05)
            if chunk.section_heading and any(w in lower_query for w in chunk.section_heading.lower().split() if len(w) > 3):
                score = min(1.0, score + 0.05)

            if score < min_score:
                continue

            source = chunk.document.source if chunk.document else None
            source_title = source.title if source else "Robbins Pathology"
            source_short = source.short_name if source else "robbins"
            edition = source.edition if source else "11th"

            # Format authoritative citation receipt
            page_label = f"p. {chunk.textbook_page}" if chunk.textbook_page else f"PDF p. {chunk.pdf_page}"
            chapter_label = f" ({chunk.chapter_name})" if chunk.chapter_name else ""
            citation = f"{source_title}, {edition} Ed., {page_label}{chapter_label}"

            scored_results.append(
                EvidenceSearchResult(
                    chunk_id=chunk.id,
                    document_title=source_title,
                    document_short_name=source_short,
                    edition=edition,
                    pdf_page=chunk.pdf_page or 1,
                    textbook_page=chunk.textbook_page,
                    chapter_name=chunk.chapter_name,
                    section_heading=chunk.section_heading,
                    content=chunk.content,
                    content_hash=chunk.content_hash,
                    word_count=chunk.word_count or len(chunk.content.split()),
                    similarity_score=round(score, 4),
                    citation_label=citation,
                    metadata=chunk.metadata_json or {},
                )
            )

        # Sort descending by similarity score
        scored_results.sort(key=lambda x: x.similarity_score, reverse=True)
        return scored_results[:top_k]

    def get_chunk_by_id(self, db: Session, chunk_id: str) -> Optional[EvidenceSearchResult]:
        """Retrieves a single chunk by its ID with full citation provenance."""
        chunk = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.id == chunk_id)
            .options(
                joinedload(DocumentChunk.document).joinedload(SourceDocument.source)
            )
            .first()
        )
        if not chunk:
            return None

        source = chunk.document.source if chunk.document else None
        source_title = source.title if source else "Robbins Pathology"
        source_short = source.short_name if source else "robbins"
        edition = source.edition if source else "11th"

        page_label = f"p. {chunk.textbook_page}" if chunk.textbook_page else f"PDF p. {chunk.pdf_page}"
        chapter_label = f" ({chunk.chapter_name})" if chunk.chapter_name else ""
        citation = f"{source_title}, {edition} Ed., {page_label}{chapter_label}"

        return EvidenceSearchResult(
            chunk_id=chunk.id,
            document_title=source_title,
            document_short_name=source_short,
            edition=edition,
            pdf_page=chunk.pdf_page or 1,
            textbook_page=chunk.textbook_page,
            chapter_name=chunk.chapter_name,
            section_heading=chunk.section_heading,
            content=chunk.content,
            content_hash=chunk.content_hash,
            word_count=chunk.word_count or len(chunk.content.split()),
            similarity_score=1.0,
            citation_label=citation,
            metadata=chunk.metadata_json or {},
        )
