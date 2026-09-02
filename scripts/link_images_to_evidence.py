"""
scripts/link_images_to_evidence.py

Milestone 18C: Automated Pathology Image-to-Text Evidence Linkage Engine.
Links curated valid pathology images to authoritative document chunks in PostgreSQL (Neon)
using physical/printed page co-occurrence and figure caption regex matching.

Usage:
  # Dry-run audit:
  python scripts/link_images_to_evidence.py --dry-run

  # Link test batch of 20 images:
  python scripts/link_images_to_evidence.py --max-images 20

  # Link all 2,165 curated images into Neon PostgreSQL:
  python scripts/link_images_to_evidence.py
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("evidence_linker")

from database.db import get_engine, get_session_factory
from database.models import (
    DocumentChunk,
    ImageAsset,
    ImageOccurrence,
    ImageTextEvidenceLink,
    Source,
    SourceDocument,
)

VALID_MANIFEST_PATH = PROJECT_ROOT / "data" / "processed" / "images" / "valid_images_manifest.json"
LINK_REPORT_PATH = PROJECT_ROOT / "data" / "processed" / "images" / "image_evidence_links_report.json"


class ImageEvidenceLinker:
    """
    Connects curated image assets and their book occurrences to surrounding
    authoritative document chunks in the database.
    """

    def __init__(self, db_session, dry_run: bool = False):
        self.db = db_session
        self.dry_run = dry_run
        self.doc_map: Dict[str, str] = {}  # source_short_name -> source_document_id
        self.chunks_by_doc_page: Dict[Tuple[str, int], List[DocumentChunk]] = defaultdict(list)
        self.chunks_by_textbook_page: Dict[Tuple[str, int], List[DocumentChunk]] = defaultdict(list)
        self._load_reference_sources()

    def _load_reference_sources(self):
        """Loads and indexes source documents and chunks from the database."""
        logger.info("📚 Loading source documents and chunks from database...")
        docs = (
            self.db.query(SourceDocument, Source.short_name)
            .join(Source, SourceDocument.source_id == Source.id)
            .all()
        )
        for doc, short_name in docs:
            self.doc_map[short_name] = doc.id
            logger.info(f"   Mapped '{short_name}' -> Document ID {doc.id}")

        # Index all document chunks by (document_id, pdf_page)
        all_chunks = self.db.query(DocumentChunk).all()
        for chunk in all_chunks:
            if chunk.pdf_page:
                self.chunks_by_doc_page[(chunk.document_id, chunk.pdf_page)].append(chunk)
            if chunk.textbook_page:
                self.chunks_by_textbook_page[(chunk.document_id, chunk.textbook_page)].append(chunk)

        logger.info(f"   Indexed {len(all_chunks):,} document chunks across {len(self.doc_map)} reference documents.")

    def find_matching_chunks(
        self,
        document_id: str,
        pdf_page: Optional[int],
        textbook_page: Optional[int],
        fig_idx: Optional[int],
    ) -> List[Tuple[DocumentChunk, str, float]]:
        """
        Finds matching chunks for an image occurrence.
        Returns: List of (DocumentChunk, link_type, confidence)
        """
        candidates: List[Tuple[DocumentChunk, str, float]] = []
        seen_chunk_ids: Set[str] = set()

        # 1. Exact PDF Page matches
        if pdf_page:
            exact_chunks = self.chunks_by_doc_page.get((document_id, pdf_page), [])
            for c in exact_chunks:
                if c.id not in seen_chunk_ids:
                    # Check for explicit figure citation in content
                    link_type = "PAGE_CO_OCCURRENCE"
                    confidence = 0.90
                    if fig_idx is not None:
                        fig_patterns = [
                            rf"\bfig(?:ure)?\.?\s*{fig_idx}\b",
                            rf"\bfig(?:ure)?\.?\s*\d+[-.]?{fig_idx}\b",
                        ]
                        for pat in fig_patterns:
                            if re.search(pat, c.content, re.IGNORECASE):
                                link_type = "FIGURE_CITATION"
                                confidence = 0.98
                                break

                    candidates.append((c, link_type, confidence))
                    seen_chunk_ids.add(c.id)

        # 2. Exact Textbook Page matches (if different from pdf_page and not yet seen)
        if textbook_page:
            tb_chunks = self.chunks_by_textbook_page.get((document_id, textbook_page), [])
            for c in tb_chunks:
                if c.id not in seen_chunk_ids:
                    candidates.append((c, "PAGE_CO_OCCURRENCE", 0.88))
                    seen_chunk_ids.add(c.id)

        # 3. Adjacent Page fallback (±1 page) if no exact chunk found
        if not candidates and pdf_page:
            for adj_p in (pdf_page - 1, pdf_page + 1):
                adj_chunks = self.chunks_by_doc_page.get((document_id, adj_p), [])
                for c in adj_chunks:
                    if c.id not in seen_chunk_ids:
                        candidates.append((c, "ADJACENT_PAGE_CO_OCCURRENCE", 0.75))
                        seen_chunk_ids.add(c.id)

        return candidates

    def link_manifest(
        self,
        manifest_path: Path = VALID_MANIFEST_PATH,
        max_images: Optional[int] = None,
        batch_size: int = 50,
    ) -> Dict[str, Any]:
        """Processes the valid images manifest and creates linkage records."""
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        images = data.get("images", [])
        if max_images:
            images = images[:max_images]

        total_images = len(images)
        logger.info(f"🔗 Linking {total_images:,} valid images to textbook evidence (dry_run={self.dry_run})...")

        stats = {
            "total_images": total_images,
            "assets_created": 0,
            "occurrences_created": 0,
            "links_created": 0,
            "citation_links": 0,
            "page_links": 0,
            "adjacent_links": 0,
            "unlinked_images": 0,
        }

        # Cache existing image assets by sha256 to avoid duplicates
        existing_assets = {a.sha256: a for a in self.db.query(ImageAsset).all()}
        existing_occurrences = {
            (o.image_asset_id, o.source_document_id, o.pdf_page): o
            for o in self.db.query(ImageOccurrence).all()
        }
        existing_links = {
            (l.image_asset_id, l.document_chunk_id): l
            for l in self.db.query(ImageTextEvidenceLink).all()
        }

        pending_assets = []
        pending_occurrences = []
        pending_links = []

        for idx, img in enumerate(images, start=1):
            sha256 = img["sha256"]
            filename = img["filename"]
            source_short = img.get("source_short_name", "robbins_pathologic_basis_11th")
            pdf_page = img.get("pdf_page")
            textbook_page = img.get("textbook_page")
            fig_idx = img.get("figure_index")
            storage_uri = f"pathology/{source_short}/{filename}"

            doc_id = self.doc_map.get(source_short)
            if not doc_id:
                logger.warning(f"No source_document_id for {source_short} (image {filename})")
                stats["unlinked_images"] += 1
                continue

            # 1. ImageAsset record
            asset = existing_assets.get(sha256)
            if not asset:
                asset = ImageAsset(
                    id=str(uuid.uuid4()),
                    sha256=sha256,
                    pixel_hash=img.get("pixel_hash", sha256[:16]),
                    filename=filename,
                    storage_uri=storage_uri,
                    width=img.get("width", 0),
                    height=img.get("height", 0),
                    aspect_ratio=img.get("aspect_ratio", 0.0),
                    file_size_bytes=img.get("file_size_bytes", 0),
                    format="PNG",
                    triage_class=img.get("triage_class", "AUTO_KEEP_CANDIDATE"),
                    curation_status="CURATED_VALID",
                    rights_status="RESTRICTED_INTERNAL",
                    entropy=img.get("entropy", 0.0),
                    blank_score=img.get("blank_score", 0.0),
                    is_exact_duplicate=img.get("is_exact_duplicate", False),
                    metadata_json={
                        "duplicate_cluster_id": img.get("duplicate_cluster_id"),
                        "triage_reason": img.get("triage_reason"),
                        "source_short_name": source_short,
                    },
                )
                existing_assets[sha256] = asset
                pending_assets.append(asset)
                stats["assets_created"] += 1

            # 2. ImageOccurrence record
            occ_key = (asset.id, doc_id, pdf_page)
            occurrence = existing_occurrences.get(occ_key)
            if not occurrence:
                fig_label = f"Figure {fig_idx}" if fig_idx is not None else None
                occurrence = ImageOccurrence(
                    id=str(uuid.uuid4()),
                    image_asset_id=asset.id,
                    source_document_id=doc_id,
                    pdf_page=pdf_page,
                    textbook_page=textbook_page,
                    figure_index=fig_idx,
                    figure_label=fig_label,
                    extraction_id=img.get("extraction_id"),
                    is_canonical=img.get("is_canonical", True),
                    metadata_json={"filename": filename},
                )
                existing_occurrences[occ_key] = occurrence
                pending_occurrences.append(occurrence)
                stats["occurrences_created"] += 1

            # 3. Find matching chunks and create links
            matched_chunks = self.find_matching_chunks(
                document_id=doc_id,
                pdf_page=pdf_page,
                textbook_page=textbook_page,
                fig_idx=fig_idx,
            )

            if not matched_chunks:
                stats["unlinked_images"] += 1
            else:
                for chunk, link_type, confidence in matched_chunks:
                    link_key = (asset.id, chunk.id)
                    if link_key not in existing_links:
                        link = ImageTextEvidenceLink(
                            id=str(uuid.uuid4()),
                            image_asset_id=asset.id,
                            document_chunk_id=chunk.id,
                            link_type=link_type,
                            confidence=confidence,
                            verification_status="AI_SUGGESTED",
                            created_at=datetime.now(timezone.utc),
                        )
                        existing_links[link_key] = link
                        pending_links.append(link)
                        stats["links_created"] += 1

                        if link_type == "FIGURE_CITATION":
                            stats["citation_links"] += 1
                        elif link_type == "PAGE_CO_OCCURRENCE":
                            stats["page_links"] += 1
                        else:
                            stats["adjacent_links"] += 1

            # Periodic batch commit
            if not self.dry_run and idx % batch_size == 0:
                if pending_assets:
                    self.db.add_all(pending_assets)
                    pending_assets.clear()
                if pending_occurrences:
                    self.db.add_all(pending_occurrences)
                    pending_occurrences.clear()
                if pending_links:
                    self.db.add_all(pending_links)
                    pending_links.clear()
                self.db.commit()
                logger.info(f"   [{idx}/{total_images}] Committed batch (Assets: {stats['assets_created']:,}, Links: {stats['links_created']:,})")

        # Final flush
        if not self.dry_run:
            if pending_assets:
                self.db.add_all(pending_assets)
            if pending_occurrences:
                self.db.add_all(pending_occurrences)
            if pending_links:
                self.db.add_all(pending_links)
            self.db.commit()

        logger.info("\n=======================================================")
        logger.info(f"✅ Image Evidence Linkage Complete! (dry_run={self.dry_run})")
        logger.info(f"   Total Images Processed: {stats['total_images']:,}")
        logger.info(f"   Unique ImageAssets:     {stats['assets_created']:,}")
        logger.info(f"   ImageOccurrences:       {stats['occurrences_created']:,}")
        logger.info(f"   Total Evidence Links:   {stats['links_created']:,}")
        logger.info(f"     - Figure Citations:   {stats['citation_links']:,}")
        logger.info(f"     - Page Co-occurrences:{stats['page_links']:,}")
        logger.info(f"     - Adjacent Pages:     {stats['adjacent_links']:,}")
        logger.info(f"   Unlinked Images:        {stats['unlinked_images']:,}")

        # Save summary report
        LINK_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LINK_REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
        logger.info(f"📄 Summary report saved to {LINK_REPORT_PATH}")

        return stats


def main():
    parser = argparse.ArgumentParser(description="Link curated pathology images to document evidence chunks")
    parser.add_argument("--dry-run", action="store_true", help="Audit matches without committing to database")
    parser.add_argument("--max-images", type=int, help="Limit number of images to process")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch commit size")
    args = parser.parse_args()

    engine = get_engine()
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        linker = ImageEvidenceLinker(db_session=session, dry_run=args.dry_run)
        linker.link_manifest(max_images=args.max_images, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
