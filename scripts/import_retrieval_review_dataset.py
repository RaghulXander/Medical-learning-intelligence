"""Import an unverified retrieval benchmark JSONL into the human-review queue.

The command is a dry run by default. It never upgrades bootstrap labels to
human-verified status and refuses to overwrite an existing dataset with a
different source hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from sqlalchemy import create_engine, select

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.models import (
    DocumentChunk,
    RetrievalBenchmark,
    RetrievalBenchmarkCase,
    RetrievalBenchmarkReview,
)


DEFAULT_DATASET = (
    PROJECT_ROOT / "data" / "evaluation" / "retrieval" / "m16a_retrieval_eval_v1.jsonl"
)
DEFAULT_SLUG = "m16a-retrieval-v1"
ID_NAMESPACE = uuid.UUID("2b2d2f16-df30-4b64-a481-da11373f2491")


def load_bootstrap_cases(path: Path) -> tuple[list[dict[str, Any]], str]:
    raw = path.read_bytes()
    cases = []
    seen = set()
    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            case_key = str(payload["id"]).strip()
            domain = str(payload["domain"]).strip()
            query = str(payload["query"]).strip()
            expected = [str(value) for value in payload.get("expected_chunk_ids", [])]
            out_of_corpus = bool(payload.get("out_of_corpus", False))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid bootstrap case at line {line_number}") from exc
        if not case_key or not domain or not query or case_key in seen:
            raise ValueError(f"Invalid or duplicate required field at line {line_number}")
        if out_of_corpus and expected:
            raise ValueError(f"Out-of-corpus case {case_key} declares expected chunks")
        if not out_of_corpus and not expected:
            raise ValueError(f"In-corpus case {case_key} has no candidate chunk")
        seen.add(case_key)
        cases.append(
            {
                "case_key": case_key,
                "domain": domain,
                "query": query,
                "expected_chunk_ids": expected,
                "out_of_corpus": out_of_corpus,
            }
        )
    if not cases:
        raise ValueError("Bootstrap dataset is empty")
    return cases, hashlib.sha256(raw).hexdigest()


def import_review_dataset(
    session,
    *,
    path: Path,
    slug: str = DEFAULT_SLUG,
    execute: bool = False,
    replace_unreviewed: bool = False,
) -> dict[str, Any]:
    cases, source_hash = load_bootstrap_cases(path)
    expected_chunk_ids = {
        chunk_id for case in cases for chunk_id in case["expected_chunk_ids"]
    }
    if expected_chunk_ids:
        found_chunk_ids = {
            str(row[0])
            for row in session.query(DocumentChunk.id)
            .filter(DocumentChunk.id.in_(expected_chunk_ids))
            .all()
        }
        missing_chunk_ids = expected_chunk_ids - found_chunk_ids
        if missing_chunk_ids:
            raise RuntimeError(
                "Bootstrap dataset references "
                f"{len(missing_chunk_ids)} chunk IDs absent from the target database"
            )
    existing = session.scalar(select(RetrievalBenchmark).where(RetrievalBenchmark.slug == slug))
    if existing:
        if existing.source_hash != source_hash:
            if not replace_unreviewed:
                raise RuntimeError(
                    f"Benchmark {slug} already exists with a different source hash"
                )
            existing_cases = session.query(RetrievalBenchmarkCase).filter_by(
                benchmark_id=existing.id
            ).all()
            existing_by_key = {case.case_key: case for case in existing_cases}
            incoming_by_key = {case["case_key"]: case for case in cases}
            review_count = (
                session.query(RetrievalBenchmarkReview)
                .join(RetrievalBenchmarkCase)
                .filter(RetrievalBenchmarkCase.benchmark_id == existing.id)
                .count()
            )
            if review_count or any(
                case.verification_status != "AUTO_BOOTSTRAP_UNVERIFIED"
                or case.reviewer_id is not None
                or case.reviewed_at is not None
                or case.review_notes is not None
                or case.revision != 1
                for case in existing_cases
            ):
                raise RuntimeError("Refusing to replace a benchmark after human review began")
            if set(existing_by_key) != set(incoming_by_key):
                raise RuntimeError("Replacement benchmark case keys do not match")
            if execute:
                for case_key, target in existing_by_key.items():
                    incoming = incoming_by_key[case_key]
                    target.domain = incoming["domain"]
                    target.query = incoming["query"]
                    target.expected_chunk_ids = incoming["expected_chunk_ids"]
                    target.out_of_corpus = incoming["out_of_corpus"]
                existing.source_hash = source_hash
                try:
                    existing.source_file = str(path.resolve().relative_to(PROJECT_ROOT))
                except ValueError:
                    existing.source_file = str(path.resolve())
                session.commit()
            return {
                "status": "REPLACED_UNREVIEWED" if execute else "DRY_RUN_REPLACE_VALID",
                "slug": slug,
                "case_count": len(cases),
                "source_hash": source_hash,
            }
        existing_count = session.query(RetrievalBenchmarkCase).filter_by(
            benchmark_id=existing.id
        ).count()
        if existing_count != len(cases):
            raise RuntimeError(
                f"Benchmark {slug} has {existing_count} cases; expected {len(cases)}"
            )
        return {
            "status": "ALREADY_IMPORTED",
            "slug": slug,
            "case_count": existing_count,
            "source_hash": source_hash,
        }

    if execute:
        benchmark_id = str(uuid.uuid5(ID_NAMESPACE, slug))
        try:
            source_file = str(path.resolve().relative_to(PROJECT_ROOT))
        except ValueError:
            source_file = str(path.resolve())
        benchmark = RetrievalBenchmark(
            id=benchmark_id,
            slug=slug,
            title="M16A Retrieval Evaluation — Human Review",
            version=1,
            status="HUMAN_REVIEW",
            source_file=source_file,
            source_hash=source_hash,
        )
        session.add(benchmark)
        for payload in cases:
            session.add(
                RetrievalBenchmarkCase(
                    id=str(uuid.uuid5(ID_NAMESPACE, f"{slug}:{payload['case_key']}")),
                    benchmark_id=benchmark_id,
                    verification_status="AUTO_BOOTSTRAP_UNVERIFIED",
                    revision=1,
                    **payload,
                )
            )
        session.commit()

    return {
        "status": "IMPORTED" if execute else "DRY_RUN_VALID",
        "slug": slug,
        "case_count": len(cases),
        "source_hash": source_hash,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the retrieval human-review queue")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--slug", default=DEFAULT_SLUG)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--replace-unreviewed",
        action="store_true",
        help="Replace a changed bootstrap only when no human review has begun",
    )
    parser.add_argument("--env-file", type=Path, default=PROJECT_ROOT / ".env")
    args = parser.parse_args()

    database_url = (dotenv_values(args.env_file).get("DATABASE_URL") or "").strip()
    if not database_url.startswith("postgresql"):
        raise RuntimeError("DATABASE_URL must identify PostgreSQL")
    engine = create_engine(database_url)
    from sqlalchemy.orm import sessionmaker

    with sessionmaker(bind=engine)() as session:
        result = import_review_dataset(
            session,
            path=args.dataset,
            slug=args.slug,
            execute=args.execute,
            replace_unreviewed=args.replace_unreviewed,
        )
    engine.dispose()
    print(f"status={result['status']}")
    print(f"slug={result['slug']}")
    print(f"case_count={result['case_count']}")
    print(f"source_hash={result['source_hash']}")


if __name__ == "__main__":
    main()
