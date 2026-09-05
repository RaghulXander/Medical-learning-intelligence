"""Build a metadata-only M19E shortlist using remote evidence and local pixels.

Dry-run is the default. ``--apply-tags`` updates only ImageAsset.metadata with
non-authoritative ranking metadata; it never changes curation or verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from backend.curation.image_ranker import RankInput, allocate_shortlist, rank_image
from database.models import DocumentChunk, ImageAsset, ImageOccurrence, ImageTextEvidenceLink, Source, SourceDocument


DEFAULT_OUTPUT = PROJECT_ROOT / "data/processed/images/m19e_pilot_shortlist.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_candidates(session) -> list[dict]:
    rows = session.execute(
        select(
            ImageAsset.id,
            ImageAsset.sha256,
            ImageAsset.filename,
            ImageAsset.width,
            ImageAsset.height,
            ImageAsset.file_size_bytes,
            ImageAsset.entropy,
            ImageAsset.blank_score,
            ImageAsset.aspect_ratio,
            ImageAsset.is_exact_duplicate,
            ImageAsset.triage_class,
            ImageOccurrence.id,
            ImageOccurrence.pdf_page,
            ImageOccurrence.textbook_page,
            Source.short_name,
            ImageTextEvidenceLink.id,
            ImageTextEvidenceLink.confidence,
            ImageTextEvidenceLink.link_type,
            DocumentChunk.content,
        )
        .join(ImageOccurrence, ImageOccurrence.image_asset_id == ImageAsset.id)
        .join(SourceDocument, SourceDocument.id == ImageOccurrence.source_document_id)
        .join(Source, Source.id == SourceDocument.source_id)
        .join(ImageTextEvidenceLink, ImageTextEvidenceLink.image_asset_id == ImageAsset.id)
        .join(DocumentChunk, DocumentChunk.id == ImageTextEvidenceLink.document_chunk_id)
        .where(
            DocumentChunk.document_id == ImageOccurrence.source_document_id,
            DocumentChunk.pdf_page == ImageOccurrence.pdf_page,
        )
    ).all()
    grouped: dict[tuple[str, str], dict] = {}
    evidence_parts: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in rows:
        key = (str(row[0]), str(row[11]))
        candidate = grouped.get(key)
        if candidate is None or float(row[16]) > candidate["link_confidence"]:
            grouped[key] = {
                "image_asset_id": str(row[0]), "sha256": row[1], "filename": row[2],
                "width": row[3], "height": row[4], "file_size_bytes": row[5],
                "entropy": row[6], "blank_score": row[7], "aspect_ratio": row[8],
                "is_exact_duplicate": row[9], "triage_class": row[10],
                "occurrence_id": str(row[11]), "pdf_page": row[12], "textbook_page": row[13],
                "source_short_name": row[14], "link_id": str(row[15]),
                "link_confidence": float(row[16]), "link_type": row[17],
            }
        evidence_parts[key].append(row[18] or "")
    candidates = []
    for key, row in grouped.items():
        ranked = rank_image(RankInput(
            width=row["width"], height=row["height"], file_size_bytes=row["file_size_bytes"],
            entropy=row["entropy"], blank_score=row["blank_score"], aspect_ratio=row["aspect_ratio"],
            is_exact_duplicate=row["is_exact_duplicate"], triage_class=row["triage_class"],
            link_confidence=row["link_confidence"], link_type=row["link_type"],
            has_exact_page_provenance=True, evidence_text="\n".join(evidence_parts[key]),
        ))
        candidates.append({
            **row, "priority_score": ranked.score,
            "suggested_utility_class": ranked.suggested_utility_class,
            "suggested_tags": list(ranked.tags), "ranking_signals": list(ranked.signals),
            "human_verification_required": True,
        })
    return candidates


def apply_tags(session, shortlist: list[dict]) -> None:
    session.query(ImageAsset).filter(
        ImageAsset.automated_rank_version == "m19e-rank-v1"
    ).update({ImageAsset.pilot_shortlisted: False}, synchronize_session=False)
    metadata_by_id = dict(session.execute(select(ImageAsset.id, ImageAsset.metadata_json)).all())
    for rank, row in enumerate(shortlist, start=1):
        metadata = dict(metadata_by_id.get(row["image_asset_id"]) or {})
        metadata["m19e_ranking"] = {
            "version": "m19e-rank-v1", "rank": rank, "priority_score": row["priority_score"],
            "shortlist_cohort": row["shortlist_cohort"],
            "suggested_utility_class": row["suggested_utility_class"],
            "suggested_tags": row["suggested_tags"], "occurrence_id": row["occurrence_id"],
            "link_id": row["link_id"], "verification_status": "AI_SUGGESTED",
        }
        session.query(ImageAsset).filter(ImageAsset.id == row["image_asset_id"]).update(
            {
                ImageAsset.metadata_json: metadata,
                ImageAsset.automated_rank_score: row["priority_score"],
                ImageAsset.automated_rank_version: "m19e-rank-v1",
                ImageAsset.automated_suggested_utility_class: row["suggested_utility_class"],
                ImageAsset.automated_tags: row["suggested_tags"],
                ImageAsset.pilot_shortlisted: True,
            },
            synchronize_session=False,
        )
    session.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url-env", default="REMOTE_DATABASE_URL")
    parser.add_argument("--image-dir", type=Path, help="Optional local image root; validates shortlist hashes")
    parser.add_argument("--limit", type=int, default=72)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--apply-tags", action="store_true")
    args = parser.parse_args()
    url = os.getenv(args.database_url_env)
    if not url:
        raise ValueError(f"{args.database_url_env} is not configured")
    engine = create_engine(url, hide_parameters=True, pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        raise ValueError("Authoritative PostgreSQL catalog is required")
    with sessionmaker(bind=engine)() as session:
        if not args.apply_tags:
            session.execute(text("SET TRANSACTION READ ONLY"))
        shortlist = allocate_shortlist(fetch_candidates(session), total=args.limit)
        if args.image_dir:
            for row in shortlist:
                path = args.image_dir / row["filename"]
                row["local_file_status"] = (
                    "HASH_VERIFIED" if path.is_file() and sha256_file(path) == row["sha256"]
                    else "MISSING_OR_HASH_MISMATCH"
                )
        if args.apply_tags:
            apply_tags(session, shortlist)
    safe_rows = [
        {key: value for key, value in row.items() if key not in {"sha256"}}
        for row in shortlist
    ]
    report = {
        "schema_version": "m19e-shortlist-v1", "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "APPLIED_TAGS" if args.apply_tags else "DRY_RUN", "candidate_count": len(safe_rows),
        "contains_source_text": False,
        "cohort_counts": dict(sorted(Counter(row["shortlist_cohort"] for row in safe_rows).items())),
        "source_counts": dict(sorted(Counter(row["source_short_name"] for row in safe_rows).items())),
        "rows": safe_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))
    print(f"Private shortlist written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
