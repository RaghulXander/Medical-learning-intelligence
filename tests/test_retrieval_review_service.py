import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.services.retrieval_review_service import (
    ReviewConflictError,
    RetrievalReviewService,
)
from database.models import (
    Base,
    DocumentChunk,
    RetrievalBenchmark,
    RetrievalBenchmarkCase,
    RetrievalBenchmarkReview,
    Source,
    SourceDocument,
    User,
    UserRole,
)


class TestRetrievalReviewService(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.reviewer = User(
            email="retrieval-reviewer@example.com",
            name="Retrieval Reviewer",
            role=UserRole.REVIEWER,
        )
        source = Source(short_name="robbins_review", title="Robbins Review")
        document = SourceDocument(source=source, title="Robbins Review document", edition="11")
        self.chunk = DocumentChunk(
            document=document,
            chunk_index=1,
            pdf_page=12,
            textbook_page=4,
            content="RB protein restrains the G1 to S cell-cycle transition.",
            content_hash="a" * 64,
            word_count=9,
        )
        self.benchmark = RetrievalBenchmark(
            slug="m16a-retrieval-v1",
            title="Retrieval review",
            version=1,
            status="HUMAN_REVIEW",
            source_file="test.jsonl",
            source_hash="b" * 64,
        )
        self.case = RetrievalBenchmarkCase(
            benchmark=self.benchmark,
            case_key="RB-001",
            domain="cell-cycle",
            query="What does RB protein restrain?",
            expected_chunk_ids=[],
            out_of_corpus=True,
            verification_status="AUTO_BOOTSTRAP_UNVERIFIED",
            revision=1,
        )
        self.db.add_all([self.reviewer, self.chunk, self.case])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_save_and_approve_are_revisioned_and_audited(self):
        saved = RetrievalReviewService.update_case(
            self.db,
            self.benchmark.slug,
            self.case.id,
            reviewer_id=self.reviewer.id,
            expected_revision=1,
            domain="cell-cycle",
            query="What does RB protein restrain?",
            expected_chunk_ids=[self.chunk.id],
            out_of_corpus=False,
            notes="Evidence inspected",
        )
        self.assertEqual(saved["verification_status"], "HUMAN_REVIEW")
        self.assertEqual(saved["revision"], 2)
        self.assertEqual(saved["evidence"][0]["content"], self.chunk.content)

        approved = RetrievalReviewService.decide_case(
            self.db,
            self.benchmark.slug,
            self.case.id,
            reviewer_id=self.reviewer.id,
            expected_revision=2,
            approve=True,
            notes="Exact passage supports the label",
        )
        self.assertEqual(approved["verification_status"], "HUMAN_VERIFIED")
        self.assertEqual(approved["revision"], 3)
        self.assertEqual(approved["reviewer_id"], self.reviewer.id)
        actions = [row.action for row in self.db.query(RetrievalBenchmarkReview).all()]
        self.assertEqual(actions, ["SAVE_DRAFT", "APPROVE"])

    def test_stale_revision_is_rejected(self):
        with self.assertRaises(ReviewConflictError):
            RetrievalReviewService.decide_case(
                self.db,
                self.benchmark.slug,
                self.case.id,
                reviewer_id=self.reviewer.id,
                expected_revision=99,
                approve=False,
                notes="This label is wrong",
            )

    def test_out_of_corpus_case_cannot_retain_chunks(self):
        with self.assertRaisesRegex(ValueError, "cannot include expected chunks"):
            RetrievalReviewService.update_case(
                self.db,
                self.benchmark.slug,
                self.case.id,
                reviewer_id=self.reviewer.id,
                expected_revision=1,
                domain="cell-cycle",
                query="What does RB protein restrain?",
                expected_chunk_ids=[self.chunk.id],
                out_of_corpus=True,
                notes="Checking negative control",
            )
        self.db.rollback()

    def test_evidence_search_supports_two_character_terms(self):
        rows = RetrievalReviewService.search_evidence(self.db, query="RB")
        self.assertEqual([row["id"] for row in rows], [self.chunk.id])


if __name__ == "__main__":
    unittest.main()
