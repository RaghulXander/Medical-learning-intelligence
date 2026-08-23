"""
scripts/run_pipeline.py

End-to-end pipeline runner:
1. Ingests raw MedMCQA files.
2. Extracts Pathology questions across train, validation, test splits.
3. Normalizes records into target Question schema with decoupled topic structure.
4. Performs duplicate/similarity clustering without dropping any records.
5. Writes processed JSONL files and a summary report.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from extract_pathology import extract_pathology_splits
from import_medmcqa import download_medmcqa
from normalize_medmcqa import normalize_question_record
from deduplicate_questions import analyze_and_annotate_duplicates

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_RAW_DIR = Path("data/raw/medmcqa")
DEFAULT_PROCESSED_DIR = Path("data/processed/pathology")


def write_jsonl(records: List[Dict[str, Any]], output_file: Path) -> None:
    """Writes list of records to a JSON Lines file in UTF-8 encoding."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    logger.info(f"Wrote {len(records):,} records to {output_file} ({output_file.stat().st_size:,} bytes).")


def run_pipeline(
    raw_dir: Path = DEFAULT_RAW_DIR,
    processed_dir: Path = DEFAULT_PROCESSED_DIR,
    force_download: bool = False,
) -> Dict[str, Any]:
    """
    Executes the entire extraction, normalization, deduplication, and export pipeline.
    """
    logger.info("=== STEP 1: Ensuring Raw Data is Available ===")
    download_medmcqa(dest_dir=raw_dir, force=force_download)

    logger.info("=== STEP 2: Extracting Pathology Questions ===")
    extracted_splits = extract_pathology_splits(raw_dir=raw_dir, subject="Pathology")

    logger.info("=== STEP 3: Normalizing Records into Domain Schema ===")
    normalized_splits: Dict[str, List[Dict[str, Any]]] = {}
    all_normalized_records: List[Dict[str, Any]] = []

    for split_name in ("train", "validation", "test"):
        df_split = extracted_splits.get(split_name, pd.DataFrame())
        split_records: List[Dict[str, Any]] = []

        for _, row in df_split.iterrows():
            raw_dict = row.to_dict()
            normalized = normalize_question_record(raw_dict, split=split_name)
            split_records.append(normalized)

        normalized_splits[split_name] = split_records
        all_normalized_records.extend(split_records)
        logger.info(f"Normalized {len(split_records):,} records for split '{split_name}'.")

    logger.info("=== STEP 4: Analyzing Duplicate & Similarity Clusters ===")
    all_annotated_records, dedupe_report = analyze_and_annotate_duplicates(all_normalized_records)

    # Re-partition annotated records by split
    records_by_split: Dict[str, List[Dict[str, Any]]] = {
        "train": [],
        "validation": [],
        "test": [],
    }
    labeled_records: List[Dict[str, Any]] = []

    for rec in all_annotated_records:
        split_name = rec["metadata"]["split"]
        if split_name in records_by_split:
            records_by_split[split_name].append(rec)
        if rec["is_labeled"]:
            labeled_records.append(rec)

    logger.info("=== STEP 5: Writing Processed JSONL Outputs ===")
    processed_dir.mkdir(parents=True, exist_ok=True)

    # 1. All records
    all_file = processed_dir / "pathology_all.jsonl"
    write_jsonl(all_annotated_records, all_file)

    # 2. Labeled records only (train + val)
    labeled_file = processed_dir / "pathology_labeled.jsonl"
    write_jsonl(labeled_records, labeled_file)

    # 3. Individual splits
    train_file = processed_dir / "pathology_train.jsonl"
    write_jsonl(records_by_split["train"], train_file)

    val_file = processed_dir / "pathology_validation.jsonl"
    write_jsonl(records_by_split["validation"], val_file)

    test_file = processed_dir / "pathology_test.jsonl"
    write_jsonl(records_by_split["test"], test_file)

    # 4. Generate comprehensive summary report
    topic_status_counts = Counter(r["topic_mapping_status"] for r in all_annotated_records)
    raw_topics_counter = Counter(r["topic_name_original"] for r in all_annotated_records if r["topic_name_original"])
    exp_counts = sum(1 for r in all_annotated_records if r["explanation"])

    summary_report: Dict[str, Any] = {
        "dataset_name": "MedMCQA-Pathology",
        "pipeline_version": "1.0.0",
        "total_pathology_questions": len(all_annotated_records),
        "labeled_questions_count": len(labeled_records),
        "unlabeled_questions_count": len(all_annotated_records) - len(labeled_records),
        "split_counts": {
            "train": len(records_by_split["train"]),
            "validation": len(records_by_split["validation"]),
            "test": len(records_by_split["test"]),
        },
        "explanations_count": exp_counts,
        "explanations_percentage": round((exp_counts / len(all_annotated_records)) * 100, 2),
        "topic_mapping_distribution": dict(topic_status_counts),
        "unique_raw_topics_count": len(raw_topics_counter),
        "top_15_raw_topics": raw_topics_counter.most_common(15),
        "deduplication_summary": dedupe_report,
    }

    report_file = processed_dir / "summary_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2, ensure_ascii=False)
    logger.info(f"Summary report written to {report_file}")

    return summary_report


def main():
    parser = argparse.ArgumentParser(description="Run Pathology MedMCQA extraction & normalization pipeline")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR, help="Directory containing raw parquet files")
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR, help="Directory to output processed JSONL files")
    parser.add_argument("--force-download", action="store_true", help="Force re-download of raw dataset files")
    args = parser.parse_args()

    run_pipeline(
        raw_dir=args.raw_dir,
        processed_dir=args.processed_dir,
        force_download=args.force_download,
    )


if __name__ == "__main__":
    main()
