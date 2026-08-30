"""
tests/test_reference_document_ingestion.py

Comprehensive Test Suite for Reference Document Ingestion, PDF Splitting with Page Offset Preservation,
GCP Document AI Normalization, Extraction Quality Scoring, and Strict Provenance Guarantees.
"""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import pypdf

from backend.ingestion.docai_normalizer import (
    DocumentAINormalizer,
    NormalizedBlock,
    NormalizedDocumentSlice,
)
from backend.ingestion.document_registry import (
    DocumentRegistry,
    RegisteredDocument,
    SliceManifest,
    compute_file_sha256,
)
from backend.ingestion.gcp_docai_client import DocumentAIClient
from backend.ingestion.pdf_splitter import PDFSplitter
from backend.ingestion.quality_report import QualityReport, QualityReportGenerator


def create_test_pdf(file_path: Path, num_pages: int = 20) -> Path:
    """Helper to generate a clean multi-page synthetic PDF with page text."""
    writer = pypdf.PdfWriter()
    for p in range(1, num_pages + 1):
        # Add a blank page with metadata
        page = writer.add_blank_page(width=612, height=792)
    with open(file_path, "wb") as f:
        writer.write(f)
    return file_path


class TestReferenceDocumentIngestion(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_docai_"))
        self.registry_file = self.temp_dir / "registry.json"
        self.slices_dir = self.temp_dir / "slices"
        self.normalized_dir = self.temp_dir / "normalized"
        self.reports_dir = self.temp_dir / "reports"
        self.raw_docai_dir = self.temp_dir / "raw_docai"

        self.registry = DocumentRegistry(registry_path=self.registry_file)
        self.splitter = PDFSplitter(registry=self.registry, slices_dir=self.slices_dir)
        self.normalizer = DocumentAINormalizer(normalized_dir=self.normalized_dir)
        self.report_gen = QualityReportGenerator(reports_dir=self.reports_dir)
        self.client = DocumentAIClient(raw_output_dir=self.raw_docai_dir)

        # Create a sample 30-page textbook PDF
        self.sample_pdf_path = self.temp_dir / "Sample_Pathology_Textbook.pdf"
        create_test_pdf(self.sample_pdf_path, num_pages=30)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_immutable_document_registry_and_tamper_detection(self):
        """Tests document registration, deterministic UUID generation, and SHA-256 tamper verification."""
        doc = self.registry.register_document(
            file_path=self.sample_pdf_path,
            short_name="sample_pathology",
            title="Sample Pathology Textbook",
            author="Test Author",
            edition="1st Edition",
            year=2026,
            publisher="DocEdge Press",
            source_type="TEXTBOOK",
        )

        self.assertIsNotNone(doc.doc_id)
        self.assertEqual(doc.short_name, "sample_pathology")
        self.assertEqual(doc.total_pages, 30)
        self.assertTrue(len(doc.sha256) == 64)
        self.assertEqual(doc.rights_status, "UNVERIFIED")

        with self.assertRaisesRegex(ValueError, "rights_basis is required"):
            self.registry.register_document(
                file_path=self.sample_pdf_path,
                short_name="authorized_without_basis",
                title="Synthetic Fixture",
                rights_status="AUTHORIZED",
            )

        authorized = self.registry.register_document(
            file_path=self.sample_pdf_path,
            short_name="sample_pathology",
            title="Sample Pathology Textbook",
            rights_status="AUTHORIZED",
            rights_basis="synthetic test fixture",
        )
        rescanned = self.registry.register_document(
            file_path=self.sample_pdf_path,
            short_name="sample_pathology",
            title="Sample Pathology Textbook",
        )
        self.assertEqual(rescanned.rights_status, "AUTHORIZED")
        self.assertEqual(rescanned.rights_basis, "synthetic test fixture")
        self.assertEqual(rescanned.registered_at, authorized.registered_at)

        # Verify lookup
        found_by_id = self.registry.get_document(doc.doc_id)
        self.assertIsNotNone(found_by_id)
        self.assertEqual(found_by_id.title, "Sample Pathology Textbook")

        found_by_name = self.registry.get_document("sample_pathology")
        self.assertIsNotNone(found_by_name)
        self.assertEqual(found_by_name.doc_id, doc.doc_id)

        # Verify integrity initially succeeds
        is_valid, exp_hash, act_hash, status = self.registry.verify_integrity(doc.doc_id)
        self.assertTrue(is_valid)
        self.assertEqual(exp_hash, act_hash)
        self.assertEqual(status, "INTEGRITY_VERIFIED")

        # Test persistence across reload
        reloaded_registry = DocumentRegistry(registry_path=self.registry_file)
        self.assertEqual(len(reloaded_registry.documents), 1)
        self.assertIn(doc.doc_id, reloaded_registry.documents)

        # Tamper with the physical file
        with open(self.sample_pdf_path, "ab") as f:
            f.write(b"TAMPER_DATA")

        is_valid_tampered, exp_t, act_t, status_t = self.registry.verify_integrity(doc.doc_id)
        self.assertFalse(is_valid_tampered)
        self.assertNotEqual(exp_t, act_t)
        self.assertIn("INTEGRITY_VIOLATION", status_t)

    def test_pdf_splitter_exact_page_offset_preservation(self):
        """Tests extracting PDF slices while ensuring exact 1-based page offset mapping."""
        doc = self.registry.register_document(
            file_path=self.sample_pdf_path,
            short_name="sample_pathology",
            title="Sample Pathology Textbook",
        )

        # Slice pages 10 to 18 (9 pages)
        manifest = self.splitter.split_slice(
            doc_id_or_short_name=doc.doc_id,
            start_page_1based=10,
            end_page_1based=18,
        )

        self.assertEqual(manifest.start_page_1based, 10)
        self.assertEqual(manifest.end_page_1based, 18)
        self.assertEqual(manifest.page_count, 9)
        self.assertTrue(Path(manifest.slice_file_path).exists())

        # Verify slice PDF has exactly 9 pages
        slice_reader = pypdf.PdfReader(manifest.slice_file_path)
        self.assertEqual(len(slice_reader.pages), 9)

        # Verify exact 1-based page offset map
        # Local slice page 1 -> Original book page 10
        # Local slice page 9 -> Original book page 18
        self.assertEqual(manifest.page_offset_map[1], 10)
        self.assertEqual(manifest.page_offset_map[2], 11)
        self.assertEqual(manifest.page_offset_map[9], 18)

        # Test invalid bounds raise ValueError
        with self.assertRaises(ValueError):
            self.splitter.split_slice(doc.doc_id, start_page_1based=0, end_page_1based=5)
        with self.assertRaises(ValueError):
            self.splitter.split_slice(doc.doc_id, start_page_1based=10, end_page_1based=50)
        with self.assertRaises(ValueError):
            self.splitter.split_slice(doc.doc_id, start_page_1based=15, end_page_1based=10)

    def test_docai_online_limit_enforcement(self):
        """Tests that Document AI client enforces the <= 15 online page limit."""
        large_slice_pdf = self.temp_dir / "large_slice.pdf"
        create_test_pdf(large_slice_pdf, num_pages=16)

        manifest_large = SliceManifest(
            slice_id="large_slice",
            parent_doc_id="doc1",
            parent_doc_title="Large Doc",
            parent_sha256="abc",
            start_page_1based=1,
            end_page_1based=16,
            page_count=16,
            slice_file_path=str(large_slice_pdf),
            slice_file_name="large_slice.pdf",
            slice_sha256="xyz",
        )

        # Attempting online parse of 16-page slice must raise ValueError
        with self.assertRaisesRegex(ValueError, "exceeds Document AI online limit of 15 pages"):
            self.client.process_slice_online(large_slice_pdf, manifest=manifest_large, force_mock=True)

        # A 15-page slice must succeed
        valid_slice_pdf = self.temp_dir / "valid_slice.pdf"
        create_test_pdf(valid_slice_pdf, num_pages=15)
        manifest_valid = SliceManifest(
            slice_id="valid_slice",
            parent_doc_id="doc1",
            parent_doc_title="Valid Doc",
            parent_sha256="abc",
            start_page_1based=1,
            end_page_1based=15,
            page_count=15,
            slice_file_path=str(valid_slice_pdf),
            slice_file_name="valid_slice.pdf",
            slice_sha256="xyz",
        )

        result = self.client.process_slice_online(valid_slice_pdf, manifest=manifest_valid, force_mock=True)
        self.assertIn("pages", result)
        self.assertEqual(len(result["pages"]), 15)
        self.assertEqual(result["_docedge"]["processing_mode"], "MOCK_LOCAL_PYPDF")
        self.assertFalse(result["_docedge"]["eligible_for_medical_evidence"])

    def test_live_client_requires_a_pinned_processor_version(self):
        missing_proc = DocumentAIClient(
            project_id="test-project",
            location="us",
            processor_id="",
            processor_version_id="",
            raw_output_dir=self.raw_docai_dir,
        )
        with self.assertRaisesRegex(RuntimeError, "GCP_PROCESSOR_ID"):
            missing_proc._validate_live_config()

        configured = DocumentAIClient(
            project_id="test-project",
            location="us",
            processor_id="test-processor",
            processor_version_id="test-version",
            raw_output_dir=self.raw_docai_dir,
        )
        configured._validate_live_config()

    def test_docai_normalizer_structure_and_zero_loss_provenance(self):
        """Tests that Document AI layout normalizer constructs typed blocks with exact page provenance."""
        doc = self.registry.register_document(
            file_path=self.sample_pdf_path,
            short_name="sample_pathology",
            title="Sample Pathology Textbook",
        )

        manifest = self.splitter.split_slice(
            doc_id_or_short_name=doc.doc_id,
            start_page_1based=11,
            end_page_1based=13,
        )

        # Synthesize raw Document AI JSON with Headings, Paragraphs, and Tables
        mock_raw_docai = {
            "text": "CHAPTER 5: CELLULAR ADAPTATIONS\nHypertrophy refers to an increase in the size of cells.\nAtrophy is a reduction in size.\nTable 5.1: Patterns of Necrosis\n",
            "pages": [
                {
                    "pageNumber": 1,  # Slice page 1 -> Original page 101
                    "blocks": [
                        {
                            "type": "heading",
                            "layout": {
                                "textAnchor": {"textSegments": [{"startIndex": "0", "endIndex": "31"}]},
                                "confidence": 0.98,
                                "boundingPoly": {
                                    "normalizedVertices": [
                                        {"x": 0.1, "y": 0.1},
                                        {"x": 0.9, "y": 0.1},
                                        {"x": 0.9, "y": 0.15},
                                        {"x": 0.1, "y": 0.15},
                                    ]
                                },
                            },
                        }
                    ],
                    "paragraphs": [
                        {
                            "type": "paragraph",
                            "layout": {
                                "textAnchor": {"textSegments": [{"startIndex": "32", "endIndex": "87"}]},
                                "confidence": 0.95,
                                "boundingPoly": {
                                    "normalizedVertices": [
                                        {"x": 0.1, "y": 0.2},
                                        {"x": 0.9, "y": 0.2},
                                        {"x": 0.9, "y": 0.3},
                                        {"x": 0.1, "y": 0.3},
                                    ]
                                },
                            },
                        }
                    ],
                },
                {
                    "pageNumber": 2,  # Slice page 2 -> Original page 102
                    "paragraphs": [
                        {
                            "type": "paragraph",
                            "layout": {
                                "textAnchor": {"textSegments": [{"startIndex": "88", "endIndex": "118"}]},
                                "confidence": 0.94,
                            },
                        }
                    ],
                    "tables": [
                        {
                            "layout": {"confidence": 0.92},
                            "headerRows": [
                                {
                                    "cells": [
                                        {"layout": {"textAnchor": {"content": "Type"}}},
                                        {"layout": {"textAnchor": {"content": "Etiology"}}},
                                    ]
                                }
                            ],
                            "bodyRows": [
                                {
                                    "cells": [
                                        {"layout": {"textAnchor": {"content": "Coagulative"}}},
                                        {"layout": {"textAnchor": {"content": "Ischemia"}}},
                                    ]
                                }
                            ],
                        }
                    ],
                },
            ],
        }

        normalized_slice = self.normalizer.normalize(
            raw_docai_data=mock_raw_docai,
            manifest=manifest,
        )

        self.assertEqual(normalized_slice.total_blocks, 4)
        self.assertEqual(normalized_slice.parent_doc_id, doc.doc_id)
        self.assertEqual(normalized_slice.parent_doc_title, doc.title)

        blocks = normalized_slice.blocks
        # Block 0: Heading on slice page 1 -> original page 11
        self.assertEqual(blocks[0].block_type, "HEADING_2")
        self.assertEqual(blocks[0].content, "CHAPTER 5: CELLULAR ADAPTATIONS")
        self.assertEqual(blocks[0].original_page_number, 11)
        self.assertEqual(blocks[0].original_doc_id, doc.doc_id)
        self.assertIsNotNone(blocks[0].bounding_box)

        # Block 1: Paragraph on slice page 1 -> original page 11
        self.assertEqual(blocks[1].block_type, "PARAGRAPH")
        self.assertIn("Hypertrophy", blocks[1].content)
        self.assertEqual(blocks[1].original_page_number, 11)

        # Block 2: Paragraph on slice page 2 -> original page 12
        self.assertEqual(blocks[2].block_type, "PARAGRAPH")
        self.assertIn("Atrophy", blocks[2].content)
        self.assertEqual(blocks[2].original_page_number, 12)

        # Block 3: Table on slice page 2 -> original page 12
        self.assertEqual(blocks[3].block_type, "TABLE")
        self.assertIn("| Type | Etiology |", blocks[3].content)
        self.assertIn("| Coagulative | Ischemia |", blocks[3].content)
        self.assertEqual(blocks[3].original_page_number, 12)

    def test_document_layout_preserves_live_mode_and_page_receipts(self):
        """The live documentLayout path retains parser metadata and physical pages."""
        manifest = SliceManifest(
            slice_id="layout_slice",
            parent_doc_id="doc-layout",
            parent_doc_title="Synthetic Layout Fixture",
            parent_sha256="fixture",
            start_page_1based=11,
            end_page_1based=12,
            page_count=2,
            slice_file_path="fixture.pdf",
            slice_file_name="fixture.pdf",
            slice_sha256="fixture-slice",
            page_offset_map={1: 11, 2: 12},
        )
        raw = {
            "_docedge": {
                "processing_mode": "LIVE_DOCAI",
                "processor_version_id": "test-version",
            },
            "documentLayout": {
                "blocks": [
                    {
                        "blockId": "heading-1",
                        "pageSpan": {"pageStart": 1, "pageEnd": 1},
                        "textBlock": {"type": "heading", "text": "Cell injury"},
                    },
                    {
                        "blockId": "paragraph-1",
                        "pageSpan": {"pageStart": 2, "pageEnd": 2},
                        "textBlock": {
                            "type": "paragraph",
                            "text": "Synthetic fixture content.",
                        },
                    },
                ]
            },
        }

        normalized = self.normalizer.normalize(raw, manifest)

        self.assertEqual(normalized.processing_mode, "LIVE_DOCAI")
        self.assertEqual(normalized.summary_stats["processed_pages"], [11, 12])
        self.assertEqual([block.pdf_page for block in normalized.blocks], [11, 12])
        self.assertTrue(
            all(
                block.metadata["processor_version_id"] == "test-version"
                for block in normalized.blocks
            )
        )
        self.assertTrue(all(block.confidence is None for block in normalized.blocks))

    def test_provenance_audit_and_quality_report(self):
        """Tests that extraction quality report verifies 100% provenance and catches anomalies."""
        doc = self.registry.register_document(
            file_path=self.sample_pdf_path,
            short_name="sample_pathology",
            title="Sample Pathology Textbook",
        )

        manifest = self.splitter.split_slice(
            doc_id_or_short_name=doc.doc_id,
            start_page_1based=1,
            end_page_1based=2,
        )

        # Create valid normalized blocks
        b1 = NormalizedBlock(
            block_id="b1",
            block_type="HEADING_1",
            content="General Pathology",
            confidence=0.98,
            original_doc_id=doc.doc_id,
            original_doc_title=doc.title,
            original_page_number=1,
            slice_id=manifest.slice_id,
            slice_page_number=1,
            content_hash="hash1",
        )
        b2 = NormalizedBlock(
            block_id="b2",
            block_type="PARAGRAPH",
            content="Pathology is the study of disease mechanisms.",
            confidence=0.95,
            original_doc_id=doc.doc_id,
            original_doc_title=doc.title,
            original_page_number=2,
            slice_id=manifest.slice_id,
            slice_page_number=2,
            content_hash="hash2",
        )

        norm_slice = NormalizedDocumentSlice(
            slice_id=manifest.slice_id,
            parent_doc_id=doc.doc_id,
            parent_doc_title=doc.title,
            start_page_1based=1,
            end_page_1based=2,
            total_blocks=2,
            blocks=[b1, b2],
            markdown_text="# General Pathology\n\nPathology is the study of disease mechanisms.",
            processing_mode="LIVE_DOCAI",
            processor_metadata={"processor_version_id": "test-version"},
        )

        report = self.report_gen.generate_report(norm_slice, registry=self.registry)
        self.assertEqual(report.provenance_integrity_score, 1.0)
        self.assertTrue(report.provenance_verified)
        self.assertEqual(report.total_blocks, 2)
        self.assertGreater(report.total_words, 0)
        self.assertTrue(report.eligible_for_evidence)
        self.assertFalse(report.extraction_accuracy_verified)
        self.assertIn("PROVENANCE PASSED", report.to_markdown())

        # Test anomaly detection when page is out of bounds
        corrupt_block = NormalizedBlock(
            block_id="corrupt_b",
            block_type="PARAGRAPH",
            content="Corrupted page attribution",
            confidence=0.60,  # Low confidence
            original_doc_id="wrong_doc_id",  # Mismatched doc_id
            original_doc_title=doc.title,
            original_page_number=999,  # Out of range page
            slice_id=manifest.slice_id,
            slice_page_number=1,
            content_hash="corrupt_hash",
        )
        corrupted_slice = NormalizedDocumentSlice(
            slice_id=manifest.slice_id,
            parent_doc_id=doc.doc_id,
            parent_doc_title=doc.title,
            start_page_1based=1,
            end_page_1based=2,
            total_blocks=1,
            blocks=[corrupt_block],
            markdown_text="Corrupted",
            processing_mode="LIVE_DOCAI",
            processor_metadata={"processor_version_id": "test-version"},
        )

        corrupt_report = self.report_gen.generate_report(corrupted_slice, registry=self.registry)
        self.assertEqual(corrupt_report.provenance_integrity_score, 0.0)
        self.assertFalse(corrupt_report.provenance_verified)
        self.assertGreater(len(corrupt_report.anomalies), 0)
        self.assertTrue(any("exceeding parent total pages" in a or "Provenance failure" in a for a in corrupt_report.anomalies))


if __name__ == "__main__":
    unittest.main()
