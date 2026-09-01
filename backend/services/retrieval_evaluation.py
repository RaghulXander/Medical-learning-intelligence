"""Versioned retrieval benchmark loading, metrics, and acceptance-gate logic."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from backend.services.hybrid_retrieval_service import HybridRetrievalService
from database.models import DocumentChunk, EmbeddingRun, EmbeddingRunStatus


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    id: str
    domain: str
    query: str
    expected_chunk_ids: List[str]
    out_of_corpus: bool
    reviewer: str


def load_evaluation_set(path: Path) -> tuple[List[RetrievalEvaluationCase], str]:
    raw = path.read_bytes()
    cases: List[RetrievalEvaluationCase] = []
    seen_ids = set()
    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            case = RetrievalEvaluationCase(
                id=str(payload["id"]).strip(),
                domain=str(payload["domain"]).strip(),
                query=str(payload["query"]).strip(),
                expected_chunk_ids=[str(item) for item in payload.get("expected_chunk_ids", [])],
                out_of_corpus=bool(payload.get("out_of_corpus", False)),
                reviewer=str(payload["reviewer"]).strip(),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid evaluation case at line {line_number}") from exc
        if not case.id or not case.domain or not case.query or not case.reviewer:
            raise ValueError(f"Blank required field at line {line_number}")
        if case.id in seen_ids:
            raise ValueError(f"Duplicate evaluation ID: {case.id}")
        if case.out_of_corpus and case.expected_chunk_ids:
            raise ValueError(f"Out-of-corpus case {case.id} must not declare expected chunks")
        if not case.out_of_corpus and not case.expected_chunk_ids:
            raise ValueError(f"In-corpus case {case.id} requires at least one expected chunk")
        seen_ids.add(case.id)
        cases.append(case)
    if not cases:
        raise ValueError("Evaluation dataset is empty")
    return cases, hashlib.sha256(raw).hexdigest()


def validate_gold_chunks(db: Session, cases: List[RetrievalEvaluationCase]) -> None:
    expected = {chunk_id for case in cases for chunk_id in case.expected_chunk_ids}
    existing = {
        row[0]
        for row in db.query(DocumentChunk.id).filter(DocumentChunk.id.in_(expected)).all()
    }
    missing = sorted(expected - existing)
    if missing:
        raise ValueError(f"Evaluation dataset references {len(missing)} missing chunk IDs")


class RetrievalEvaluator:
    def __init__(self, retrieval_service: HybridRetrievalService) -> None:
        self.retrieval_service = retrieval_service

    def evaluate(
        self,
        db: Session,
        *,
        cases: List[RetrievalEvaluationCase],
        dataset_hash: str,
        embedding_run_id: str,
    ) -> Dict[str, Any]:
        validate_gold_chunks(db, cases)
        run = db.get(EmbeddingRun, embedding_run_id)
        if not run or run.status != EmbeddingRunStatus.COMPLETED:
            raise ValueError("Evaluation requires a completed embedding run")
        if run.provider == "mock_test_only" or run.provider.startswith("mock"):
            raise ValueError("Mock embedding runs cannot produce acceptance metrics")
        if run.completed_chunk_count != run.expected_chunk_count or run.failed_chunk_count:
            raise ValueError("Embedding run is incomplete")

        hits = {1: 0, 5: 0, 10: 0}
        reciprocal_rank_total = 0.0
        in_corpus_count = 0
        out_of_corpus_count = 0
        refused_out_of_corpus = 0
        domain_stats: Dict[str, Dict[str, int]] = {}
        citation_mismatches = 0
        failures: List[Dict[str, Any]] = []

        for case in cases:
            outcome = self.retrieval_service.search(
                db,
                case.query,
                top_k=10,
                embedding_run_id=embedding_run_id,
            )
            for receipt in outcome.results:
                chunk = db.get(DocumentChunk, receipt.chunk_id)
                if not chunk or chunk.content_hash != receipt.content_hash:
                    citation_mismatches += 1

            if case.out_of_corpus:
                out_of_corpus_count += 1
                if outcome.status == "INSUFFICIENT_EVIDENCE":
                    refused_out_of_corpus += 1
                else:
                    failures.append({"id": case.id, "domain": case.domain, "failure": "not_refused"})
                continue

            in_corpus_count += 1
            domain = domain_stats.setdefault(case.domain, {"count": 0, "recall_at_5_hits": 0})
            domain["count"] += 1
            returned = [receipt.chunk_id for receipt in outcome.results]
            expected = set(case.expected_chunk_ids)
            first_rank = next((rank for rank, chunk_id in enumerate(returned, 1) if chunk_id in expected), None)
            if first_rank:
                reciprocal_rank_total += 1.0 / first_rank
            for k in hits:
                if expected.intersection(returned[:k]):
                    hits[k] += 1
            if expected.intersection(returned[:5]):
                domain["recall_at_5_hits"] += 1
            else:
                failures.append({"id": case.id, "domain": case.domain, "failure": "recall_at_5"})

        recall = {
            f"recall_at_{k}": (hits[k] / in_corpus_count if in_corpus_count else 0.0)
            for k in (1, 5, 10)
        }
        per_domain = {
            domain: {
                "count": values["count"],
                "recall_at_5": values["recall_at_5_hits"] / values["count"],
            }
            for domain, values in sorted(domain_stats.items())
        }
        refusal_rate = (
            refused_out_of_corpus / out_of_corpus_count if out_of_corpus_count else 0.0
        )
        dataset_shape_valid = len(cases) >= 50 and len(domain_stats) >= 5 and out_of_corpus_count > 0
        gate_passed = (
            dataset_shape_valid
            and recall["recall_at_5"] >= 0.90
            and all(value["recall_at_5"] >= 0.80 for value in per_domain.values())
            and refusal_rate == 1.0
            and citation_mismatches == 0
        )
        return {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dataset_hash": dataset_hash,
            "case_count": len(cases),
            "domain_count": len(domain_stats),
            "in_corpus_count": in_corpus_count,
            "out_of_corpus_count": out_of_corpus_count,
            "embedding_run_id": run.id,
            "embedding_provider": run.provider,
            "embedding_model_id": run.model_id,
            "retrieval_configuration_hash": self.retrieval_service.config.configuration_hash,
            **recall,
            "mrr": reciprocal_rank_total / in_corpus_count if in_corpus_count else 0.0,
            "unsupported_query_refusal_rate": refusal_rate,
            "citation_mismatches": citation_mismatches,
            "per_domain": per_domain,
            "dataset_shape_valid": dataset_shape_valid,
            "gate_passed": gate_passed,
            "failures": failures,
        }
