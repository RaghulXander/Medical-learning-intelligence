"""
backend/ingestion/medical_normalizer.py

Medical Normalization & Page-Level Evidence Block Builder.
The critical curation stage prior to vector embedding (pgvector) and MCQ evidence retrieval.

Performs:
1. Running header & footer artifact stripping (preventing text contamination)
2. Two-column reading order reconstruction (Left Column Top-to-Bottom -> Right Column Top-to-Bottom)
3. Dual-page provenance binding (pdf_page + textbook_page)
4. Structured table & figure caption association
5. Chapter & section context hierarchy resolution
6. Emits clean, cohesive PageEvidenceBlock artifacts ready for pgvector embedding.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.ingestion.docai_normalizer import (
    NormalizedBlock,
    NormalizedDocumentSlice,
)

logger = logging.getLogger(__name__)

DEFAULT_EVIDENCE_DIR = Path("data/processed/reference_documents/evidence_blocks")

# Common patterns of running headers/footers in scanned medical books
COMMON_HEADER_FOOTER_PATTERNS = [
    r"^(chapter|unit|section|part)\s+([0-9]+|[ivxlcdm]+)",
    r"^[0-9ivxlcdm]+\s+(chapter|unit|section|part)",
    r"^robbins\s+(and|&)\s+cotran",
    r"^sternberg('?s)?\s+diagnostic",
    r"^(vip\.)?persianss\.ir",
    r"^tahir99\s*-\s*unitedvrg",
    r"^algrawany",
    r"^\d{1,4}\s*$",  # Lone page numbers in running margins
]


def is_running_artifact(content: str) -> bool:
    """Checks if a text block is a repeated running header, footer, or watermark."""
    norm = content.strip().lower()
    if len(norm) < 4:
        # Lone digits or single characters
        if norm.isdigit():
            return True
    for pat in COMMON_HEADER_FOOTER_PATTERNS:
        if re.search(pat, norm, re.IGNORECASE):
            return True
    return False


@dataclass
class PageEvidenceBlock:
    """A clean, curated page-level evidence unit formatted for pgvector embeddings and MCQ grounding."""
    evidence_id: str
    document_id: str
    source: str
    pdf_page: int
    textbook_page: Optional[int]
    chunk_id: str
    chapter: Optional[str]
    section: Optional[str]
    content: str
    headings: List[str] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    figures: List[Dict[str, Any]] = field(default_factory=list)
    raw_block_count: int = 0
    word_count: int = 0
    character_count: int = 0
    content_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PageEvidenceBlock:
        return cls(**data)


class MedicalNormalizer:
    """Curates and transforms raw normalized slices into grounded page-level evidence blocks."""

    def __init__(self, evidence_dir: Path | str = DEFAULT_EVIDENCE_DIR):
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def normalize_slice(
        self, normalized_slice: NormalizedDocumentSlice
    ) -> List[PageEvidenceBlock]:
        """
        Transforms a NormalizedDocumentSlice into clean, ordered, page-level evidence blocks.
        """
        # Group blocks by physical PDF page
        page_groups: Dict[int, List[NormalizedBlock]] = {}
        for b in normalized_slice.blocks:
            page_num = b.pdf_page or b.original_page_number
            page_groups.setdefault(page_num, []).append(b)

        evidence_blocks: List[PageEvidenceBlock] = []
        current_chapter: Optional[str] = None
        current_section: Optional[str] = None

        for pdf_page in sorted(page_groups.keys()):
            raw_page_blocks = page_groups[pdf_page]
            textbook_page = None
            for b in raw_page_blocks:
                if b.textbook_page is not None:
                    textbook_page = b.textbook_page
                    break

            # 1. Filter out running headers, footers, and OCR watermarks
            filtered_blocks: List[NormalizedBlock] = []
            for b in raw_page_blocks:
                if b.is_header_or_footer or is_running_artifact(b.content):
                    # Check if it defines a chapter heading before discarding
                    if "chapter" in b.content.lower() and len(b.content) < 100:
                        current_chapter = b.content.strip()
                    continue
                filtered_blocks.append(b)

            if not filtered_blocks:
                continue

            # 2. Reconstruct Two-Column Reading Order
            ordered_blocks = self._order_page_blocks(filtered_blocks)

            # 3. Assemble clean page content, tracking active headings & tables
            page_headings: List[str] = []
            page_tables: List[Dict[str, Any]] = []
            page_figures: List[Dict[str, Any]] = []
            content_paragraphs: List[str] = []

            for b in ordered_blocks:
                if "HEADING" in b.block_type:
                    page_headings.append(b.content)
                    if "chapter" in b.content.lower():
                        current_chapter = b.content
                    else:
                        current_section = b.content
                    content_paragraphs.append(f"\n### {b.content}\n")
                elif b.block_type == "TABLE":
                    if b.table_data:
                        page_tables.append(b.table_data)
                    content_paragraphs.append(f"\n{b.content}\n")
                elif b.block_type == "FIGURE_CAPTION":
                    page_figures.append({"caption": b.content, "bbox": b.bounding_box})
                    content_paragraphs.append(f"\n*Figure Caption: {b.content}*\n")
                else:
                    content_paragraphs.append(b.content)

            page_content = "\n\n".join(content_paragraphs).strip()
            word_count = len(page_content.split())
            char_count = len(page_content)
            content_hash = hashlib.sha256(page_content.encode("utf-8")).hexdigest()

            evidence_id = (
                f"{normalized_slice.parent_doc_id}_pdf{pdf_page:04d}_"
                f"tb{textbook_page or 0:04d}_{content_hash[:8]}"
            )

            evidence_block = PageEvidenceBlock(
                evidence_id=evidence_id,
                document_id=normalized_slice.parent_doc_id,
                source=normalized_slice.parent_doc_title,
                pdf_page=pdf_page,
                textbook_page=textbook_page,
                chunk_id=normalized_slice.slice_id,
                chapter=current_chapter,
                section=current_section,
                content=page_content,
                headings=page_headings,
                tables=page_tables,
                figures=page_figures,
                raw_block_count=len(ordered_blocks),
                word_count=word_count,
                character_count=char_count,
                content_hash=content_hash,
                metadata={
                    "start_page_1based": normalized_slice.start_page_1based,
                    "end_page_1based": normalized_slice.end_page_1based,
                },
            )
            evidence_blocks.append(evidence_block)

        # Save evidence blocks to disk
        out_file = self.evidence_dir / f"{normalized_slice.slice_id}_evidence.json"
        with open(out_file, "w", encoding="utf-8") as f_out:
            payload = {
                "slice_id": normalized_slice.slice_id,
                "document_id": normalized_slice.parent_doc_id,
                "source": normalized_slice.parent_doc_title,
                "evidence_count": len(evidence_blocks),
                "evidence_blocks": [eb.to_dict() for eb in evidence_blocks],
            }
            json.dump(payload, f_out, indent=2, ensure_ascii=False)

        return evidence_blocks

    def _order_page_blocks(
        self, blocks: List[NormalizedBlock]
    ) -> List[NormalizedBlock]:
        """
        Orders blocks on a page to respect two-column reading flow:
        - Full-width spans (headings, banners) appear in top-to-bottom order.
        - Left column blocks (col=0) are read top-to-bottom.
        - Right column blocks (col=1) are read top-to-bottom.
        """
        # If no bounding box information is available, retain original sequential order
        if not all(b.bounding_box for b in blocks):
            return blocks

        # Group into full-width, left column, and right column
        full_width: List[Tuple[float, NormalizedBlock]] = []
        left_col: List[Tuple[float, NormalizedBlock]] = []
        right_col: List[Tuple[float, NormalizedBlock]] = []

        for b in blocks:
            bbox = b.bounding_box or {}
            ymin = bbox.get("ymin", 0.0)
            if b.column_index == 0:
                left_col.append((ymin, b))
            elif b.column_index == 1:
                right_col.append((ymin, b))
            else:
                full_width.append((ymin, b))

        # Sort each partition by vertical position (ymin)
        full_width.sort(key=lambda x: x[0])
        left_col.sort(key=lambda x: x[0])
        right_col.sort(key=lambda x: x[0])

        # If there is a two-column distribution on the page, sequence left before right
        if left_col and right_col:
            ordered: List[NormalizedBlock] = []
            # Prepend top full-width headings (e.g. ymin < 0.25)
            for ymin, b in full_width:
                if ymin < 0.25:
                    ordered.append(b)

            # Add left column then right column
            ordered.extend(b for _, b in left_col)
            ordered.extend(b for _, b in right_col)

            # Append bottom full-width blocks
            for ymin, b in full_width:
                if ymin >= 0.25:
                    ordered.append(b)

            return ordered

        # Single column fallback: sort purely by vertical ymin
        all_sorted = sorted(
            blocks, key=lambda b: (b.bounding_box or {}).get("ymin", 0.0)
        )
        return all_sorted
