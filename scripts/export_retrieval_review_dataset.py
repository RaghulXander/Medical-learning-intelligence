"""Export a completed human retrieval review queue for strict evaluation."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.retrieval_review_service import RetrievalReviewService
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "retrieval"
    / "verified"
    / "m16a_retrieval_eval_v1.jsonl"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", default="m16a-retrieval-v1")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--database-url-env",
        default="DATABASE_URL",
        help="Environment-variable name containing the PostgreSQL URL (never pass the URL as a CLI argument).",
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
    database_url = os.environ.get(args.database_url_env)
    if not database_url:
        parser.error(f"{args.database_url_env} is not configured")
    engine = create_engine(database_url, hide_parameters=True, pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        parser.error("Verified retrieval export requires PostgreSQL")
    with sessionmaker(bind=engine)() as session:
        payload, summary = RetrievalReviewService.export_verified_dataset(
            session, args.slug
        )
    engine.dispose()

    if args.execute:
        if args.output.exists() and not args.overwrite:
            parser.error("Output exists; use --overwrite to replace it")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(payload)
    print(
        json.dumps(
            {
                **summary,
                "status": "EXPORTED" if args.execute else "DRY_RUN_VALID",
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
