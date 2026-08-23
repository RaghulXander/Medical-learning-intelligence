"""
scripts/ingest_cli.py

CLI tool for ingesting questions from various sources into the database:
- CSV / Excel files
- Google Forms JSON files
- External JSONL datasets
- Single question JSON payloads
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_engine, init_db
from backend.ingestion.universal_ingestor import UniversalQuestionIngestor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Universal Question Ingestion CLI")
    parser.add_argument("--source-type", type=str, required=True, choices=["csv", "google_forms", "jsonl", "manual"], help="Type of intake source")
    parser.add_argument("--file", type=Path, required=True, help="Path to input file")
    parser.add_argument("--source-exam-id", "--course-id", dest="source_exam_id", type=str, default=None, help="Optional source exam / past paper code (e.g., NEET-PG-2021)")
    parser.add_argument("--topic-id", type=str, default=None, help="Optional primary curriculum topic UUID")
    parser.add_argument("--created-by", type=str, default="cli_ingest", help="User or system identifier")
    parser.add_argument("--db-url", type=str, default=None, help="Database URL override")
    args = parser.parse_args()

    engine = get_engine(database_url=args.db_url)
    init_db(engine=engine)
    ingestor = UniversalQuestionIngestor(engine)

    if args.source_type == "csv":
        res = ingestor.ingest_csv(
            csv_file_or_content=args.file,
            source_exam_id=args.source_exam_id,
            primary_topic_id=args.topic_id,
            created_by=args.created_by,
        )
        logger.info(f"CSV Ingestion Result: {res}")
    elif args.source_type == "google_forms":
        with open(args.file, "r", encoding="utf-8") as f:
            rows = json.load(f)
        if not isinstance(rows, list):
            rows = [rows]
        res = ingestor.ingest_google_forms(
            form_rows=rows,
            source_exam_id=args.source_exam_id,
            primary_topic_id=args.topic_id,
            created_by=args.created_by,
        )
        logger.info(f"Google Forms Ingestion Result: {res}")
    elif args.source_type == "manual":
        with open(args.file, "r", encoding="utf-8") as f:
            data = json.load(f)
        q = ingestor.ingest_single(
            raw_dict=data,
            source_type="manual_entry",
            source_exam_id=args.source_exam_id,
            primary_topic_id=args.topic_id,
            created_by=args.created_by,
        )
        logger.info(f"Ingested Question ID: {q.id} ({q.stem[:80]}...)")


if __name__ == "__main__":
    main()
