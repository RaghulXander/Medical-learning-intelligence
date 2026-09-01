"""Validate or execute the versioned Milestone 16A retrieval benchmark."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()

from backend.services.embedding_service import GeminiEmbeddingProvider
from backend.services.hybrid_retrieval_service import HybridRetrievalService
from backend.services.retrieval_evaluation import (
    RetrievalEvaluator,
    load_evaluation_set,
    validate_gold_chunks,
)
from database.db import get_default_db_url
from database.models import EmbeddingRun


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--embedding-run-id")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    engine = create_engine(get_default_db_url(), hide_parameters=True)
    if engine.dialect.name != "postgresql":
        parser.error("Retrieval evaluation requires PostgreSQL")
    cases, dataset_hash = load_evaluation_set(args.dataset)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        validate_gold_chunks(session, cases)
        if args.validate_only:
            print(
                json.dumps(
                    {
                        "status": "VALID",
                        "case_count": len(cases),
                        "domain_count": len({case.domain for case in cases}),
                        "dataset_hash": dataset_hash,
                    },
                    sort_keys=True,
                )
            )
            return
        if not args.embedding_run_id or not args.output:
            parser.error("--embedding-run-id and --output are required unless --validate-only is used")
        run = session.get(EmbeddingRun, args.embedding_run_id)
        if not run:
            parser.error("Embedding run not found")
        provider = GeminiEmbeddingProvider(
            model_name=run.model_id,
            dimension=run.dimension,
            task_type=run.query_task_type,
            vertex_ai=run.provider == "google_vertex_ai",
        )
        report = RetrievalEvaluator(HybridRetrievalService(provider)).evaluate(
            session,
            cases=cases,
            dataset_hash=dataset_hash,
            embedding_run_id=run.id,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS" if report["gate_passed"] else "FAIL", "output": str(args.output)}))


if __name__ == "__main__":
    main()
