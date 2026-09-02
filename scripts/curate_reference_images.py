"""
scripts/curate_reference_images.py

Milestone 18A: CLI Tool for Portable Pathology Image Curation,
Inventory Generation, Automated Triage, Contact Sheets, and 300-Image Calibration Set.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.curation.image_inventory import ImageInventoryEngine, ImageRecord
from backend.curation.image_triage import DecisionStatus, ImageTriageEngine, TriageClass, TriageResult
from backend.curation.contact_sheets import ContactSheetGenerator

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("image_curation")

DEFAULT_IMAGE_DIR = PROJECT_ROOT / "data" / "processed" / "images"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "images"
CONTACT_SHEETS_DIR = DEFAULT_OUTPUT_DIR / "contact_sheets"


def select_stratified_sample(
    records: List[ImageRecord],
    triage_results: List[TriageResult],
    sample_size: int = 300,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    Selects a stratified 300-image calibration sample across size bands,
    decision statuses, utility classes, and page ranges.
    """
    random.seed(seed)
    triage_map = {t.extraction_id: t for t in triage_results}

    # Group records by (decision_status, size_band)
    strata: Dict[str, List[ImageRecord]] = {}

    for rec in records:
        triage = triage_map.get(rec.extraction_id)
        status = triage.decision_status.value if triage else "UNKNOWN"

        if rec.file_size_bytes < 5_000:
            band = "micro"
        elif rec.file_size_bytes < 50_000:
            band = "small"
        elif rec.file_size_bytes < 500_000:
            band = "medium"
        else:
            band = "large"

        stratum_key = f"{status}_{band}"
        strata.setdefault(stratum_key, []).append(rec)

    sample: List[ImageRecord] = []
    total_strata = len(strata)
    quota_per_stratum = max(1, sample_size // total_strata)

    # First pass: take equal quotas
    remaining_pool: List[ImageRecord] = []
    for key, group in strata.items():
        shuffled = list(group)
        random.shuffle(shuffled)
        take_count = min(len(shuffled), quota_per_stratum)
        sample.extend(shuffled[:take_count])
        remaining_pool.extend(shuffled[take_count:])

    # Second pass: fill remaining slots up to sample_size
    if len(sample) < sample_size and remaining_pool:
        random.shuffle(remaining_pool)
        needed = sample_size - len(sample)
        sample.extend(remaining_pool[:needed])

    sample_dicts: List[Dict[str, Any]] = []
    for idx, rec in enumerate(sample[:sample_size], start=1):
        triage = triage_map.get(rec.extraction_id)
        sample_dicts.append({
            "sample_index": idx,
            "extraction_id": rec.extraction_id,
            "filename": rec.filename,
            "pdf_page": rec.pdf_page,
            "textbook_page": rec.textbook_page,
            "figure_index": rec.figure_index,
            "width": rec.width,
            "height": rec.height,
            "file_size_bytes": rec.file_size_bytes,
            "sha256": rec.sha256,
            "entropy": rec.entropy,
            "proposed_triage_class": triage.triage_class.value if triage else "UNKNOWN",
            "proposed_decision_status": triage.decision_status.value if triage else "UNKNOWN",
            "human_reviewer_decision": None,  # For human review in 18B
            "human_corrected_class": None,
            "human_notes": None,
        })

    logger.info(f"📋 Selected {len(sample_dicts)} stratified calibration images across {total_strata} strata.")
    return sample_dicts


def main():
    parser = argparse.ArgumentParser(description="Milestone 18A Image Curation & Triage CLI")
    parser.add_argument(
        "action",
        choices=["inventory", "triage", "contact-sheets", "sample-300", "export-valid", "run-all"],
        default="run-all",
        nargs="?",
        help="Action to execute (default: run-all)",
    )
    parser.add_argument("--image-dir", type=Path, default=DEFAULT_IMAGE_DIR, help="Path to extracted images directory")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Path to output artifacts directory")
    parser.add_argument("--include-review", action="store_true", help="Include HUMAN_REVIEW_REQUIRED images in export-valid")
    args = parser.parse_args()

    engine = ImageInventoryEngine(image_dir=args.image_dir)
    triage_engine = ImageTriageEngine()
    cs_generator = ContactSheetGenerator(output_dir=CONTACT_SHEETS_DIR)

    records: List[ImageRecord] = []
    triage_results: List[TriageResult] = []

    # 1. Run Inventory
    if args.action in ("inventory", "run-all", "triage", "contact-sheets", "sample-300"):
        records, inv_summary = engine.run_inventory()

        manifest_file = args.output_dir / "inventory_manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in records], f, indent=2)

        duplicate_clusters = {}
        for r in records:
            if r.is_exact_duplicate:
                duplicate_clusters.setdefault(r.sha256, []).append({
                    "filename": r.filename,
                    "pdf_page": r.pdf_page,
                    "is_canonical": r.is_canonical,
                })

        dup_report_file = args.output_dir / "duplicate_report.json"
        with open(dup_report_file, "w", encoding="utf-8") as f:
            json.dump({
                "summary": inv_summary,
                "exact_duplicate_clusters": duplicate_clusters,
            }, f, indent=2)

        logger.info(f"💾 Saved inventory manifest ({manifest_file}) and duplicate report ({dup_report_file}).")

    # 2. Run Triage
    if args.action in ("triage", "run-all", "contact-sheets", "sample-300"):
        triage_results, triage_summary = triage_engine.run_triage(records)

        triage_file = args.output_dir / "triage_summary.json"
        with open(triage_file, "w", encoding="utf-8") as f:
            json.dump({
                "summary": triage_summary,
                "results": [t.to_dict() for t in triage_results],
            }, f, indent=2)

        logger.info(f"💾 Saved triage summary to {triage_file}.")

    # 3. Contact Sheets
    if args.action in ("contact-sheets", "run-all"):
        cs_file = cs_generator.render_contact_sheet(
            records=records,
            triage_results=triage_results,
            title="Milestone 18A — Robbins 11th Image Curation Contact Sheet",
            sheet_filename="contact_sheet_index.html",
            max_images=300,
        )
        logger.info(f"🖼️ View contact sheet at: {cs_file}")

    # 4. Stratified 300-Image Calibration Set
    if args.action in ("sample-300", "run-all"):
        calibration_sample = select_stratified_sample(records, triage_results, sample_size=300)
        sample_file = args.output_dir / "human_calibration_sample_300.json"
        with open(sample_file, "w", encoding="utf-8") as f:
            json.dump(calibration_sample, f, indent=2)
        logger.info(f"💾 Saved 300-image calibration sample to {sample_file}.")

    # 5. Export Valid Images (Isolate valid images locally)
    if args.action in ("export-valid",):
        import shutil
        triage_file = args.output_dir / "triage_summary.json"
        if not triage_file.exists():
            records, _ = engine.run_inventory()
            triage_results, _ = triage_engine.run_triage(records)
        else:
            with open(triage_file, "r", encoding="utf-8") as f:
                t_data = json.load(f)
            triage_results = [
                TriageResult(
                    extraction_id=r["extraction_id"],
                    filename=r["filename"],
                    sha256=r["sha256"],
                    triage_class=TriageClass(r["triage_class"]),
                    decision_status=DecisionStatus(r["decision_status"]),
                    confidence=r["confidence"],
                    reasons=r["reasons"],
                    width=r["width"],
                    height=r["height"],
                    aspect_ratio=r["aspect_ratio"],
                    pixel_area=r["pixel_area"],
                    file_size_bytes=r["file_size_bytes"],
                    pdf_page=r["pdf_page"],
                    textbook_page=r["textbook_page"],
                    is_exact_duplicate=r["is_exact_duplicate"],
                )
                for r in t_data["results"]
            ]

        valid_dir = args.output_dir / "curated_valid"
        valid_dir.mkdir(parents=True, exist_ok=True)

        valid_targets = [DecisionStatus.AUTO_KEEP_CANDIDATE]
        if args.include_review:
            valid_targets.append(DecisionStatus.HUMAN_REVIEW_REQUIRED)

        valid_items = [t for t in triage_results if t.decision_status in valid_targets]
        logger.info(f"📦 Exporting {len(valid_items):,} valid images to {valid_dir} (include_review={args.include_review})...")

        valid_manifest = []
        for item in valid_items:
            src = args.image_dir / item.filename
            dst = valid_dir / item.filename
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
            valid_manifest.append(item.to_dict())

        valid_manifest_path = args.output_dir / "valid_images_manifest.json"
        with open(valid_manifest_path, "w", encoding="utf-8") as f:
            json.dump({
                "total_valid_count": len(valid_items),
                "export_directory": str(valid_dir),
                "images": valid_manifest,
            }, f, indent=2)

        logger.info(f"✅ Exported {len(valid_items):,} valid images to {valid_dir}")
        logger.info(f"📄 Valid manifest written to {valid_manifest_path}")


if __name__ == "__main__":
    main()
