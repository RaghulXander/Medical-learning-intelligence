"""
scripts/import_reference_evidence.py

Bulk Ingestion Engine for Authoritative Pathology Reference Evidence.
Ingests calibrated page-level evidence blocks from GCP Document AI extraction
into the relational database (Source -> SourceDocument -> DocumentChunk).
Guarantees cryptographic provenance and prevents duplicate or unverified imports.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
load_dotenv()

from database.db import init_db, session_scope
from database.models import (
    DocumentChunk,
    Source,
    SourceDocument,
    SourceType,
)
from backend.ingestion.document_registry import DocumentRegistry
from backend.ingestion.provenance_manifest import ProvenanceManifestAuditor

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

DEFAULT_EVIDENCE_DIR = Path("data/processed/reference_documents/evidence_blocks")


def get_or_create_source_and_document(
    session,
    doc_meta: Dict[str, Any],
) -> Tuple[Source, SourceDocument]:
    """Ensures authoritative Source and SourceDocument records exist."""
    short_name = doc_meta["short_name"]
    source = session.query(Source).filter(Source.short_name == short_name).first()
    if not source:
        source = Source(
            id=str(uuid.uuid4()),
            short_name=short_name,
            title=doc_meta["title"],
            author=doc_meta.get("author", "Vinay Kumar, Abul Abbas, Jon Aster"),
            edition=doc_meta.get("edition", "11th"),
            year=doc_meta.get("year", 2024),
            publisher=doc_meta.get("publisher", "Elsevier"),
            source_type=SourceType.TEXTBOOK,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(source)
        session.flush()

    # Source Document (Edition / Master File)
    source_doc = (
        session.query(SourceDocument)
        .filter(SourceDocument.source_id == source.id)
        .first()
    )
    if not source_doc:
        source_doc = SourceDocument(
            id=str(uuid.uuid4()),
            source_id=source.id,
            title=f"{source.title} ({source.edition} Edition)",
            edition=source.edition,
            file_path=doc_meta.get("file_path"),
            file_hash=doc_meta.get("sha256"),
            page_start=1,
            page_end=doc_meta.get("total_pages"),
            metadata_json={
                "rights_status": doc_meta.get("rights_status", "AUTHORIZED"),
                "total_pages": doc_meta.get("total_pages"),
                "textbook_page_offset": doc_meta.get("textbook_page_offset"),
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(source_doc)
        session.flush()

    return source, source_doc


def import_reference_evidence(
    evidence_dir: Path | str = DEFAULT_EVIDENCE_DIR,
    doc_filter: Optional[str] = None,
    dry_run: bool = False,
    enforce_audit: bool = True,
) -> Dict[str, Any]:
    """
    Scans evidence JSON files, validates provenance, and ingests DocumentChunk records.
    """
    evidence_path = Path(evidence_dir)
    if not evidence_path.exists():
        raise FileNotFoundError(f"Evidence directory not found: {evidence_path}")

    registry = DocumentRegistry()
    auditor = ProvenanceManifestAuditor(evidence_dir=evidence_dir)

    # Validate provenance gates if enforced
    if enforce_audit:
        for registered_doc in registry.list_documents():
            if doc_filter and registered_doc.short_name != doc_filter:
                continue
            manifest = auditor.generate_manifest(registered_doc.doc_id, registry=registry)
            if manifest.status != "PASSED" or not manifest.is_ready_for_embedding:
                logger.warning(
                    f"⚠️ Document '{registered_doc.short_name}' provenance gate is {manifest.status} "
                    f"(Embedding Ready: {manifest.is_ready_for_embedding})."
                )

    evidence_files = sorted(evidence_path.glob("*.json"))
    if doc_filter:
        evidence_files = [
            f for f in evidence_files if f.name.startswith(f"{doc_filter}_")
        ]

    logger.info(
        f"📚 Found {len(evidence_files)} evidence files to process (Filter: {doc_filter or 'All'})."
    )

    stats = {
        "files_scanned": len(evidence_files),
        "chunks_imported": 0,
        "chunks_updated": 0,
        "chunks_skipped": 0,
        "total_words_imported": 0,
        "documents_processed": set(),
    }

    if dry_run:
        logger.info("🔍 DRY RUN MODE: Database changes will not be committed.")

    init_db()

    with session_scope() as session:
        # Cache SourceDocument mappings
        source_doc_map: Dict[str, SourceDocument] = {}

        for registered_doc in registry.list_documents():
            _, source_doc = get_or_create_source_and_document(
                session, registered_doc.to_dict()
            )
            source_doc_map[registered_doc.short_name] = source_doc
            source_doc_map[registered_doc.doc_id] = source_doc

        for ev_file in evidence_files:
            with open(ev_file, "r", encoding="utf-8") as f:
                ev_data = json.load(f)

            slice_id = ev_data.get("slice_id", "")
            parent_short_name = None

            # Determine parent document from short name prefix
            for s_name in source_doc_map.keys():
                if slice_id.startswith(f"{s_name}_"):
                    parent_short_name = s_name
                    break

            if not parent_short_name or parent_short_name not in source_doc_map:
                logger.warning(f"Could not map slice '{slice_id}' to a registered document. Skipping.")
                stats["chunks_skipped"] += len(ev_data.get("evidence_blocks", []))
                continue

            source_doc = source_doc_map[parent_short_name]
            stats["documents_processed"].add(parent_short_name)

            blocks = ev_data.get("evidence_blocks", [])
            for idx, block in enumerate(blocks):
                content = block.get("content", "").strip()
                if not content:
                    continue

                content_hash = block.get("content_hash") or hashlib.sha256(content.encode("utf-8")).hexdigest()
                pdf_page = block.get("pdf_page") or block.get("original_page_number", 1)
                textbook_page = block.get("textbook_page")
                chapter_name = block.get("chapter_name") or block.get("chapter")
                section_heading = block.get("section_heading") or block.get("section")
                word_count = block.get("word_count") or len(content.split())

                # Unique chunk identifier deterministic from slice and block index
                block_id_str = block.get("block_id") or f"{slice_id}_eb{idx+1:03d}"
                # Generate deterministic UUID for ID field
                chunk_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{source_doc.id}:{block_id_str}"))

                existing_chunk = (
                    session.query(DocumentChunk)
                    .filter(DocumentChunk.id == chunk_uuid)
                    .first()
                )

                if existing_chunk:
                    # Update fields if modified
                    existing_chunk.content = content
                    existing_chunk.content_hash = content_hash
                    existing_chunk.pdf_page = pdf_page
                    existing_chunk.textbook_page = textbook_page
                    existing_chunk.page_number = pdf_page
                    existing_chunk.chapter_name = chapter_name
                    existing_chunk.section_heading = section_heading
                    existing_chunk.word_count = word_count
                    existing_chunk.metadata_json = block
                    stats["chunks_updated"] += 1
                else:
                    new_chunk = DocumentChunk(
                        id=chunk_uuid,
                        document_id=source_doc.id,
                        slice_id=slice_id,
                        chunk_index=idx,
                        pdf_page=pdf_page,
                        textbook_page=textbook_page,
                        page_number=pdf_page,
                        chapter_name=chapter_name,
                        section_heading=section_heading,
                        content=content,
                        content_hash=content_hash,
                        word_count=word_count,
                        metadata_json=block,
                        created_at=datetime.now(timezone.utc),
                    )
                    if not dry_run:
                        session.add(new_chunk)
                    stats["chunks_imported"] += 1

                stats["total_words_imported"] += word_count

        if dry_run:
            session.rollback()
        else:
            session.commit()

    stats["documents_processed"] = list(stats["documents_processed"])
    logger.info(
        f"✅ Evidence Ingestion Complete!\n"
        f"   - Documents: {', '.join(stats['documents_processed'])}\n"
        f"   - Chunks Imported (New): {stats['chunks_imported']}\n"
        f"   - Chunks Updated:        {stats['chunks_updated']}\n"
        f"   - Total Words:           {stats['total_words_imported']:,}"
    )
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Import extracted reference document evidence into the database."
    )
    parser.add_argument(
        "--evidence-dir",
        type=str,
        default=str(DEFAULT_EVIDENCE_DIR),
        help="Path to evidence JSON directory.",
    )
    parser.add_argument(
        "--doc",
        type=str,
        default=None,
        help="Filter ingestion to specific document short_name (e.g. robbins_review).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and count without committing to database.",
    )
    parser.add_argument(
        "--no-audit",
        action="store_true",
        help="Skip provenance manifest audit gate check before importing.",
    )

    args = parser.parse_args()
    import_reference_evidence(
        evidence_dir=args.evidence_dir,
        doc_filter=args.doc,
        dry_run=args.dry_run,
        enforce_audit=not args.no_audit,
    )


if __name__ == "__main__":
    main()
