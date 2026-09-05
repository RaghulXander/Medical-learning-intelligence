"""Dry-run or execute the controlled Milestone 19D text-question pilot."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from backend.services.embedding_service import GeminiEmbeddingProvider
from backend.services.generation.m19d_pilot import (
    M19D_COHORT_ID,
    M19D_CORPUS_MANIFEST_HASH,
    M19D_EMBEDDING_CONFIG_HASH,
    M19D_EMBEDDING_RUN_ID,
    M19D_RETRIEVAL_CONFIG_HASH,
    M19DPilotService,
    VertexPilotGenerator,
    load_blueprint,
)
from backend.services.hybrid_retrieval_service import HybridRetrievalService
from database.models import EmbeddingRun, EmbeddingRunStatus, Question


DEFAULT_BLUEPRINT = PROJECT_ROOT / "data/generation/blueprints/m19d_text_pilot_v1.json"
DEFAULT_ACCEPTANCE_REPORT = (
    PROJECT_ROOT / "data/evaluation/retrieval/reports/m19c_retrieval_eval_v1.json"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "data/generation/reports/m19d_text_pilot_v1.json"


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN"


def validate_acceptance_report(path: Path, blueprint) -> Dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "gate_passed": True,
        "dataset_hash": blueprint.accepted_dataset_hash,
        "embedding_run_id": blueprint.accepted_embedding_run_id,
        "retrieval_configuration_hash": blueprint.accepted_retrieval_config_hash,
        "citation_mismatches": 0,
    }
    mismatches = {
        key: {"expected": value, "actual": report.get(key)}
        for key, value in expected.items()
        if report.get(key) != value
    }
    if report.get("recall_at_5", 0) < 0.90:
        mismatches["recall_at_5"] = {"expected": ">=0.90", "actual": report.get("recall_at_5")}
    if report.get("unsupported_query_refusal_rate") != 1.0:
        mismatches["unsupported_query_refusal_rate"] = {
            "expected": 1.0,
            "actual": report.get("unsupported_query_refusal_rate"),
        }
    if any(item.get("recall_at_5", 0) < 0.80 for item in report.get("per_domain", {}).values()):
        mismatches["per_domain"] = {"expected": ">=0.80 each", "actual": report.get("per_domain")}
    if mismatches:
        raise ValueError(f"M19C acceptance report mismatch: {json.dumps(mismatches, sort_keys=True)}")
    return report


def estimate_usage(
    row_count: int,
    input_rate: float | None,
    output_rate: float | None,
    embedding_rate: float | None,
) -> Dict[str, Any]:
    # Conservative planning caps. Actual usage is recorded from each provider receipt.
    input_tokens = row_count * 18_000
    output_tokens = row_count * 2_200
    generation_cost = None
    embedding_cost = None
    total_cost = None
    if input_rate is not None and output_rate is not None:
        generation_cost = (input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * output_rate
    if embedding_rate is not None:
        embedding_cost = (row_count / 1_000) * embedding_rate
    if generation_cost is not None and embedding_cost is not None:
        total_cost = round(generation_cost + embedding_cost, 4)
    return {
        "maximum_generation_requests": row_count,
        "maximum_query_embedding_requests": row_count,
        "estimated_max_input_tokens": input_tokens,
        "estimated_max_output_tokens": output_tokens,
        "estimated_generation_cost": round(generation_cost, 4) if generation_cost is not None else None,
        "estimated_query_embedding_cost": round(embedding_cost, 6) if embedding_cost is not None else None,
        "estimated_total_cost": total_cost,
        "cost_currency": "USD" if total_cost is not None else None,
        "pricing_note": (
            "Estimate uses caller-supplied generation token rates and query-embedding request rate."
            if total_cost is not None
            else "Supply current generation and query-embedding rates before approval."
        ),
    }


def build_preflight(args, blueprint, blueprint_hash: str, report: Dict[str, Any]) -> Dict[str, Any]:
    selected = blueprint.rows[: args.limit]
    return {
        "status": "READY_FOR_COST_APPROVAL" if blueprint.is_approved else "BLUEPRINT_APPROVAL_REQUIRED",
        "mode": "execute" if args.execute else "dry_run",
        "blueprint_id": blueprint.blueprint_id,
        "blueprint_hash": blueprint_hash,
        "blueprint_status": blueprint.status,
        "blueprint_rows": len(blueprint.rows),
        "selected_rows": len(selected),
        "domain_distribution": dict(sorted(Counter(row.domain for row in selected).items())),
        "difficulty_distribution": dict(sorted(Counter(row.difficulty for row in selected).items())),
        "cognitive_distribution": dict(sorted(Counter(row.cognitive_level for row in selected).items())),
        "accepted_artifacts": {
            "corpus_manifest_hash": M19D_CORPUS_MANIFEST_HASH,
            "dataset_hash": report["dataset_hash"],
            "embedding_run_id": report["embedding_run_id"],
            "embedding_config_hash": M19D_EMBEDDING_CONFIG_HASH,
            "retrieval_config_hash": report["retrieval_configuration_hash"],
        },
        "vertex": {
            "project": os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID") or "NOT_CONFIGURED",
            "location": os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            "model": args.model,
        },
        "usage_estimate": estimate_usage(
            len(selected),
            args.input_cost_per_million,
            args.output_cost_per_million,
            args.embedding_cost_per_thousand,
        ),
        "will_call_vertex": bool(args.execute),
        "will_write_database": bool(args.execute),
    }


def validate_remote_run(session) -> EmbeddingRun:
    run = session.get(EmbeddingRun, M19D_EMBEDDING_RUN_ID)
    if not run or run.status != EmbeddingRunStatus.COMPLETED:
        raise ValueError("Accepted M19D embedding run is absent or incomplete")
    if run.provider != "google_vertex_ai" or run.model_id != "gemini-embedding-001":
        raise ValueError("Accepted embedding provider/model changed")
    if run.dimension != 768 or run.completed_chunk_count != 2845 or run.failed_chunk_count:
        raise ValueError("Accepted embedding cohort counts or dimensions changed")
    if run.config_hash != M19D_EMBEDDING_CONFIG_HASH:
        raise ValueError("Accepted embedding configuration hash changed")
    return run


def write_report(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def execute(args, blueprint, blueprint_hash: str, preflight: Dict[str, Any]) -> Dict[str, Any]:
    if not blueprint.is_approved:
        raise ValueError("Blueprint must be human-approved before --execute")
    database_url = os.getenv(args.database_url_env)
    if not database_url:
        raise ValueError(f"{args.database_url_env} is not configured")
    engine = create_engine(database_url, hide_parameters=True, pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        raise ValueError("M19D execution requires PostgreSQL; local fallback is forbidden")
    session_factory = sessionmaker(bind=engine)
    outcomes = []
    failed_count = 0
    with session_factory() as session:
        run = validate_remote_run(session)
        query_provider = GeminiEmbeddingProvider(
            model_name=run.model_id,
            dimension=run.dimension,
            task_type=run.query_task_type,
            vertex_ai=True,
        )
        retrieval = HybridRetrievalService(query_provider)
        if retrieval.config.configuration_hash != M19D_RETRIEVAL_CONFIG_HASH:
            raise ValueError("Runtime retrieval configuration differs from accepted M19C configuration")
        generator = VertexPilotGenerator(model=args.model)
        service = M19DPilotService(
            retrieval=retrieval,
            generator=generator,
            blueprint_id=blueprint.blueprint_id,
            blueprint_hash=blueprint_hash,
        )
        for row in blueprint.rows[: args.limit]:
            try:
                question, created = service.generate_row(session, row)
                outcomes.append(
                    {
                        "row_id": row.id,
                        "outcome": "GENERATED" if created else "ALREADY_EXISTS",
                        "question_id": question.id,
                        "question_status": question.status.value,
                        "quality_score": question.quality_score,
                        "provider_usage": {
                            key: question.metadata_json["provider_receipt"].get(key)
                            for key in ("input_tokens", "output_tokens", "total_tokens", "latency_ms")
                        },
                    }
                )
            except Exception as exc:
                session.rollback()
                failed_count += 1
                outcomes.append({"row_id": row.id, "outcome": "FAILED", "reason": str(exc)})
            partial = {
                **preflight,
                "status": "RUNNING",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "git_commit": git_commit(),
                "cohort_id": M19D_COHORT_ID,
                "outcomes": outcomes,
            }
            write_report(args.output, partial)
            if failed_count * 3 > len(outcomes):
                partial["status"] = "STOPPED_FAILURE_RATE"
                write_report(args.output, partial)
                return partial
        persisted_count = session.query(Question).filter_by(origin_cohort=M19D_COHORT_ID).count()
    engine.dispose()
    final = {
        **preflight,
        "status": "EXECUTION_COMPLETE",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "cohort_id": M19D_COHORT_ID,
        "persisted_cohort_count": persisted_count,
        "outcomes": outcomes,
    }
    write_report(args.output, final)
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blueprint", type=Path, default=DEFAULT_BLUEPRINT)
    parser.add_argument("--acceptance-report", type=Path, default=DEFAULT_ACCEPTANCE_REPORT)
    parser.add_argument("--database-url-env", default="REMOTE_DATABASE_URL")
    parser.add_argument("--embedding-run-id", default=M19D_EMBEDDING_RUN_ID)
    parser.add_argument("--model", default=os.getenv("M19D_VERTEX_MODEL", "gemini-2.5-flash"))
    parser.add_argument("--limit", type=int, default=50, choices=range(1, 51), metavar="1..50")
    parser.add_argument("--input-cost-per-million", type=float)
    parser.add_argument("--output-cost-per-million", type=float)
    parser.add_argument("--embedding-cost-per-thousand", type=float)
    parser.add_argument("--approved-cost-cap", type=float)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    if args.embedding_run_id != M19D_EMBEDDING_RUN_ID:
        parser.error("M19D is pinned to the accepted embedding run ID")
    blueprint, blueprint_hash = load_blueprint(args.blueprint)
    acceptance = validate_acceptance_report(args.acceptance_report, blueprint)
    preflight = build_preflight(args, blueprint, blueprint_hash, acceptance)
    if not args.execute:
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return
    if None in (
        args.input_cost_per_million,
        args.output_cost_per_million,
        args.embedding_cost_per_thousand,
        args.approved_cost_cap,
    ):
        parser.error("--execute requires current pricing inputs and --approved-cost-cap")
    estimate = preflight["usage_estimate"]["estimated_total_cost"]
    if estimate is None or estimate > args.approved_cost_cap:
        parser.error("Conservative estimated cost exceeds the approved cost cap")
    result = execute(args, blueprint, blueprint_hash, preflight)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
