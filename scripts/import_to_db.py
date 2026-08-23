"""
scripts/import_to_db.py

High-performance database ingestion script for Medical Exam AI.
Imports normalized Pathology JSONL datasets into PostgreSQL / SQLite database.
Seeds foundational knowledge sources, courses, users, and curriculum taxonomy.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_engine, init_db, session_scope
from database.models import (
    CurriculumLevel,
    CurriculumTopic,
    Question,
    QuestionStatus,
    QuestionType,
    Source,
    SourceType,
    TopicMappingStatus,
)
from scripts.seed_curriculum import FOUNDATIONAL_SOURCES, seed_curriculum

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_INPUT_FILE = (
    Path("data/processed/pathology/pathology_all.jsonl")
    if Path("data/processed/pathology/pathology_all.jsonl").exists()
    else Path("data/processed/pathology/pathology_labeled.jsonl")
)


def seed_sources_and_curriculum(engine) -> None:
    """Seeds authoritative pathology sources, courses, users, and curriculum taxonomy."""
    seed_curriculum(engine)


def parse_iso_datetime(iso_str: Optional[str]) -> datetime:
    """Parses ISO string to UTC datetime."""
    if not iso_str:
        return datetime.now(timezone.utc)
    try:
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"
        return datetime.fromisoformat(iso_str)
    except Exception:
        return datetime.now(timezone.utc)


def import_questions_from_jsonl(
    jsonl_path: Path,
    engine,
    batch_size: int = 1000,
    skip_existing: bool = True,
) -> Dict[str, Any]:
    """
    Imports questions from a processed JSONL file into the database in batches.
    """
    if not jsonl_path.exists():
        raise FileNotFoundError(f"Input JSONL file not found: {jsonl_path}")

    logger.info(f"Starting import from {jsonl_path} (batch size: {batch_size})...")

    # Fetch existing external_source_ids to skip duplicates if requested
    existing_ids = set()
    if skip_existing:
        with session_scope(engine) as session:
            existing_ids = {qid[0] for qid in session.query(Question.external_source_id).all()}
            logger.info(f"Found {len(existing_ids):,} existing questions in database.")

    total_read = 0
    total_inserted = 0
    total_skipped = 0
    batch: List[Question] = []

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            total_read += 1
            rec = json.loads(line)
            ext_id = rec.get("external_source_id")

            if skip_existing and ext_id in existing_ids:
                total_skipped += 1
                continue

            topic_mapping_status_val = TopicMappingStatus(rec.get("topic_mapping_status", "UNMAPPED"))
            question_type_val = QuestionType(rec.get("question_type", "single_best_answer"))
            status_val = QuestionStatus(rec.get("status", "IMPORTED"))

            q = Question(
                id=rec["id"],
                external_source=rec.get("external_source", "medmcqa"),
                external_source_id=ext_id,
                source_exam_id=rec.get("source_exam_id") or rec.get("origin_exam_id") or rec.get("course_id"),
                speciality=rec.get("speciality", "Pathology"),
                subject=rec.get("subject", "Pathology"),
                topic_name_original=rec.get("topic_name_original"),
                topic_name_normalized=rec.get("topic_name_normalized"),
                topic_mapping_status=topic_mapping_status_val,
                primary_topic_id=rec.get("primary_topic_id") or rec.get("curriculum_topic_id"),
                learning_objective=rec.get("learning_objective"),
                question_type=question_type_val,
                stem=rec.get("stem", ""),
                options=rec.get("options", []),
                correct_option=rec.get("correct_option"),
                correct_index=rec.get("correct_index", -1),
                is_labeled=rec.get("is_labeled", True),
                explanation=rec.get("explanation"),
                difficulty=None,
                cognitive_level=None,
                status=status_val,
                quality_score=rec.get("quality_score"),
                content_hash=rec["content_hash"],
                exact_stem_hash=rec.get("exact_stem_hash", ""),
                norm_stem_hash=rec.get("norm_stem_hash", ""),
                duplicate_signals=rec.get("duplicate_signals"),
                metadata_json=rec.get("metadata", {}),
                created_by=rec.get("created_by", "system_import"),
                created_at=parse_iso_datetime(rec.get("created_at")),
                updated_at=parse_iso_datetime(rec.get("updated_at")),
            )

            batch.append(q)
            if ext_id:
                existing_ids.add(ext_id)

            if len(batch) >= batch_size:
                with session_scope(engine) as session:
                    session.add_all(batch)
                total_inserted += len(batch)
                batch = []
                logger.info(f"Progress: Read {total_read:,} | Inserted {total_inserted:,} | Skipped {total_skipped:,}")

    # Insert remaining batch
    if batch:
        with session_scope(engine) as session:
            session.add_all(batch)
        total_inserted += len(batch)

    logger.info(
        f"Import complete! Total processed: {total_read:,} | "
        f"Inserted: {total_inserted:,} | Skipped: {total_skipped:,}"
    )

    return {
        "total_read": total_read,
        "total_inserted": total_inserted,
        "total_skipped": total_skipped,
    }


def main():
    parser = argparse.ArgumentParser(description="Import processed Pathology questions into database")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_FILE, help="Path to input JSONL file")
    parser.add_argument("--db-url", type=str, default=None, help="Database connection URL (overrides env)")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch insert chunk size")
    parser.add_argument("--force-recreate", action="store_true", help="Drop and recreate all tables before import")
    args = parser.parse_args()

    engine = get_engine(database_url=args.db_url)

    if args.force_recreate:
        logger.warning("Dropping all existing database tables...")
        from database.models import Base
        Base.metadata.drop_all(bind=engine)

    init_db(engine=engine)
    seed_curriculum(engine=engine)
    import_questions_from_jsonl(
        jsonl_path=args.input,
        engine=engine,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
