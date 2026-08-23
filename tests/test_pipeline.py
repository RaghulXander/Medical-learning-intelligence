"""
tests/test_pipeline.py

Unit tests for Pathology data pipeline:
- Subject extraction
- Schema normalization
- Topic decoupling and provenance
- Option mapping and COP resolution
- Unicode and medical symbol preservation
- Duplicate clustering without record loss
- JSONL round-trip serialization
"""

import json
import tempfile
import unittest
from pathlib import Path
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pandas as pd
from extract_pathology import extract_pathology_from_df
from normalize_medmcqa import (
    normalize_question_record,
    normalize_topic,
    sanitize_text,
    compute_content_hashes,
)
from deduplicate_questions import analyze_and_annotate_duplicates


class TestPathologyPipeline(unittest.TestCase):

    def test_extract_pathology_filtering(self):
        sample_data = {
            "id": ["1", "2", "3", "4"],
            "question": ["Q1", "Q2", "Q3", "Q4"],
            "subject_name": ["Pathology", "PATHOLOGY ", "Anatomy", "pathology"],
        }
        df = pd.DataFrame(sample_data)
        extracted = extract_pathology_from_df(df, subject="Pathology")
        self.assertEqual(len(extracted), 3)
        self.assertListEqual(list(extracted["id"]), ["1", "2", "4"])

    def test_normalize_question_labeled(self):
        raw_record = {
            "id": "test-uuid-1234",
            "question": "A 45-year-old male with   fever and leukocytosis... \u2193 platelet count",
            "opa": "Leukemoid reaction",
            "opb": "Leukopenia",
            "opc": "Myeloid metaplasia",
            "opd": "Neutrophilia",
            "cop": 0,
            "choice_type": "single",
            "exp": "Ref: Robbins 9th ed.\nExplanation text here.",
            "subject_name": "Pathology",
            "topic_name": "General pathology",
        }
        norm = normalize_question_record(raw_record, split="train")

        self.assertEqual(norm["external_source"], "medmcqa")
        self.assertEqual(norm["external_source_id"], "medmcqa-test-uuid-1234")
        self.assertTrue(len(norm["id"]) > 0)
        self.assertEqual(norm["correct_option"], "A")
        self.assertEqual(norm["correct_index"], 0)
        self.assertTrue(norm["is_labeled"])
        self.assertIn("\u2193 platelet count", norm["stem"])
        self.assertEqual(norm["options"][0], {"key": "A", "text": "Leukemoid reaction"})
        self.assertEqual(norm["options"][1], {"key": "B", "text": "Leukopenia"})
        self.assertEqual(norm["topic_name_original"], "General pathology")
        self.assertEqual(norm["topic_name_normalized"], "General pathology")
        self.assertEqual(norm["topic_mapping_status"], "RAW_ONLY")
        self.assertIsNone(norm["curriculum_topic_id"])
        self.assertEqual(norm["status"], "IMPORTED")
        self.assertTrue(len(norm["content_hash"]) == 64)

    def test_normalize_question_unlabeled_test_split(self):
        raw_record = {
            "id": "blind-test-id",
            "question": "Question without answer?",
            "opa": "Opt 1",
            "opb": "Opt 2",
            "opc": "Opt 3",
            "opd": "Opt 4",
            "cop": -1,
            "choice_type": "single",
            "exp": None,
            "subject_name": "Pathology",
            "topic_name": None,
        }
        norm = normalize_question_record(raw_record, split="test")

        self.assertIsNone(norm["correct_option"])
        self.assertEqual(norm["correct_index"], -1)
        self.assertFalse(norm["is_labeled"])
        self.assertIsNone(norm["explanation"])
        self.assertIsNone(norm["topic_name_original"])
        self.assertIsNone(norm["topic_name_normalized"])
        self.assertEqual(norm["topic_mapping_status"], "UNMAPPED")

    def test_topic_decoupling_states(self):
        # Case 1: Null / None
        self.assertIsNone(normalize_topic(None))
        self.assertIsNone(normalize_topic(""))
        self.assertIsNone(normalize_topic("nan"))
        self.assertIsNone(normalize_topic("null"))

        # Case 2: Clean topic
        self.assertEqual(normalize_topic("  Haematology  "), "Haematology")
        self.assertEqual(normalize_topic("Cardiovascular   system"), "Cardiovascular system")

    def test_sanitize_text_preserves_medical_characters(self):
        raw_text = "Patient has \u00a0 α-thalassemia and \u2193 Hb \n\n   with microcytosis   "
        sanitized = sanitize_text(raw_text)
        self.assertIn("α-thalassemia", sanitized)
        self.assertIn("\u2193 Hb", sanitized)
        self.assertIn("with microcytosis", sanitized)
        self.assertNotIn("\u00a0", sanitized)

    def test_deduplication_preserves_all_records(self):
        rec1 = {
            "id": "id-1",
            "content_hash": "hash_aaa",
            "norm_stem_hash": "stem_aaa",
            "stem": "What is amyloid?",
            "is_labeled": True,
            "metadata": {"split": "train"},
        }
        rec2 = {
            "id": "id-2",
            "content_hash": "hash_aaa",  # duplicate content hash
            "norm_stem_hash": "stem_aaa",
            "stem": "What is amyloid?",
            "is_labeled": True,
            "metadata": {"split": "train"},
        }
        rec3 = {
            "id": "id-3",
            "content_hash": "hash_bbb",
            "norm_stem_hash": "stem_bbb",
            "stem": "What is apoptosis?",
            "is_labeled": True,
            "metadata": {"split": "train"},
        }

        annotated, report = analyze_and_annotate_duplicates([rec1, rec2, rec3])
        # 100% of records preserved
        self.assertEqual(len(annotated), 3)
        self.assertEqual(report["total_records_processed"], 3)
        self.assertEqual(report["duplicate_content_clusters_count"], 1)

        # Verified duplicate signal attached
        self.assertIn("duplicate_signals", annotated[0])
        self.assertIn("duplicate_signals", annotated[1])
        self.assertNotIn("duplicate_signals", annotated[2])
        self.assertEqual(annotated[0]["duplicate_signals"]["content_duplicate_count"], 2)

    def test_jsonl_roundtrip(self):
        raw = {
            "id": "roundtrip-id",
            "question": "Sample Question",
            "opa": "A",
            "opb": "B",
            "opc": "C",
            "opd": "D",
            "cop": 2,
            "choice_type": "single",
            "exp": "Exp",
            "subject_name": "Pathology",
            "topic_name": "Neoplasia",
        }
        norm = normalize_question_record(raw, split="train")

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".jsonl", delete=False, encoding="utf-8") as tmp:
            tmp.write(json.dumps(norm, ensure_ascii=False) + "\n")
            tmp_path = Path(tmp.name)

        with open(tmp_path, "r", encoding="utf-8") as f:
            line = f.readline()
            loaded = json.loads(line)

        self.assertEqual(loaded["id"], norm["id"])
        self.assertEqual(loaded["stem"], norm["stem"])
        self.assertEqual(loaded["correct_option"], "C")
        self.assertEqual(loaded["correct_index"], 2)
        tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()
