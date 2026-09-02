"""Preview, apply, or roll back deterministic ontology mapping suggestions."""

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

from backend.services.ontology.question_mapping_service import QuestionOntologyMappingService
from backend.domain.surgical_pathology_ontology import OntologyMappingReviewDecision
from database.db import get_default_db_url


def _engine():
    engine = create_engine(get_default_db_url(), hide_parameters=True)
    if engine.dialect.name != "postgresql":
        raise RuntimeError("The ontology mapping command requires configured PostgreSQL")
    with engine.connect():
        pass
    return engine


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scheme", default="SURGICAL-PATHOLOGY")
    parser.add_argument("--version", default="2026.08-draft.1")
    parser.add_argument("--subject", default="Pathology")
    parser.add_argument("--speciality")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--rollback-run-id")
    parser.add_argument("--review-mapping-id")
    parser.add_argument("--decision", choices=[item.value for item in OntologyMappingReviewDecision])
    parser.add_argument("--corrected-node-code")
    parser.add_argument("--actor", default="m14_mapping_rule")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    selected_modes = sum(bool(item) for item in (args.apply, args.rollback_run_id, args.review_mapping_id))
    if selected_modes > 1:
        parser.error("--apply, --rollback-run-id, and --review-mapping-id are mutually exclusive")
    if args.review_mapping_id and not args.decision:
        parser.error("--review-mapping-id requires --decision")
    if args.decision and not args.review_mapping_id:
        parser.error("--decision requires --review-mapping-id")

    session_factory = sessionmaker(bind=_engine())
    service = QuestionOntologyMappingService()
    with session_factory() as session:
        if args.review_mapping_id:
            reviewed = service.review(
                session,
                args.review_mapping_id,
                decision=OntologyMappingReviewDecision(args.decision),
                reviewer=args.actor,
                corrected_node_code=args.corrected_node_code,
            )
            session.commit()
            result = {
                "status": args.decision,
                "source_mapping_id": args.review_mapping_id,
                "reviewed_mapping_id": reviewed.id if reviewed else None,
            }
        elif args.rollback_run_id:
            count = service.rollback(session, args.rollback_run_id, actor=args.actor)
            session.commit()
            result = {"status": "ROLLED_BACK", "run_id": args.rollback_run_id, "deactivated": count}
        else:
            preview = service.preview(
                session,
                scheme_code=args.scheme,
                ontology_version=args.version,
                subject=args.subject or None,
                speciality=args.speciality,
                limit=args.limit,
            )
            result = {
                "status": "APPLIED" if args.apply else "PREVIEW",
                **preview.summary(),
                "candidates": [candidate.__dict__ for candidate in preview.candidates],
                "ambiguous": [item.__dict__ for item in preview.ambiguous],
            }
            if args.apply:
                run = service.apply(session, preview, actor=args.actor)
                session.commit()
                result["run_id"] = run.id

    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(json.dumps({"status": result["status"], "output": str(args.output)}))
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
