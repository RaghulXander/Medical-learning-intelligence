import json
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import (
    Base,
    DocumentChunk,
    RetrievalBenchmark,
    RetrievalBenchmarkCase,
    Source,
    SourceDocument,
)
from scripts.import_retrieval_review_dataset import import_review_dataset


class TestImportRetrievalReviewDataset(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "benchmark.jsonl"
        records = [
            {
                "id": "case-1",
                "domain": "breast",
                "query": "Which passage supports HER2 testing?",
                "expected_chunk_ids": ["11111111-1111-1111-1111-111111111111"],
                "out_of_corpus": False,
            },
            {
                "id": "case-2",
                "domain": "negative-control",
                "query": "Unsupported subject outside the three books",
                "expected_chunk_ids": [],
                "out_of_corpus": True,
            },
        ]
        self.path.write_text(
            "".join(json.dumps(record) + "\n" for record in records),
            encoding="utf-8",
        )
        source = Source(short_name="test-source", title="Test Source")
        document = SourceDocument(source=source, title="Test document")
        self.db.add(
            DocumentChunk(
                id="11111111-1111-1111-1111-111111111111",
                document=document,
                chunk_index=0,
                content="Test benchmark evidence",
                content_hash="a" * 64,
                word_count=3,
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.temp_dir.cleanup()

    def test_dry_run_does_not_write(self):
        result = import_review_dataset(self.db, path=self.path)
        self.assertEqual(result["status"], "DRY_RUN_VALID")
        self.assertEqual(result["case_count"], 2)
        self.assertEqual(self.db.query(RetrievalBenchmark).count(), 0)

    def test_execute_is_idempotent_and_never_auto_verifies(self):
        first = import_review_dataset(self.db, path=self.path, execute=True)
        second = import_review_dataset(self.db, path=self.path, execute=True)
        self.assertEqual(first["status"], "IMPORTED")
        self.assertEqual(second["status"], "ALREADY_IMPORTED")
        cases = self.db.query(RetrievalBenchmarkCase).all()
        self.assertEqual(len(cases), 2)
        self.assertEqual(
            {case.verification_status for case in cases},
            {"AUTO_BOOTSTRAP_UNVERIFIED"},
        )

    def test_missing_target_chunk_is_rejected_before_import(self):
        self.db.query(DocumentChunk).delete()
        self.db.commit()

        with self.assertRaisesRegex(RuntimeError, "absent from the target database"):
            import_review_dataset(self.db, path=self.path, execute=True)

    def test_changed_bootstrap_can_replace_only_before_review_begins(self):
        import_review_dataset(self.db, path=self.path, execute=True)
        records = [json.loads(line) for line in self.path.read_text().splitlines()]
        records[0]["query"] = "Which exact passage supports HER2 testing?"
        self.path.write_text(
            "".join(json.dumps(record) + "\n" for record in records),
            encoding="utf-8",
        )

        dry_run = import_review_dataset(
            self.db, path=self.path, replace_unreviewed=True
        )
        executed = import_review_dataset(
            self.db, path=self.path, execute=True, replace_unreviewed=True
        )

        self.assertEqual(dry_run["status"], "DRY_RUN_REPLACE_VALID")
        self.assertEqual(executed["status"], "REPLACED_UNREVIEWED")
        stored = self.db.query(RetrievalBenchmarkCase).filter_by(case_key="case-1").one()
        self.assertEqual(stored.query, records[0]["query"])

    def test_changed_bootstrap_cannot_replace_reviewed_case(self):
        import_review_dataset(self.db, path=self.path, execute=True)
        reviewed = self.db.query(RetrievalBenchmarkCase).filter_by(case_key="case-1").one()
        reviewed.verification_status = "HUMAN_REVIEW"
        self.db.commit()
        records = [json.loads(line) for line in self.path.read_text().splitlines()]
        records[0]["query"] = "Which exact passage supports HER2 testing?"
        self.path.write_text(
            "".join(json.dumps(record) + "\n" for record in records),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(RuntimeError, "after human review began"):
            import_review_dataset(
                self.db,
                path=self.path,
                execute=True,
                replace_unreviewed=True,
            )


if __name__ == "__main__":
    unittest.main()
