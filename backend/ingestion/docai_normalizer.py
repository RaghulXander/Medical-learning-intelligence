"""
backend/ingestion/docai_normalizer.py

Structured JSON Downloader and Normalizer for GCP Document AI.
Transforms hierarchical Document AI layout trees into clean, typed medical domain blocks
while guaranteeing zero loss of 1-based original page and document provenance.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.ingestion.document_registry import SliceManifest

logger = logging.getLogger(__name__)

DEFAULT_NORMALIZED_DIR = Path("data/processed/reference_documents/normalized")


def sanitize_extracted_text(text: Optional[str]) -> str:
    """Normalizes unicode and whitespace in extracted OCR/layout text."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in text.splitlines()]
    return "\n".join(l for l in lines if l).strip()


@dataclass
class NormalizedBlock:
    """Structured, provenance-backed content block extracted from a reference document."""
    block_id: str
    block_type: str  # HEADING_1, HEADING_2, HEADING_3, PARAGRAPH, TABLE, LIST_ITEM, FIGURE_CAPTION, RUNNING_HEADER, RUNNING_FOOTER
    content: str
    confidence: float
    original_doc_id: str
    original_doc_title: str
    original_page_number: int  # 1-based physical page in PDF
    slice_id: str
    slice_page_number: int  # 1-based local page in slice
    content_hash: str
    pdf_page: int = 1
    textbook_page: Optional[int] = None
    document_id: str = ""
    source: str = ""
    chunk_id: str = ""
    column_index: Optional[int] = None  # 0: left column, 1: right column, None: full-width
    is_header_or_footer: bool = False
    bounding_box: Optional[Dict[str, float]] = None
    text_anchor: Optional[Dict[str, int]] = None
    table_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.pdf_page:
            self.pdf_page = self.original_page_number
        if not self.document_id:
            self.document_id = self.original_doc_id
        if not self.source:
            self.source = self.original_doc_title
        if not self.chunk_id:
            self.chunk_id = self.slice_id

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> NormalizedBlock:
        return cls(**data)


@dataclass
class NormalizedDocumentSlice:
    """Complete collection of normalized blocks from a parsed document slice."""
    slice_id: str
    parent_doc_id: str
    parent_doc_title: str
    start_page_1based: int
    end_page_1based: int
    total_blocks: int
    blocks: List[NormalizedBlock]
    markdown_text: str
    summary_stats: Dict[str, Any] = field(default_factory=dict)
    processing_mode: str = "UNSPECIFIED"
    processor_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slice_id": self.slice_id,
            "parent_doc_id": self.parent_doc_id,
            "parent_doc_title": self.parent_doc_title,
            "start_page_1based": self.start_page_1based,
            "end_page_1based": self.end_page_1based,
            "total_blocks": self.total_blocks,
            "blocks": [b.to_dict() for b in self.blocks],
            "markdown_text": self.markdown_text,
            "summary_stats": self.summary_stats,
            "processing_mode": self.processing_mode,
            "processor_metadata": self.processor_metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> NormalizedDocumentSlice:
        data = dict(data)
        blocks_raw = data.pop("blocks", [])
        blocks = [NormalizedBlock.from_dict(b) for b in blocks_raw]
        return cls(blocks=blocks, **data)


class DocumentAINormalizer:
    """Normalizes raw Google Cloud Document AI JSON into structured domain blocks."""

    def __init__(self, normalized_dir: Path | str = DEFAULT_NORMALIZED_DIR):
        self.normalized_dir = Path(normalized_dir)
        self.normalized_dir.mkdir(parents=True, exist_ok=True)

    def normalize(
        self,
        raw_docai_data: Dict[str, Any],
        manifest: SliceManifest,
    ) -> NormalizedDocumentSlice:
        """Transforms raw Document AI layout JSON into a NormalizedDocumentSlice."""
        full_text = raw_docai_data.get("text", "")
        pages = raw_docai_data.get("pages", [])
        processor_metadata = dict(raw_docai_data.get("_docedge", {}))
        processing_mode = processor_metadata.get("processing_mode", "UNSPECIFIED")
        normalized_blocks: List[NormalizedBlock] = []
        md_sections: List[str] = []
        processed_pages: List[int] = []

        # Check if response is from Document AI Layout Parser (documentLayout format)
        if "documentLayout" in raw_docai_data:
            normalized_blocks = self._normalize_document_layout(
                doc_layout=raw_docai_data["documentLayout"],
                manifest=manifest,
                processing_metadata=processor_metadata,
            )
            processed_pages.extend(
                self._document_layout_processed_pages(
                    raw_docai_data["documentLayout"], manifest
                )
            )
            for b in normalized_blocks:
                if "HEADING" in b.block_type:
                    md_sections.append(f"## {b.content}\n")
                elif b.block_type == "TABLE":
                    md_sections.append(f"{b.content}\n")
                else:
                    md_sections.append(f"{b.content}\n")
        else:
            full_text = raw_docai_data.get("text", "")
            pages = raw_docai_data.get("pages", [])

            for page_data in pages:
                slice_page_num = page_data.get("pageNumber", 1)

                # Map slice page index to original 1-based book page
                original_page_num = manifest.page_offset_map.get(
                    slice_page_num,
                    manifest.start_page_1based + slice_page_num - 1,
                )
                processed_pages.append(original_page_num)

                # 1. Process Heading/Block Elements
                for block_elem in page_data.get("blocks", []):
                    block = self._parse_layout_element(
                        elem_dict=block_elem,
                        full_text=full_text,
                        default_type="HEADING_2",
                        manifest=manifest,
                        slice_page_num=slice_page_num,
                        original_page_num=original_page_num,
                        processing_metadata=processor_metadata,
                    )
                    if block:
                        normalized_blocks.append(block)
                        md_sections.append(f"## {block.content}\n")

                # 2. Process Paragraphs
                for para_elem in page_data.get("paragraphs", []):
                    block = self._parse_layout_element(
                        elem_dict=para_elem,
                        full_text=full_text,
                        default_type="PARAGRAPH",
                        manifest=manifest,
                        slice_page_num=slice_page_num,
                        original_page_num=original_page_num,
                        processing_metadata=processor_metadata,
                    )
                    if block:
                        normalized_blocks.append(block)
                        md_sections.append(f"{block.content}\n")

                # 3. Process Tables
                for table_idx, table_elem in enumerate(page_data.get("tables", [])):
                    table_block = self._parse_table_element(
                        table_elem=table_elem,
                        full_text=full_text,
                        manifest=manifest,
                        slice_page_num=slice_page_num,
                        original_page_num=original_page_num,
                        table_idx=table_idx,
                        processing_metadata=processor_metadata,
                    )
                    if table_block:
                        normalized_blocks.append(table_block)
                        md_sections.append(f"{table_block.content}\n")

        # Compute summary statistics
        heading_count = sum(1 for b in normalized_blocks if "HEADING" in b.block_type)
        paragraph_count = sum(1 for b in normalized_blocks if b.block_type == "PARAGRAPH")
        table_count = sum(1 for b in normalized_blocks if b.block_type == "TABLE")
        avg_confidence = (
            sum(b.confidence for b in normalized_blocks) / len(normalized_blocks)
            if normalized_blocks
            else 1.0
        )

        composite_markdown = "\n\n".join(md_sections)
        summary_stats = {
            "total_blocks": len(normalized_blocks),
            "heading_count": heading_count,
            "paragraph_count": paragraph_count,
            "table_count": table_count,
            "average_confidence": round(avg_confidence, 4),
            "start_page_1based": manifest.start_page_1based,
            "end_page_1based": manifest.end_page_1based,
            "original_pages_covered": sorted(
                list(set(b.original_page_number for b in normalized_blocks))
            ),
            "processed_pages": sorted(set(processed_pages)),
            "processing_mode": processing_mode,
        }

        normalized_doc = NormalizedDocumentSlice(
            slice_id=manifest.slice_id,
            parent_doc_id=manifest.parent_doc_id,
            parent_doc_title=manifest.parent_doc_title,
            start_page_1based=manifest.start_page_1based,
            end_page_1based=manifest.end_page_1based,
            total_blocks=len(normalized_blocks),
            blocks=normalized_blocks,
            markdown_text=composite_markdown,
            summary_stats=summary_stats,
            processing_mode=processing_mode,
            processor_metadata=processor_metadata,
        )

        # Save to disk
        out_path = self.normalized_dir / f"{manifest.slice_id}_normalized.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(normalized_doc.to_dict(), f, indent=2, ensure_ascii=False)

        return normalized_doc

    def _parse_layout_element(
        self,
        elem_dict: Dict[str, Any],
        full_text: str,
        default_type: str,
        manifest: SliceManifest,
        slice_page_num: int,
        original_page_num: int,
        processing_metadata: Dict[str, Any],
    ) -> Optional[NormalizedBlock]:
        """Extracts text, confidence, and bounding box for a layout block."""
        layout = elem_dict.get("layout", {})
        text_anchor = layout.get("textAnchor", {})
        confidence = float(layout.get("confidence", 0.90))

        text_content = self._extract_text_from_anchor(text_anchor, full_text)
        cleaned_text = sanitize_extracted_text(text_content)
        if not cleaned_text:
            return None

        # Determine type
        elem_type = elem_dict.get("type", "").lower()
        if "heading" in elem_type or default_type.startswith("HEADING"):
            block_type = "HEADING_2"
        elif "list" in elem_type:
            block_type = "LIST_ITEM"
        elif "caption" in elem_type:
            block_type = "FIGURE_CAPTION"
        else:
            block_type = default_type

        # Extract bounding box
        bbox = self._extract_bounding_box(layout)
        column_index = None
        is_header_or_footer = False

        if bbox:
            xmin = bbox.get("xmin", 0.0)
            xmax = bbox.get("xmax", 1.0)
            ymin = bbox.get("ymin", 0.0)
            ymax = bbox.get("ymax", 1.0)

            if xmax <= 0.55:
                column_index = 0  # Left column
            elif xmin >= 0.45:
                column_index = 1  # Right column

            if ymax <= 0.075:
                is_header_or_footer = True
                block_type = "RUNNING_HEADER"
            elif ymin >= 0.93:
                is_header_or_footer = True
                block_type = "RUNNING_FOOTER"

        # Extract anchor range
        anchor_dict = None
        segments = text_anchor.get("textSegments", [])
        if segments:
            anchor_dict = {
                "start": int(segments[0].get("startIndex", "0")),
                "end": int(segments[0].get("endIndex", "0")),
            }

        pdf_page = original_page_num
        textbook_page = manifest.pdf_to_textbook_map.get(
            pdf_page,
            pdf_page - manifest.textbook_page_offset if pdf_page > manifest.textbook_page_offset else None,
        )

        content_hash = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()
        block_id = f"{manifest.slice_id}_p{original_page_num:04d}_{content_hash[:8]}"

        return NormalizedBlock(
            block_id=block_id,
            block_type=block_type,
            content=cleaned_text,
            confidence=confidence,
            original_doc_id=manifest.parent_doc_id,
            original_doc_title=manifest.parent_doc_title,
            original_page_number=original_page_num,
            slice_id=manifest.slice_id,
            slice_page_number=slice_page_num,
            content_hash=content_hash,
            pdf_page=pdf_page,
            textbook_page=textbook_page,
            document_id=manifest.parent_doc_id,
            source=manifest.parent_doc_title,
            chunk_id=manifest.slice_id,
            column_index=column_index,
            is_header_or_footer=is_header_or_footer,
            bounding_box=bbox,
            text_anchor=anchor_dict,
            metadata=dict(processing_metadata),
        )

    def _parse_table_element(
        self,
        table_elem: Dict[str, Any],
        full_text: str,
        manifest: SliceManifest,
        slice_page_num: int,
        original_page_num: int,
        table_idx: int,
        processing_metadata: Dict[str, Any],
    ) -> Optional[NormalizedBlock]:
        """Extracts structured table grid and converts to Markdown."""
        layout = table_elem.get("layout", {})
        confidence = float(layout.get("confidence", 0.90))

        headers: List[str] = []
        for h_row in table_elem.get("headerRows", []):
            row_cells = []
            for cell in h_row.get("cells", []):
                c_anchor = cell.get("layout", {}).get("textAnchor", {})
                cell_text = self._extract_text_from_anchor(c_anchor, full_text)
                row_cells.append(sanitize_extracted_text(cell_text))
            if row_cells:
                headers = row_cells
                break

        body_rows: List[List[str]] = []
        for b_row in table_elem.get("bodyRows", []):
            row_cells = []
            for cell in b_row.get("cells", []):
                c_anchor = cell.get("layout", {}).get("textAnchor", {})
                cell_text = self._extract_text_from_anchor(c_anchor, full_text)
                row_cells.append(sanitize_extracted_text(cell_text))
            if row_cells:
                body_rows.append(row_cells)

        if not headers and not body_rows:
            return None

        # Build Markdown Table
        col_count = max(
            len(headers),
            max((len(r) for r in body_rows), default=0),
        )
        if not headers:
            headers = [f"Col {i+1}" for i in range(col_count)]

        while len(headers) < col_count:
            headers.append(f"Col {len(headers)+1}")

        md_lines = []
        md_lines.append("| " + " | ".join(headers) + " |")
        md_lines.append("| " + " | ".join(["---"] * col_count) + " |")
        for row in body_rows:
            padded = row + [""] * (col_count - len(row))
            md_lines.append("| " + " | ".join(padded) + " |")

        table_md = "\n".join(md_lines)
        content_hash = hashlib.sha256(table_md.encode("utf-8")).hexdigest()
        block_id = f"{manifest.slice_id}_p{original_page_num:04d}_tbl{table_idx}_{content_hash[:8]}"

        pdf_page = original_page_num
        textbook_page = manifest.pdf_to_textbook_map.get(
            pdf_page,
            pdf_page - manifest.textbook_page_offset if pdf_page > manifest.textbook_page_offset else None,
        )

        return NormalizedBlock(
            block_id=block_id,
            block_type="TABLE",
            content=table_md,
            confidence=confidence,
            original_doc_id=manifest.parent_doc_id,
            original_doc_title=manifest.parent_doc_title,
            original_page_number=original_page_num,
            slice_id=manifest.slice_id,
            slice_page_number=slice_page_num,
            content_hash=content_hash,
            pdf_page=pdf_page,
            textbook_page=textbook_page,
            document_id=manifest.parent_doc_id,
            source=manifest.parent_doc_title,
            chunk_id=manifest.slice_id,
            bounding_box=self._extract_bounding_box(layout),
            table_data={"headers": headers, "rows": body_rows},
            metadata=dict(processing_metadata),
        )

    def _extract_text_from_anchor(
        self, text_anchor: Dict[str, Any], full_text: str
    ) -> str:
        """Slices substring from full Document AI text using textSegments."""
        if "content" in text_anchor:
            return str(text_anchor["content"])

        segments = text_anchor.get("textSegments", [])
        if not segments:
            return ""

        extracted = []
        for seg in segments:
            try:
                start = int(seg.get("startIndex", "0"))
                end = int(seg.get("endIndex", str(len(full_text))))
                extracted.append(full_text[start:end])
            except (ValueError, IndexError):
                continue
        return "".join(extracted)

    def _extract_bounding_box(
        self, layout: Dict[str, Any]
    ) -> Optional[Dict[str, float]]:
        """Extracts normalized [ymin, xmin, ymax, xmax] rectangle from boundingPoly."""
        poly = layout.get("boundingPoly", {})
        vertices = poly.get("normalizedVertices", [])
        if not vertices:
            return None

        xs = [v.get("x", 0.0) for v in vertices if "x" in v]
        ys = [v.get("y", 0.0) for v in vertices if "y" in v]
        if not xs or not ys:
            return None

        return {
            "ymin": round(min(ys), 4),
            "xmin": round(min(xs), 4),
            "ymax": round(max(ys), 4),
            "xmax": round(max(xs), 4),
        }

    def _normalize_document_layout(
        self,
        doc_layout: Dict[str, Any],
        manifest: SliceManifest,
        processing_metadata: Dict[str, Any],
    ) -> List[NormalizedBlock]:
        """Recursively parses Google Cloud Layout Parser documentLayout blocks."""
        blocks: List[NormalizedBlock] = []

        def recurse_blocks(block_list: List[Dict[str, Any]]) -> None:
            for b in block_list:
                page_span = b.get("pageSpan", {})
                slice_page_num = page_span.get("pageStart", 1)
                original_page_num = manifest.page_offset_map.get(
                    slice_page_num, manifest.start_page_1based + slice_page_num - 1
                )
                pdf_page = original_page_num
                textbook_page = manifest.pdf_to_textbook_map.get(
                    pdf_page,
                    pdf_page - manifest.textbook_page_offset if pdf_page > manifest.textbook_page_offset else None,
                )

                # 1. Process Table Block
                table_block = b.get("tableBlock")
                if table_block:
                    headers: List[str] = []
                    for h_row in table_block.get("headerRows", []):
                        row_cells = [c.get("text", "").strip() for c in h_row.get("cells", [])]
                        if row_cells:
                            headers = row_cells
                            break

                    body_rows: List[List[str]] = []
                    for b_row in table_block.get("bodyRows", []):
                        row_cells = [c.get("text", "").strip() for c in b_row.get("cells", [])]
                        if row_cells:
                            body_rows.append(row_cells)

                    if headers or body_rows:
                        col_count = max(len(headers), max((len(r) for r in body_rows), default=0))
                        if not headers:
                            headers = [f"Col {i+1}" for i in range(col_count)]
                        while len(headers) < col_count:
                            headers.append(f"Col {len(headers)+1}")

                        md_lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * col_count) + " |"]
                        for row in body_rows:
                            padded = row + [""] * (col_count - len(row))
                            md_lines.append("| " + " | ".join(padded) + " |")

                        table_md = "\n".join(md_lines)
                        content_hash = hashlib.sha256(table_md.encode("utf-8")).hexdigest()

                        blocks.append(
                            NormalizedBlock(
                                block_id=f"{manifest.slice_id}_p{original_page_num:04d}_tbl_{b.get('blockId', '0')}",
                                block_type="TABLE",
                                content=table_md,
                                confidence=float(b.get("confidence", 0.0)),
                                original_doc_id=manifest.parent_doc_id,
                                original_doc_title=manifest.parent_doc_title,
                                original_page_number=original_page_num,
                                slice_id=manifest.slice_id,
                                slice_page_number=slice_page_num,
                                content_hash=content_hash,
                                pdf_page=pdf_page,
                                textbook_page=textbook_page,
                                document_id=manifest.parent_doc_id,
                                source=manifest.parent_doc_title,
                                chunk_id=manifest.slice_id,
                                table_data={"headers": headers, "rows": body_rows},
                                metadata=dict(processing_metadata),
                            )
                        )

                # 2. Process Text Block
                text_block = b.get("textBlock")
                if text_block:
                    raw_text = text_block.get("text", "")
                    cleaned_text = sanitize_extracted_text(raw_text)
                    gcp_type = text_block.get("type", "paragraph").lower()

                    is_hdr_ftr = False
                    if "header" in gcp_type:
                        block_type = "RUNNING_HEADER"
                        is_hdr_ftr = True
                    elif "footer" in gcp_type:
                        block_type = "RUNNING_FOOTER"
                        is_hdr_ftr = True
                    elif "heading" in gcp_type:
                        block_type = "HEADING_2"
                    else:
                        block_type = "PARAGRAPH"

                    if cleaned_text:
                        content_hash = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()
                        blocks.append(
                            NormalizedBlock(
                                block_id=f"{manifest.slice_id}_p{original_page_num:04d}_{b.get('blockId', '0')}_{content_hash[:8]}",
                                block_type=block_type,
                                content=cleaned_text,
                                confidence=float(b.get("confidence", 0.0)),
                                original_doc_id=manifest.parent_doc_id,
                                original_doc_title=manifest.parent_doc_title,
                                original_page_number=original_page_num,
                                slice_id=manifest.slice_id,
                                slice_page_number=slice_page_num,
                                content_hash=content_hash,
                                pdf_page=pdf_page,
                                textbook_page=textbook_page,
                                document_id=manifest.parent_doc_id,
                                source=manifest.parent_doc_title,
                                chunk_id=manifest.slice_id,
                                is_header_or_footer=is_hdr_ftr,
                                metadata=dict(processing_metadata),
                            )
                        )

                    # Recurse children if present
                    child_blocks = text_block.get("blocks", [])
                    if child_blocks:
                        recurse_blocks(child_blocks)

        recurse_blocks(doc_layout.get("blocks", []))
        return blocks

    def _document_layout_processed_pages(
        self,
        doc_layout: Dict[str, Any],
        manifest: SliceManifest,
    ) -> List[int]:
        """Collect page receipts explicitly represented by documentLayout blocks."""
        slice_pages: set[int] = set()

        def recurse(block_list: List[Dict[str, Any]]) -> None:
            for block in block_list:
                page_span = block.get("pageSpan", {})
                start = page_span.get("pageStart")
                end = page_span.get("pageEnd", start)
                if isinstance(start, int):
                    safe_end = end if isinstance(end, int) and end >= start else start
                    slice_pages.update(range(start, safe_end + 1))
                text_block = block.get("textBlock", {})
                recurse(text_block.get("blocks", []))

        recurse(doc_layout.get("blocks", []))
        return [
            manifest.page_offset_map.get(
                page,
                manifest.start_page_1based + page - 1,
            )
            for page in sorted(slice_pages)
        ]
