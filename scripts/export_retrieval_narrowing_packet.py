"""Export unresolved retrieval cases as a private prompt-narrowing review packet."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.retrieval_review_service import RetrievalReviewService
from database.models import RetrievalBenchmark, RetrievalBenchmarkCase


DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "reference_documents"
    / "review_packets"
    / "m19b_remaining_prompt_narrowing.txt"
)


def _format_evidence(item: dict) -> str:
    citation = ", ".join(
        part
        for part in (
            item.get("source_short_name"),
            f"edition {item['edition']}" if item.get("edition") else None,
            f"PDF page {item['pdf_page']}" if item.get("pdf_page") else None,
            f"textbook page {item['textbook_page']}" if item.get("textbook_page") else None,
            item.get("chapter_name"),
            item.get("section_heading"),
        )
        if part
    )
    return (
        f"CHUNK_ID: {item['id']}\n"
        f"CITATION: {citation}\n"
        f"CONTENT_HASH: {item['content_hash']}\n"
        f"EVIDENCE_TEXT:\n{item['content'].strip()}"
    )


def build_packet(session, slug: str) -> str:
    benchmark = session.query(RetrievalBenchmark).filter_by(slug=slug).one()
    cases = (
        session.query(RetrievalBenchmarkCase)
        .filter_by(benchmark_id=benchmark.id, verification_status="HUMAN_REVIEW")
        .order_by(RetrievalBenchmarkCase.case_key)
        .all()
    )
    lines = [
        "M19B RETRIEVAL PROMPT-NARROWING PACKET",
        f"Benchmark: {slug}",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"Cases: {len(cases)}",
        "",
        "INSTRUCTIONS FOR THE REVIEW MODEL",
        "Use only the supplied evidence text. For each case, determine whether the current prompt is fully answerable from that evidence.",
        "If it is only partially supported, rewrite it to the narrowest medically useful question directly answered by the evidence.",
        "Do not add facts, markers, diagnoses, page numbers, or citations not present in the evidence.",
        "If narrowing would make the question misleading or trivial, return REPLACE_EVIDENCE and provide concise corpus-search terms.",
        "If the subject is genuinely absent from the three-book corpus, return OUT_OF_CORPUS; otherwise do not use that decision.",
        "",
        "RETURN THIS FORMAT FOR EVERY CASE",
        "CASE_KEY: <unchanged>",
        "DECISION: KEEP | NARROW | REPLACE_EVIDENCE | OUT_OF_CORPUS",
        "REVISED_PROMPT: <question, or blank unless KEEP/NARROW>",
        "KEEP_CHUNK_IDS: <comma-separated supplied chunk IDs that directly support the revised prompt>",
        "CORPUS_SEARCH_TERMS: <only for REPLACE_EVIDENCE>",
        "RATIONALE: <one concise evidence-grounded sentence>",
        "",
    ]
    for index, case in enumerate(cases, start=1):
        detail = RetrievalReviewService.get_case(session, slug, case.id)
        lines.extend(
            [
                "=" * 100,
                f"CASE {index:02d} OF {len(cases)}",
                f"CASE_KEY: {case.case_key}",
                f"DOMAIN: {case.domain}",
                f"REVISION: {case.revision}",
                f"CURRENT_PROMPT: {case.query}",
                f"HUMAN_REVIEW_NOTES: {case.review_notes or '(none)'}",
                f"SELECTED_EVIDENCE_COUNT: {len(detail['evidence'])}",
                "",
            ]
        )
        if detail["evidence"]:
            for evidence_index, item in enumerate(detail["evidence"], start=1):
                lines.extend(
                    [
                        f"--- SELECTED EVIDENCE {evidence_index} ---",
                        _format_evidence(item),
                        "",
                    ]
                )
        else:
            lines.extend(["SELECTED EVIDENCE: (none)", ""])
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", default="m16a-retrieval-v1")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--database-url-env",
        default="DATABASE_URL",
        help="Environment-variable name containing the PostgreSQL URL (never pass the URL as a CLI argument).",
    )
    args = parser.parse_args()

    load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
    database_url = os.environ.get(args.database_url_env)
    if not database_url:
        parser.error(f"{args.database_url_env} is not configured")

    engine = create_engine(database_url, hide_parameters=True, pool_pre_ping=True)
    try:
        with sessionmaker(bind=engine)() as session:
            packet = build_packet(session, args.slug)
    finally:
        engine.dispose()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(packet, encoding="utf-8")
    case_count = packet.count("\nCASE_KEY:") - 1
    print(f"Exported {case_count} unresolved cases to {args.output}")
    print("This file contains private derived textbook content and must not be committed.")


if __name__ == "__main__":
    main()
