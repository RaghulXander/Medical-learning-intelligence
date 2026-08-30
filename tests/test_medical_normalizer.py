"""
tests/test_medical_normalizer.py

Test Suite for Medical Normalizer, Dual-Page Provenance (pdf_page vs textbook_page),
Header/Footer Stripping, and Two-Column Reading Order Reconstruction.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from backend.ingestion.docai_normalizer import (
    NormalizedBlock,
    NormalizedDocumentSlice,
)
from backend.ingestion.medical_normalizer import (
    MedicalNormalizer,
    PageEvidenceBlock,
    is_running_artifact,
)


class TestMedicalNormalizer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_med_norm_"))
        self.evidence_dir = self.temp_dir / "evidence_blocks"
        self.normalizer = MedicalNormalizer(evidence_dir=self.evidence_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_running_artifact_detection(self):
        """Tests that common book headers, watermarks, and margin numbers are detected as artifacts."""
        self.assertTrue(is_running_artifact("CHAPTER 2 Cellular Pathology 11"))
        self.assertTrue(is_running_artifact("UNIT I General Pathology"))
        self.assertTrue(is_running_artifact("vip.persianss.ir"))
        self.assertTrue(is_running_artifact("tahir99 - UnitedVRG"))
        self.assertTrue(is_running_artifact("12"))
        self.assertTrue(is_running_artifact("Robbins and Cotran Review of Pathology"))
        self.assertFalse(is_running_artifact("Hypertrophy is an increase in the size of cells resulting in an overall increase in organ size."))

    def test_dual_page_and_header_stripping(self):
        """Tests that physical PDF pages and printed textbook pages are preserved while header clutter is stripped."""
        # PDF page 21 corresponds to Textbook page 5 (offset = 16)
        header_block = NormalizedBlock(
            block_id="b_hdr",
            block_type="RUNNING_HEADER",
            content="CHAPTER 1 The Cell as a Unit of Health and Disease",
            confidence=0.98,
            original_doc_id="robbins_11e",
            original_doc_title="Robbins Pathologic Basis of Disease, 11th Ed.",
            original_page_number=21,
            slice_id="chunk_1",
            slice_page_number=1,
            content_hash="h1",
            pdf_page=21,
            textbook_page=5,
            is_header_or_footer=True,
            bounding_box={"ymin": 0.04, "xmin": 0.1, "ymax": 0.06, "xmax": 0.9},
        )

        body_block = NormalizedBlock(
            block_id="b_body",
            block_type="PARAGRAPH",
            content="The human genome contains approximately 3.2 billion DNA base pairs.",
            confidence=0.96,
            original_doc_id="robbins_11e",
            original_doc_title="Robbins Pathologic Basis of Disease, 11th Ed.",
            original_page_number=21,
            slice_id="chunk_1",
            slice_page_number=1,
            content_hash="h2",
            pdf_page=21,
            textbook_page=5,
            bounding_box={"ymin": 0.15, "xmin": 0.1, "ymax": 0.35, "xmax": 0.5},
        )

        footer_block = NormalizedBlock(
            block_id="b_ftr",
            block_type="RUNNING_FOOTER",
            content="5",
            confidence=0.99,
            original_doc_id="robbins_11e",
            original_doc_title="Robbins Pathologic Basis of Disease, 11th Ed.",
            original_page_number=21,
            slice_id="chunk_1",
            slice_page_number=1,
            content_hash="h3",
            pdf_page=21,
            textbook_page=5,
            is_header_or_footer=True,
            bounding_box={"ymin": 0.95, "xmin": 0.45, "ymax": 0.97, "xmax": 0.55},
        )

        norm_slice = NormalizedDocumentSlice(
            slice_id="chunk_1",
            parent_doc_id="robbins_11e",
            parent_doc_title="Robbins Pathologic Basis of Disease, 11th Ed.",
            start_page_1based=21,
            end_page_1based=21,
            total_blocks=3,
            blocks=[header_block, body_block, footer_block],
            markdown_text="Composite",
        )

        evidence_blocks = self.normalizer.normalize_slice(norm_slice)
        self.assertEqual(len(evidence_blocks), 1)

        ev = evidence_blocks[0]
        self.assertEqual(ev.pdf_page, 21)
        self.assertEqual(ev.textbook_page, 5)
        self.assertEqual(ev.document_id, "robbins_11e")
        self.assertEqual(ev.source, "Robbins Pathologic Basis of Disease, 11th Ed.")
        self.assertIn("The human genome contains", ev.content)
        # Verify header and footer were excluded from flowing evidence body
        self.assertNotIn("CHAPTER 1 The Cell as a Unit", ev.content)
        self.assertNotIn("\n5\n", ev.content)

    def test_two_column_reading_order_reconstruction(self):
        """Tests that two-column pathology layout is sequenced left column first, then right column."""
        # Top banner heading
        heading = NormalizedBlock(
            block_id="b_head",
            block_type="HEADING_2",
            content="Cellular Responses to Stress",
            confidence=0.98,
            original_doc_id="doc1",
            original_doc_title="Robbins",
            original_page_number=10,
            slice_id="c1",
            slice_page_number=1,
            content_hash="h_head",
            pdf_page=10,
            textbook_page=10,
            column_index=None,
            bounding_box={"ymin": 0.10, "xmin": 0.1, "ymax": 0.15, "xmax": 0.9},
        )

        # Left Column Paragraph (top)
        left_p1 = NormalizedBlock(
            block_id="b_l1",
            block_type="PARAGRAPH",
            content="[Left Col P1] Normal cells maintain homeostasis.",
            confidence=0.95,
            original_doc_id="doc1",
            original_doc_title="Robbins",
            original_page_number=10,
            slice_id="c1",
            slice_page_number=1,
            content_hash="h_l1",
            pdf_page=10,
            textbook_page=10,
            column_index=0,
            bounding_box={"ymin": 0.20, "xmin": 0.1, "ymax": 0.45, "xmax": 0.5},
        )

        # Left Column Paragraph (bottom)
        left_p2 = NormalizedBlock(
            block_id="b_l2",
            block_type="PARAGRAPH",
            content="[Left Col P2] When stresses exceed limits, cell injury occurs.",
            confidence=0.95,
            original_doc_id="doc1",
            original_doc_title="Robbins",
            original_page_number=10,
            slice_id="c1",
            slice_page_number=1,
            content_hash="h_l2",
            pdf_page=10,
            textbook_page=10,
            column_index=0,
            bounding_box={"ymin": 0.50, "xmin": 0.1, "ymax": 0.80, "xmax": 0.5},
        )

        # Right Column Paragraph (top)
        right_p1 = NormalizedBlock(
            block_id="b_r1",
            block_type="PARAGRAPH",
            content="[Right Col P1] Reversible injury manifests as swelling and fatty change.",
            confidence=0.95,
            original_doc_id="doc1",
            original_doc_title="Robbins",
            original_page_number=10,
            slice_id="c1",
            slice_page_number=1,
            content_hash="h_r1",
            pdf_page=10,
            textbook_page=10,
            column_index=1,
            bounding_box={"ymin": 0.20, "xmin": 0.55, "ymax": 0.50, "xmax": 0.95},
        )

        # Scrambled intake order (interleaved as OCR often reads horizontally)
        norm_slice = NormalizedDocumentSlice(
            slice_id="c1",
            parent_doc_id="doc1",
            parent_doc_title="Robbins",
            start_page_1based=10,
            end_page_1based=10,
            total_blocks=4,
            blocks=[heading, left_p1, right_p1, left_p2],  # Scrambled horizontal read
            markdown_text="Composite",
        )

        evidence_blocks = self.normalizer.normalize_slice(norm_slice)
        self.assertEqual(len(evidence_blocks), 1)

        content = evidence_blocks[0].content
        # Assert left_p2 appears BEFORE right_p1 in the reconstructed column flow
        l1_idx = content.find("[Left Col P1]")
        l2_idx = content.find("[Left Col P2]")
        r1_idx = content.find("[Right Col P1]")

        self.assertNotEqual(l1_idx, -1)
        self.assertNotEqual(l2_idx, -1)
        self.assertNotEqual(r1_idx, -1)

        # Correct reading flow: Left P1 -> Left P2 -> Right P1
        self.assertTrue(l1_idx < l2_idx < r1_idx)


if __name__ == "__main__":
    unittest.main()
