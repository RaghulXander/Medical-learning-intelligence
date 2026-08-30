"""
backend/api/routes/evidence.py

REST API Endpoints for Authoritative Pathology Evidence Retrieval & Citation Search.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.db import get_engine, session_scope
from database.models import DocumentChunk, Source, SourceDocument
from backend.services.retrieval_service import RetrievalService, EvidenceSearchResult

router = APIRouter(prefix="/api/evidence", tags=["Evidence"])
retrieval_service = RetrievalService()


def get_db():
    from database.db import get_engine, get_session_factory
    engine = get_engine()
    session_factory = get_session_factory(engine)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


class EvidenceSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Medical search query (e.g. 'HER2 testing in breast cancer')")
    top_k: int = Field(default=5, ge=1, le=50, description="Max results to return")
    min_score: float = Field(default=0.2, ge=0.0, le=1.0, description="Minimum cosine similarity threshold")
    doc_filter: Optional[str] = Field(default=None, description="Filter by document short_name (e.g. 'robbins_review')")
    chapter_filter: Optional[str] = Field(default=None, description="Filter by chapter name")
    page_start: Optional[int] = Field(default=None, ge=1)
    page_end: Optional[int] = Field(default=None, ge=1)


class EvidenceSearchResponse(BaseModel):
    query: str
    total_found: int
    results: List[Dict[str, Any]]


class EvidenceStatsResponse(BaseModel):
    total_chunks: int
    total_words: int
    documents: List[Dict[str, Any]]


@router.post("/search", response_model=EvidenceSearchResponse)
def search_pathology_evidence(
    req: EvidenceSearchRequest,
    db: Session = Depends(get_db),
):
    """
    Performs dense vector similarity search across Robbins pathology corpus with hybrid filtering.
    """
    page_range = None
    if req.page_start and req.page_end:
        page_range = (req.page_start, req.page_end)

    results = retrieval_service.search_evidence(
        db=db,
        query=req.query,
        top_k=req.top_k,
        min_score=req.min_score,
        doc_filter=req.doc_filter,
        chapter_filter=req.chapter_filter,
        page_range=page_range,
    )

    return EvidenceSearchResponse(
        query=req.query,
        total_found=len(results),
        results=[r.to_dict() for r in results],
    )


@router.get("/stats", response_model=EvidenceStatsResponse)
def get_evidence_stats(db: Session = Depends(get_db)):
    """Returns total evidence chunks, words, and registered documents in the database."""
    total_chunks = db.query(DocumentChunk).count()
    sources = db.query(Source).all()

    doc_list = []
    total_words = 0

    for s in sources:
        for d in s.documents:
            c_count = len(d.chunks)
            w_count = sum(c.word_count for c in d.chunks)
            total_words += w_count
            doc_list.append({
                "short_name": s.short_name,
                "title": s.title,
                "edition": s.edition,
                "total_chunks": c_count,
                "total_words": w_count,
            })

    return EvidenceStatsResponse(
        total_chunks=total_chunks,
        total_words=total_words,
        documents=doc_list,
    )


@router.get("/{chunk_id}")
def get_evidence_chunk(
    chunk_id: str,
    db: Session = Depends(get_db),
):
    """Retrieves a single evidence chunk with full citation metadata and layout tree."""
    res = retrieval_service.get_chunk_by_id(db=db, chunk_id=chunk_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence chunk '{chunk_id}' not found.",
        )
    return res.to_dict()
