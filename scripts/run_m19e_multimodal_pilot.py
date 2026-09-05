"""Read-only preflight for the Milestone 19E multimodal pilot.

This runner intentionally has no execute mode yet. Generation stays unavailable
until the curated 30-image allocation is frozen and the owner approves a priced
Vertex vision run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from backend.services.image_review_service import ImageReviewService


DEFAULT_BLUEPRINT = PROJECT_ROOT / "data/generation/blueprints/m19e_multimodal_pilot_v1.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blueprint", type=Path, default=DEFAULT_BLUEPRINT)
    parser.add_argument("--database-url-env", default="REMOTE_DATABASE_URL")
    args = parser.parse_args()

    blueprint = json.loads(args.blueprint.read_text(encoding="utf-8"))
    if blueprint.get("total_candidates") != 30 or sum(row["count"] for row in blueprint["cohorts"]) != 30:
        raise ValueError("M19E blueprint must contain exactly 30 candidate slots")
    database_url = os.getenv(args.database_url_env)
    if not database_url:
        raise ValueError(f"{args.database_url_env} is not configured")
    engine = create_engine(database_url, hide_parameters=True, pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        raise ValueError("M19E preflight requires the authoritative PostgreSQL catalog")
    with sessionmaker(bind=engine)() as session:
        readiness = ImageReviewService.pilot_readiness(session)
    report = {
        "mode": "READ_ONLY_PREFLIGHT",
        "blueprint_id": blueprint["blueprint_id"],
        "blueprint_status": blueprint["status"],
        **readiness,
        "will_call_vertex": False,
        "will_write_database": False,
        "next_gate": "Freeze 30 eligible image allocations, review complete prompts, then obtain explicit priced-run approval.",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if readiness["gate_open"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
