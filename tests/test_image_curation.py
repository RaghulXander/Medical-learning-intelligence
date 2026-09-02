"""
tests/test_image_curation.py

Unit tests for Milestone 18A Image Curation & Triage suite:
- Synthetic PNG generation & header decoding
- Provenance parsing from filename
- Exact duplicate clustering & canonicalization
- Deterministic triage classification & decision status
- Contact sheet HTML generation
- Stratified sample selection
"""

import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from backend.curation.contact_sheets import ContactSheetGenerator
from backend.curation.image_inventory import ImageInventoryEngine, ImageRecord
from backend.curation.image_triage import DecisionStatus, ImageTriageEngine, TriageClass
from scripts.curate_reference_images import select_stratified_sample


def make_synthetic_png(w: int, h: int, r: int = 180, g: int = 50, b: int = 120, noise: bool = False) -> bytes:
    """Constructs valid in-memory PNG bytes for deterministic testing."""
    ihdr_data = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data)
    ihdr = struct.pack(">I4s", 13, b"IHDR") + ihdr_data + struct.pack(">I", ihdr_crc)

    if noise:
        raw_rows = []
        for y in range(h):
            row = bytearray([0])
            for x in range(w):
                row.extend([(x * 37 + y * 73) % 256, (x * 19 + y * 13) % 256, (x * 97 + y * 41) % 256])
            raw_rows.append(bytes(row))
        raw_scanlines = b"".join(raw_rows)
    else:
        raw_scanlines = b"".join(b"\x00" + bytes([r, g, b] * w) for _ in range(h))

    idat_data = zlib.compress(raw_scanlines)
    idat_crc = zlib.crc32(b"IDAT" + idat_data)
    idat = struct.pack(">I4s", len(idat_data), b"IDAT") + idat_data + struct.pack(">I", idat_crc)

    iend = struct.pack(">I4sI", 0, b"IEND", zlib.crc32(b"IEND"))
    return b"\x89PNG\r\n\x1a\n" + ihdr + idat + iend


class TestImageCurationSuite(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.image_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_png_header_and_provenance_parsing(self):
        # Create a synthetic 100x200 PNG file with valid filename format
        file_path = self.image_dir / "img-robins-p0070-f002.png"
        file_path.write_bytes(make_synthetic_png(100, 200))

        engine = ImageInventoryEngine(self.image_dir)
        rec = engine.inspect_image_file(file_path)

        self.assertEqual(rec.width, 100)
        self.assertEqual(rec.height, 200)
        self.assertEqual(rec.aspect_ratio, 0.5)
        self.assertEqual(rec.pixel_area, 20_000)
        self.assertFalse(rec.is_corrupt)
        self.assertEqual(rec.pdf_page, 70)
        self.assertEqual(rec.textbook_page, 54)  # 70 - 16
        self.assertEqual(rec.figure_index, 2)
        self.assertEqual(rec.figure_label, "Figure 2")
        self.assertTrue(len(rec.sha256) == 64)

    def test_exact_duplicate_detection(self):
        png_data = make_synthetic_png(50, 50)

        # Write two identical files with different names
        (self.image_dir / "img-robins-p0100-f001.png").write_bytes(png_data)
        (self.image_dir / "img-robins-p0105-f002.png").write_bytes(png_data)
        # Write one distinct file
        (self.image_dir / "img-robins-p0110-f001.png").write_bytes(make_synthetic_png(60, 60))

        engine = ImageInventoryEngine(self.image_dir)
        records, summary = engine.run_inventory()

        self.assertEqual(len(records), 3)
        self.assertEqual(summary["exact_duplicates_count"], 1)
        self.assertEqual(summary["unique_binary_hashes"], 2)

        dup_group = [r for r in records if r.is_exact_duplicate]
        self.assertEqual(len(dup_group), 2)
        # One canonical, one duplicate occurrence
        self.assertEqual(sum(1 for r in dup_group if r.is_canonical), 1)
        self.assertEqual(sum(1 for r in dup_group if not r.is_canonical), 1)

    def test_triage_classification_rules(self):
        triage_engine = ImageTriageEngine()

        # 1. Micro decoration bullet (5x5 px) -> AUTO_REJECT
        rec_bullet = ImageRecord(
            extraction_id="test-bullet",
            filename="img-robins-p0001-f001.png",
            relative_path="assets/bullet.png",
            source_short_name="robbins",
            source_document_hash="hash",
            pdf_page=1,
            textbook_page=None,
            figure_index=1,
            figure_label="Figure 1",
            file_size_bytes=400,
            sha256="sha-bullet",
            pixel_hash="px-bullet",
            width=5,
            height=5,
            aspect_ratio=1.0,
            pixel_area=25,
            bit_depth=8,
            color_type=2,
            color_mode="RGB",
            has_alpha=False,
            is_corrupt=False,
            entropy=2.1,
            blank_score=0.9,
        )
        res_bullet = triage_engine.evaluate_record(rec_bullet)
        self.assertEqual(res_bullet.decision_status, DecisionStatus.AUTO_REJECT_CANDIDATE)
        self.assertEqual(res_bullet.triage_class, TriageClass.LOGO_ICON_OR_DECORATION)

        # 2. Thin Page Rule (600x4 px) -> AUTO_REJECT
        rec_rule = ImageRecord(
            extraction_id="test-rule",
            filename="img-robins-p0002-f001.png",
            relative_path="assets/rule.png",
            source_short_name="robbins",
            source_document_hash="hash",
            pdf_page=2,
            textbook_page=None,
            figure_index=1,
            figure_label="Figure 1",
            file_size_bytes=1500,
            sha256="sha-rule",
            pixel_hash="px-rule",
            width=600,
            height=4,
            aspect_ratio=150.0,
            pixel_area=2400,
            bit_depth=8,
            color_type=2,
            color_mode="RGB",
            has_alpha=False,
            is_corrupt=False,
            entropy=1.5,
            blank_score=0.1,
        )
        res_rule = triage_engine.evaluate_record(rec_rule)
        self.assertEqual(res_rule.decision_status, DecisionStatus.AUTO_REJECT_CANDIDATE)
        self.assertEqual(res_rule.triage_class, TriageClass.PAGE_FRAGMENT_OR_RULE)

        # 3. High-resolution medical plate -> AUTO_KEEP
        rec_plate = ImageRecord(
            extraction_id="test-plate",
            filename="img-robins-p0050-f001.png",
            relative_path="assets/plate.png",
            source_short_name="robbins",
            source_document_hash="hash",
            pdf_page=50,
            textbook_page=34,
            figure_index=1,
            figure_label="Figure 1",
            file_size_bytes=500_000,
            sha256="sha-plate",
            pixel_hash="px-plate",
            width=800,
            height=600,
            aspect_ratio=1.3333,
            pixel_area=480_000,
            bit_depth=8,
            color_type=2,
            color_mode="RGB",
            has_alpha=False,
            is_corrupt=False,
            entropy=7.4,
            blank_score=0.0,
        )
        res_plate = triage_engine.evaluate_record(rec_plate)
        self.assertEqual(res_plate.decision_status, DecisionStatus.AUTO_KEEP_CANDIDATE)
        self.assertEqual(res_plate.triage_class, TriageClass.PATHOLOGY_MICROSCOPY)

        # 4. Small ambiguous inset -> HUMAN_REVIEW_REQUIRED (Safety rule: Never auto-delete valuable insets!)
        rec_inset = ImageRecord(
            extraction_id="test-inset",
            filename="img-robins-p0050-f002.png",
            relative_path="assets/inset.png",
            source_short_name="robbins",
            source_document_hash="hash",
            pdf_page=50,
            textbook_page=34,
            figure_index=2,
            figure_label="Figure 2",
            file_size_bytes=35_000,
            sha256="sha-inset",
            pixel_hash="px-inset",
            width=180,
            height=140,
            aspect_ratio=1.2857,
            pixel_area=25_200,
            bit_depth=8,
            color_type=2,
            color_mode="RGB",
            has_alpha=False,
            is_corrupt=False,
            entropy=6.8,
            blank_score=0.0,
        )
        res_inset = triage_engine.evaluate_record(rec_inset)
        self.assertEqual(res_inset.decision_status, DecisionStatus.HUMAN_REVIEW_REQUIRED)

    def test_contact_sheet_and_stratified_sampling(self):
        # Generate 10 synthetic files
        records = []
        for i in range(1, 11):
            fn = f"img-robins-p{i:04d}-f001.png"
            w = 50 * i
            h = 40 * i
            p = self.image_dir / fn
            p.write_bytes(make_synthetic_png(w, h, noise=True))

        engine = ImageInventoryEngine(self.image_dir)
        records, _ = engine.run_inventory()
        triage_engine = ImageTriageEngine()
        triage_results, _ = triage_engine.run_triage(records)

        # Test Contact Sheet Generator
        cs_dir = self.image_dir / "contact_sheets"
        generator = ContactSheetGenerator(output_dir=cs_dir)
        sheet_path = generator.render_contact_sheet(records, triage_results, max_images=10)
        self.assertTrue(sheet_path.exists())
        self.assertGreater(sheet_path.stat().st_size, 500)

        # Test Stratified Sampling
        sample = select_stratified_sample(records, triage_results, sample_size=5)
        self.assertEqual(len(sample), 5)
        self.assertIn("proposed_decision_status", sample[0])
        self.assertIn("proposed_triage_class", sample[0])


if __name__ == "__main__":
    unittest.main()
