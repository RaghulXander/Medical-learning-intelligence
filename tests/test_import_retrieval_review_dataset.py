import json
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, RetrievalBenchmark, RetrievalBenchmarkCase
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


if __name__ == "__main__":
    unittest.main()
