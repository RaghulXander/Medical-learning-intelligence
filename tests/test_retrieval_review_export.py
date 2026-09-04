from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.services.retrieval_evaluation import load_evaluation_set
from backend.services.retrieval_review_service import RetrievalReviewService
from database.models import (
    Base,
    DocumentChunk,
    RetrievalBenchmark,
    RetrievalBenchmarkCase,
    Source,
    SourceDocument,
    User,
    UserRole,
)


@pytest.fixture()
def reviewed_database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    reviewer = User(email="gold@example.com", name="Gold Reviewer", role=UserRole.REVIEWER)
    source = Source(short_name="robbins_review", title="Robbins Review")
    document = SourceDocument(source=source, title="Review document", edition="11")
    chunk = DocumentChunk(
        document=document,
        chunk_index=0,
        pdf_page=10,
        textbook_page=5,
        content="Verified pathology evidence.",
        content_hash="a" * 64,
        word_count=3,
    )
    benchmark = RetrievalBenchmark(
        slug="verified-benchmark",
        title="Verified benchmark",
        version=1,
        status="HUMAN_VERIFIED",
        source_file="review-db",
        source_hash="b" * 64,
    )
    session.add_all([reviewer, chunk, benchmark])
    session.flush()
    domains = ["general", "neoplasia", "hematology", "systemic", "diagnostic"]
    for index in range(50):
        out_of_corpus = index == 49
        session.add(
            RetrievalBenchmarkCase(
                benchmark_id=benchmark.id,
                case_key=f"case-{index + 1:03d}",
                domain="out_of_corpus" if out_of_corpus else domains[index % 5],
                query=f"Reviewed retrieval prompt {index + 1}",
                expected_chunk_ids=[] if out_of_corpus else [chunk.id],
                out_of_corpus=out_of_corpus,
                verification_status="HUMAN_VERIFIED",
                reviewer_id=reviewer.id,
                reviewed_at=datetime.now(timezone.utc),
                review_notes="Evidence checked manually",
                revision=2,
            )
        )
    session.commit()
    yield session, benchmark, chunk
    session.close()
    Base.metadata.drop_all(engine)


def test_verified_review_queue_exports_deterministically(reviewed_database, tmp_path):
    session, benchmark, chunk = reviewed_database

    first, summary = RetrievalReviewService.export_verified_dataset(
        session, benchmark.slug
    )
    second, repeated_summary = RetrievalReviewService.export_verified_dataset(
        session, benchmark.slug
    )
    output = tmp_path / "verified.jsonl"
    output.write_bytes(first)
    cases, dataset_hash = load_evaluation_set(output)

    assert first == second
    assert summary == repeated_summary
    assert summary["case_count"] == 50
    assert summary["in_corpus_domain_count"] == 5
    assert summary["out_of_corpus_count"] == 1
    assert summary["referenced_chunk_count"] == 1
    assert summary["dataset_hash"] == dataset_hash
    assert len(cases) == 50
    assert cases[0].expected_chunk_ids == [chunk.id]


def test_export_refuses_incomplete_human_review(reviewed_database):
    session, benchmark, _ = reviewed_database
    case = session.query(RetrievalBenchmarkCase).filter_by(case_key="case-001").one()
    case.verification_status = "HUMAN_REVIEW"
    benchmark.status = "HUMAN_REVIEW"
    session.commit()

    with pytest.raises(ValueError, match="Benchmark is not HUMAN_VERIFIED"):
        RetrievalReviewService.export_verified_dataset(session, benchmark.slug)


def test_export_refuses_missing_reviewer_metadata(reviewed_database):
    session, benchmark, _ = reviewed_database
    case = session.query(RetrievalBenchmarkCase).filter_by(case_key="case-001").one()
    case.review_notes = None
    session.commit()

    with pytest.raises(ValueError, match="lacks human review metadata"):
        RetrievalReviewService.export_verified_dataset(session, benchmark.slug)
