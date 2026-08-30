"""
tests/test_provenance_manifest.py

Test Suite for BookProvenanceManifest & Provenance QC Hard Gate.
Verifies that embedding is strictly blocked if any physical pages are missing,
chunks failed, or page mappings are invalid.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from backend.ingestion.document_registry import (
    DocumentRegistry,
    RegisteredDocument,
)
from backend.ingestion.provenance_manifest import (
    BookProvenanceManifest,
    ProvenanceGateError,
    ProvenanceManifestAuditor,
)


class TestProvenanceManifest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_prov_gate_"))
        self.manifest_dir = self.temp_dir / "provenance_manifests"
        self.evidence_dir = self.temp_dir / "evidence_blocks"
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

        self.registry = DocumentRegistry(registry_path=self.temp_dir / "registry.json")
        self.auditor = ProvenanceManifestAuditor(
            manifest_dir=self.manifest_dir,
            evidence_dir=self.evidence_dir,
        )

        # Create a mock registered document: 30 pages total
        self.doc = RegisteredDocument(
            doc_id="test_book_doc_id",
            short_name="test_book",
            title="Test Pathology Book",
            author="Author",
            edition="1st",
            year=2024,
            publisher="Pub",
            source_type="TEXTBOOK",
            speciality="Pathology",
            subject="Pathology",
            file_name="test_book.pdf",
            file_path="/path/test_book.pdf",
            file_size_bytes=1000,
            sha256="abc123sha",
            total_pages=30,
            rights_status="AUTHORIZED",
            rights_basis="synthetic test fixture",
            textbook_page_offset=5,  # PDF Page 6 = Textbook Page 1
        )
        self.registry.documents[self.doc.doc_id] = self.doc
        self.registry.short_name_index[self.doc.short_name.lower()] = self.doc.doc_id
        self.registry.save()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_incomplete_manifest_blocks_embedding(self):
        """Tests that a partial book with missing pages is blocked from embedding."""
        # Only write evidence for chunk 1 (pages 1..15). Pages 16..30 are missing!
        ev_payload = {
            "slice_id": "test_book_p0001_p0015",
            "document_id": "test_book_doc_id",
            "source": "Test Pathology Book",
            "processing_mode": "LIVE_DOCAI",
            "processor_metadata": {"processor_version_id": "test-version"},
            "processed_pages": list(range(1, 16)),
            "evidence_blocks": [
                {
                    "evidence_id": f"ev_{p}",
                    "pdf_page": p,
                    "textbook_page": self.doc.get_textbook_page(p),
                    "content": f"Content for page {p}",
                    "word_count": 100,
                }
                for p in range(1, 16)
            ],
        }
        with open(self.evidence_dir / "test_book_p0001_p0015_evidence.json", "w") as f:
            json.dump(ev_payload, f)

        manifest = self.auditor.generate_manifest(
            doc_id_or_short_name="test_book",
            registry=self.registry,
            pages_per_chunk=15,
        )

        self.assertEqual(manifest.status, "INCOMPLETE")
        self.assertFalse(manifest.is_ready_for_embedding)
        self.assertEqual(manifest.completed_chunks, 1)
        self.assertEqual(manifest.expected_chunks, 2)
        self.assertEqual(len(manifest.missing_pages), 15)
        self.assertEqual(manifest.missing_pages, list(range(16, 31)))

        # Enforce gate should raise ProvenanceGateError
        with self.assertRaises(ProvenanceGateError) as ctx:
            self.auditor.enforce_embedding_gate("test_book", registry=self.registry)
        self.assertIn("HARD GATE STOP", str(ctx.exception))

    def test_complete_manifest_passes_embedding_gate(self):
        """Tests that 100% extracted book passes the provenance gate and allows embedding."""
        # Chunk 1 (pages 1..15)
        ev1 = {
            "slice_id": "test_book_p0001_p0015",
            "document_id": "test_book_doc_id",
            "source": "Test Pathology Book",
            "processing_mode": "LIVE_DOCAI",
            "processor_metadata": {"processor_version_id": "test-version"},
            "processed_pages": list(range(1, 16)),
            "evidence_blocks": [
                {
                    "evidence_id": f"ev_{p}",
                    "pdf_page": p,
                    "textbook_page": self.doc.get_textbook_page(p),
                    "content": f"Content for page {p}",
                    "word_count": 100,
                }
                for p in range(1, 16)
            ],
        }
        # Chunk 2 (pages 16..30)
        ev2 = {
            "slice_id": "test_book_p0016_p0030",
            "document_id": "test_book_doc_id",
            "source": "Test Pathology Book",
            "processing_mode": "LIVE_DOCAI",
            "processor_metadata": {"processor_version_id": "test-version"},
            "processed_pages": list(range(16, 31)),
            "evidence_blocks": [
                {
                    "evidence_id": f"ev_{p}",
                    "pdf_page": p,
                    "textbook_page": self.doc.get_textbook_page(p),
                    "content": f"Content for page {p}",
                    "word_count": 100,
                }
                for p in range(16, 31)
            ],
        }

        with open(self.evidence_dir / "test_book_p0001_p0015_evidence.json", "w") as f:
            json.dump(ev1, f)
        with open(self.evidence_dir / "test_book_p0016_p0030_evidence.json", "w") as f:
            json.dump(ev2, f)

        manifest = self.auditor.enforce_embedding_gate("test_book", registry=self.registry)

        self.assertEqual(manifest.status, "PASSED")
        self.assertTrue(manifest.is_ready_for_embedding)
        self.assertEqual(manifest.completed_chunks, 2)
        self.assertEqual(manifest.expected_chunks, 2)
        self.assertEqual(len(manifest.missing_pages), 0)
        self.assertEqual(manifest.total_evidence_blocks, 30)

        # Check persisted markdown manifest
        md_file = self.manifest_dir / "test_book_provenance_manifest.md"
        self.assertTrue(md_file.exists())
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("PASSED (READY FOR EMBEDDING)", content)

    def test_inconsistent_page_mapping_blocks_embedding(self):
        """Tests that invalid/inconsistent textbook page calculations block embedding."""
        # Chunk with corrupted textbook page offset
        ev_corrupted = {
            "slice_id": "test_book_p0001_p0015",
            "document_id": "test_book_doc_id",
            "source": "Test Pathology Book",
            "processing_mode": "LIVE_DOCAI",
            "processor_metadata": {"processor_version_id": "test-version"},
            "processed_pages": [10],
            "evidence_blocks": [
                {
                    "evidence_id": "ev_10",
                    "pdf_page": 10,
                    "textbook_page": 999,  # Inconsistent with offset=5 (should be 5)
                    "content": "Content",
                    "word_count": 50,
                }
            ],
        }
        with open(self.evidence_dir / "test_book_p0001_p0015_evidence.json", "w") as f:
            json.dump(ev_corrupted, f)

        manifest = self.auditor.generate_manifest("test_book", registry=self.registry)
        self.assertFalse(manifest.page_mapping_valid)
        self.assertFalse(manifest.is_ready_for_embedding)

    def test_mock_artifacts_never_pass_embedding_gate(self):
        """Complete page coverage from a local mock parser remains non-authoritative."""
        for start, end in ((1, 15), (16, 30)):
            payload = {
                "slice_id": f"test_book_p{start:04d}_p{end:04d}",
                "document_id": self.doc.doc_id,
                "source": self.doc.title,
                "processing_mode": "MOCK_LOCAL_PYPDF",
                "processor_metadata": {"processor_version_id": "test-version"},
                "processed_pages": list(range(start, end + 1)),
                "evidence_blocks": [],
            }
            path = self.evidence_dir / f"test_book_p{start:04d}_p{end:04d}_evidence.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f)

        manifest = self.auditor.generate_manifest("test_book", registry=self.registry)
        self.assertEqual(manifest.status, "FAILED")
        self.assertFalse(manifest.is_ready_for_embedding)
        self.assertEqual(manifest.processing_modes, ["MOCK_LOCAL_PYPDF"])

    def test_overlapping_runs_are_blocked_as_duplicate_pages(self):
        """Pilot and canonical artifacts cannot be silently merged."""
        payloads = [
            ("test_book_p0001_p0015", 1, 15),
            ("test_book_p0001_p0015_pilot", 1, 15),
            ("test_book_p0016_p0030", 16, 30),
        ]
        for slice_id, start, end in payloads:
            payload = {
                "slice_id": slice_id,
                "document_id": self.doc.doc_id,
                "source": self.doc.title,
                "processing_mode": "LIVE_DOCAI",
                "processor_metadata": {"processor_version_id": "test-version"},
                "processed_pages": list(range(start, end + 1)),
                "evidence_blocks": [],
            }
            with open(
                self.evidence_dir / f"{slice_id}_evidence.json",
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(payload, f)

        manifest = self.auditor.generate_manifest("test_book", registry=self.registry)
        self.assertEqual(manifest.status, "FAILED")
        self.assertFalse(manifest.is_ready_for_embedding)
        self.assertEqual(manifest.duplicate_pages, list(range(1, 16)))


if __name__ == "__main__":
    unittest.main()
