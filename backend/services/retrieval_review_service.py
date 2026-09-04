"""Human review workflow for retrieval benchmark labels and evidence chunks."""

from __future__ import annotations

import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from sqlalchemy import func, or_

from database.models import (
    DocumentChunk,
    RetrievalBenchmark,
    RetrievalBenchmarkCase,
    RetrievalBenchmarkReview,
    Source,
    SourceDocument,
)


ALLOWED_SOURCES = {
    "robbins_review",
    "robbins_pathologic_basis_11th",
    "sternberg_review_2nd",
}
ALLOWED_STATUSES = {
    "AUTO_BOOTSTRAP_UNVERIFIED",
    "HUMAN_REVIEW",
    "HUMAN_VERIFIED",
    "REJECTED",
}


class ReviewConflictError(RuntimeError):
    pass


class RetrievalReviewService:
    @staticmethod
    def _benchmark(db, slug: str) -> RetrievalBenchmark:
        benchmark = db.query(RetrievalBenchmark).filter_by(slug=slug).first()
        if not benchmark:
            raise ValueError(f"Retrieval benchmark not found: {slug}")
        return benchmark

    @staticmethod
    def _case_for_update(db, slug: str, case_id: str) -> RetrievalBenchmarkCase:
        case = (
            db.query(RetrievalBenchmarkCase)
            .join(RetrievalBenchmark)
            .filter(RetrievalBenchmark.slug == slug, RetrievalBenchmarkCase.id == case_id)
            .with_for_update()
            .first()
        )
        if not case:
            raise ValueError(f"Retrieval review case not found: {case_id}")
        return case

    @staticmethod
    def _snapshot(case: RetrievalBenchmarkCase) -> dict[str, Any]:
        return {
            "case_key": case.case_key,
            "domain": case.domain,
            "query": case.query,
            "expected_chunk_ids": list(case.expected_chunk_ids or []),
            "out_of_corpus": case.out_of_corpus,
            "verification_status": case.verification_status,
            "reviewer_id": case.reviewer_id,
            "reviewed_at": case.reviewed_at.isoformat() if case.reviewed_at else None,
            "review_notes": case.review_notes,
            "revision": case.revision,
        }

    @staticmethod
    def _evidence_rows(db, chunk_ids: Sequence[str]) -> list[dict[str, Any]]:
        if not chunk_ids:
            return []
        records = (
            db.query(DocumentChunk, SourceDocument, Source)
            .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
            .join(Source, SourceDocument.source_id == Source.id)
            .filter(DocumentChunk.id.in_(tuple(chunk_ids)))
            .all()
        )
        by_id = {
            chunk.id: RetrievalReviewService._serialize_chunk(chunk, document, source)
            for chunk, document, source in records
        }
        return [by_id[chunk_id] for chunk_id in chunk_ids if chunk_id in by_id]

    @staticmethod
    def _serialize_chunk(chunk, document, source) -> dict[str, Any]:
        return {
            "id": chunk.id,
            "content": chunk.content,
            "content_hash": chunk.content_hash,
            "source_short_name": source.short_name,
            "source_title": source.title,
            "edition": document.edition or source.edition,
            "pdf_page": chunk.pdf_page,
            "textbook_page": chunk.textbook_page,
            "chapter_name": chunk.chapter_name,
            "section_heading": chunk.section_heading,
            "word_count": chunk.word_count,
        }

    @staticmethod
    def summary(db, slug: str) -> dict[str, Any]:
        benchmark = RetrievalReviewService._benchmark(db, slug)
        status_rows = (
            db.query(RetrievalBenchmarkCase.verification_status, func.count())
            .filter_by(benchmark_id=benchmark.id)
            .group_by(RetrievalBenchmarkCase.verification_status)
            .all()
        )
        domain_rows = (
            db.query(RetrievalBenchmarkCase.domain, func.count())
            .filter_by(benchmark_id=benchmark.id)
            .group_by(RetrievalBenchmarkCase.domain)
            .all()
        )
        out_of_corpus = (
            db.query(RetrievalBenchmarkCase)
            .filter_by(benchmark_id=benchmark.id, out_of_corpus=True)
            .count()
        )
        status_counts = {status: count for status, count in status_rows}
        total = sum(status_counts.values())
        verified = status_counts.get("HUMAN_VERIFIED", 0)
        return {
            "id": benchmark.id,
            "slug": benchmark.slug,
            "title": benchmark.title,
            "version": benchmark.version,
            "status": benchmark.status,
            "source_hash": benchmark.source_hash,
            "total_cases": total,
            "verified_cases": verified,
            "progress_percent": round((verified / total * 100) if total else 0, 1),
            "status_counts": status_counts,
            "domain_counts": {domain: count for domain, count in domain_rows},
            "out_of_corpus_cases": out_of_corpus,
        }

    @staticmethod
    def list_cases(
        db,
        slug: str,
        *,
        verification_status: Optional[str] = None,
        domain: Optional[str] = None,
        page: int = 1,
        limit: int = 25,
    ) -> dict[str, Any]:
        benchmark = RetrievalReviewService._benchmark(db, slug)
        query = db.query(RetrievalBenchmarkCase).filter_by(benchmark_id=benchmark.id)
        if verification_status:
            if verification_status not in ALLOWED_STATUSES:
                raise ValueError("Invalid verification status")
            query = query.filter_by(verification_status=verification_status)
        if domain:
            query = query.filter_by(domain=domain)
        total = query.count()
        cases = (
            query.order_by(RetrievalBenchmarkCase.case_key)
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        return {
            "items": [
                {
                    "id": case.id,
                    "case_key": case.case_key,
                    "domain": case.domain,
                    "query": case.query,
                    "expected_chunk_count": len(case.expected_chunk_ids or []),
                    "out_of_corpus": case.out_of_corpus,
                    "verification_status": case.verification_status,
                    "reviewer_id": case.reviewer_id,
                    "reviewed_at": case.reviewed_at,
                    "revision": case.revision,
                }
                for case in cases
            ],
            "total": total,
            "page": page,
            "limit": limit,
        }

    @staticmethod
    def get_case(db, slug: str, case_id: str) -> dict[str, Any]:
        case = (
            db.query(RetrievalBenchmarkCase)
            .join(RetrievalBenchmark)
            .filter(RetrievalBenchmark.slug == slug, RetrievalBenchmarkCase.id == case_id)
            .first()
        )
        if not case:
            raise ValueError(f"Retrieval review case not found: {case_id}")
        history = (
            db.query(RetrievalBenchmarkReview)
            .filter_by(case_id=case.id)
            .order_by(RetrievalBenchmarkReview.created_at.desc())
            .all()
        )
        return {
            **RetrievalReviewService._snapshot(case),
            "id": case.id,
            "evidence": RetrievalReviewService._evidence_rows(
                db, case.expected_chunk_ids or []
            ),
            "history": [
                {
                    "id": review.id,
                    "reviewer_id": review.reviewer_id,
                    "action": review.action,
                    "notes": review.notes,
                    "created_at": review.created_at,
                    "previous_snapshot": review.previous_snapshot,
                    "new_snapshot": review.new_snapshot,
                }
                for review in history
            ],
        }

    @staticmethod
    def search_evidence(
        db,
        *,
        query: str,
        source_short_name: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if len(query.strip()) < 2:
            raise ValueError("Evidence search requires at least two characters")
        records = (
            db.query(DocumentChunk, SourceDocument, Source)
            .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
            .join(Source, SourceDocument.source_id == Source.id)
            .filter(Source.short_name.in_(ALLOWED_SOURCES))
        )
        if source_short_name:
            if source_short_name not in ALLOWED_SOURCES:
                raise ValueError("Source is outside the approved benchmark corpus")
            records = records.filter(Source.short_name == source_short_name)
        normalized_query = query.strip()
        terms = [term for term in normalized_query.split() if len(term) >= 3][:6]
        if not terms:
            terms = [normalized_query]
        records = records.filter(
            or_(*(DocumentChunk.content.ilike(f"%{term}%") for term in terms))
        )
        rows = (
            records.order_by(Source.short_name, DocumentChunk.pdf_page, DocumentChunk.chunk_index)
            .limit(limit)
            .all()
        )
        return [
            RetrievalReviewService._serialize_chunk(chunk, document, source)
            for chunk, document, source in rows
        ]

    @staticmethod
    def _validate_labels(db, case: RetrievalBenchmarkCase) -> None:
        chunk_ids = list(dict.fromkeys(case.expected_chunk_ids or []))
        case.expected_chunk_ids = chunk_ids
        if case.out_of_corpus:
            if chunk_ids:
                raise ValueError("Out-of-corpus cases cannot include expected chunks")
            return
        if not chunk_ids:
            raise ValueError("In-corpus cases require at least one expected chunk")
        found = (
            db.query(DocumentChunk.id)
            .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
            .join(Source, SourceDocument.source_id == Source.id)
            .filter(DocumentChunk.id.in_(chunk_ids), Source.short_name.in_(ALLOWED_SOURCES))
            .all()
        )
        found_ids = {row[0] for row in found}
        missing = [chunk_id for chunk_id in chunk_ids if chunk_id not in found_ids]
        if missing:
            raise ValueError(
                f"Expected evidence contains {len(missing)} missing/out-of-scope chunk IDs"
            )

    @staticmethod
    def _record_review(
        db,
        *,
        case: RetrievalBenchmarkCase,
        reviewer_id: str,
        action: str,
        notes: str,
        previous: dict[str, Any],
    ) -> None:
        db.add(
            RetrievalBenchmarkReview(
                id=str(uuid.uuid4()),
                case_id=case.id,
                reviewer_id=reviewer_id,
                action=action,
                notes=notes,
                previous_snapshot=previous,
                new_snapshot=RetrievalReviewService._snapshot(case),
            )
        )

    @staticmethod
    def _refresh_benchmark_status(db, benchmark_id: str) -> None:
        """Promote a benchmark only when its complete human-review gate passes."""
        cases = (
            db.query(RetrievalBenchmarkCase)
            .filter_by(benchmark_id=benchmark_id)
            .all()
        )
        benchmark = db.query(RetrievalBenchmark).filter_by(id=benchmark_id).one()
        verified = [case for case in cases if case.verification_status == "HUMAN_VERIFIED"]
        domains = {case.domain for case in verified if not case.out_of_corpus}
        has_out_of_corpus = any(case.out_of_corpus for case in verified)
        benchmark.status = (
            "HUMAN_VERIFIED"
            if len(cases) >= 50
            and len(verified) == len(cases)
            and len(domains) >= 5
            and has_out_of_corpus
            else "HUMAN_REVIEW"
        )

    @staticmethod
    def export_verified_dataset(db, slug: str) -> tuple[bytes, dict[str, Any]]:
        """Build a deterministic evaluator dataset from completed human review."""
        benchmark = RetrievalReviewService._benchmark(db, slug)
        cases = (
            db.query(RetrievalBenchmarkCase)
            .filter_by(benchmark_id=benchmark.id)
            .order_by(RetrievalBenchmarkCase.case_key)
            .all()
        )
        if benchmark.status != "HUMAN_VERIFIED":
            raise ValueError("Benchmark is not HUMAN_VERIFIED")
        if len(cases) < 50:
            raise ValueError("Verified benchmark requires at least 50 cases")
        in_corpus_domains = {case.domain for case in cases if not case.out_of_corpus}
        if len(in_corpus_domains) < 5:
            raise ValueError("Verified benchmark requires at least five in-corpus domains")
        if not any(case.out_of_corpus for case in cases):
            raise ValueError("Verified benchmark requires an out-of-corpus control")

        rows = []
        referenced_chunk_ids: set[str] = set()
        for case in cases:
            if case.verification_status != "HUMAN_VERIFIED":
                raise ValueError(f"Case {case.case_key} is not HUMAN_VERIFIED")
            if not case.reviewer_id or not case.reviewed_at or not case.review_notes:
                raise ValueError(f"Case {case.case_key} lacks human review metadata")
            chunk_ids = list(case.expected_chunk_ids or [])
            if len(chunk_ids) != len(set(chunk_ids)):
                raise ValueError(f"Case {case.case_key} contains duplicate chunk IDs")
            RetrievalReviewService._validate_labels(db, case)
            evidence = RetrievalReviewService._evidence_rows(db, chunk_ids)
            if len(evidence) != len(chunk_ids):
                raise ValueError(f"Case {case.case_key} has unresolved evidence")
            referenced_chunk_ids.update(chunk_ids)
            rows.append(
                {
                    "id": case.case_key,
                    "domain": case.domain,
                    "query": case.query,
                    "expected_chunk_ids": chunk_ids,
                    "out_of_corpus": case.out_of_corpus,
                    "reviewer": case.reviewer_id,
                    "reviewed_at": case.reviewed_at.isoformat(),
                    "review_notes": case.review_notes,
                    "verification_status": case.verification_status,
                    "evidence_receipts": [
                        {
                            key: item[key]
                            for key in (
                                "id",
                                "content_hash",
                                "source_short_name",
                                "edition",
                                "pdf_page",
                                "textbook_page",
                                "chapter_name",
                                "section_heading",
                            )
                        }
                        for item in evidence
                    ],
                }
            )

        payload = "".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            for row in rows
        ).encode("utf-8")
        return payload, {
            "slug": benchmark.slug,
            "case_count": len(cases),
            "in_corpus_domain_count": len(in_corpus_domains),
            "out_of_corpus_count": sum(case.out_of_corpus for case in cases),
            "referenced_chunk_count": len(referenced_chunk_ids),
            "dataset_hash": hashlib.sha256(payload).hexdigest(),
        }

    @staticmethod
    def update_case(
        db,
        slug: str,
        case_id: str,
        *,
        reviewer_id: str,
        expected_revision: int,
        domain: str,
        query: str,
        expected_chunk_ids: Sequence[str],
        out_of_corpus: bool,
        notes: str,
    ) -> dict[str, Any]:
        case = RetrievalReviewService._case_for_update(db, slug, case_id)
        if case.revision != expected_revision:
            raise ReviewConflictError("Case was changed by another reviewer; reload it")
        if not domain.strip() or not query.strip():
            raise ValueError("Domain and query are required")
        previous = RetrievalReviewService._snapshot(case)
        case.domain = domain.strip()
        case.query = query.strip()
        case.expected_chunk_ids = list(expected_chunk_ids)
        case.out_of_corpus = out_of_corpus
        case.verification_status = "HUMAN_REVIEW"
        case.reviewer_id = reviewer_id
        case.reviewed_at = None
        case.review_notes = notes.strip() or None
        case.revision += 1
        RetrievalReviewService._validate_labels(db, case)
        RetrievalReviewService._record_review(
            db,
            case=case,
            reviewer_id=reviewer_id,
            action="SAVE_DRAFT",
            notes=notes.strip() or "Draft reviewed and saved",
            previous=previous,
        )
        RetrievalReviewService._refresh_benchmark_status(db, case.benchmark_id)
        db.commit()
        return RetrievalReviewService.get_case(db, slug, case_id)

    @staticmethod
    def decide_case(
        db,
        slug: str,
        case_id: str,
        *,
        reviewer_id: str,
        expected_revision: int,
        approve: bool,
        notes: str,
    ) -> dict[str, Any]:
        if len(notes.strip()) < 3:
            raise ValueError("Review notes are required")
        case = RetrievalReviewService._case_for_update(db, slug, case_id)
        if case.revision != expected_revision:
            raise ReviewConflictError("Case was changed by another reviewer; reload it")
        previous = RetrievalReviewService._snapshot(case)
        if approve:
            RetrievalReviewService._validate_labels(db, case)
            case.verification_status = "HUMAN_VERIFIED"
            action = "APPROVE"
        else:
            case.verification_status = "REJECTED"
            action = "REJECT"
        case.reviewer_id = reviewer_id
        case.reviewed_at = datetime.now(timezone.utc)
        case.review_notes = notes.strip()
        case.revision += 1
        RetrievalReviewService._record_review(
            db,
            case=case,
            reviewer_id=reviewer_id,
            action=action,
            notes=notes.strip(),
            previous=previous,
        )
        RetrievalReviewService._refresh_benchmark_status(db, case.benchmark_id)
        db.commit()
        return RetrievalReviewService.get_case(db, slug, case_id)
