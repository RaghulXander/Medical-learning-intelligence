"""
backend/ingestion/pdf_splitter.py

PDF Splitting Engine with Strict 1-Based Original Page Offset Preservation.
Slices large medical textbooks into pilot chunks compliant with GCP Document AI
online processing limits (<= 15 pages) while preserving immutable parent provenance.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pypdf

from backend.ingestion.document_registry import (
    DocumentRegistry,
    RegisteredDocument,
    SliceManifest,
    compute_file_sha256,
)

logger = logging.getLogger(__name__)

DEFAULT_SLICES_DIR = Path("data/processed/reference_documents/slices")
MAX_ONLINE_PAGES = 15


class PDFSplitter:
    """Extracts page slices from reference PDFs while retaining exact page provenance."""

    def __init__(
        self,
        registry: Optional[DocumentRegistry] = None,
        slices_dir: Path | str = DEFAULT_SLICES_DIR,
    ):
        self.registry = registry or DocumentRegistry()
        self.slices_dir = Path(slices_dir)
        self.slices_dir.mkdir(parents=True, exist_ok=True)

    def split_slice(
        self,
        doc_id_or_short_name: str,
        start_page_1based: int,
        end_page_1based: int,
        slice_suffix: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SliceManifest:
        """
        Extracts a slice from a registered document and saves both the slice PDF
        and its accompanying SliceManifest.
        """
        doc = self.registry.get_document(doc_id_or_short_name)
        if not doc:
            raise KeyError(f"Document '{doc_id_or_short_name}' not found in registry.")

        if start_page_1based < 1:
            raise ValueError(f"start_page_1based must be >= 1, got {start_page_1based}")
        if end_page_1based > doc.total_pages:
            raise ValueError(
                f"end_page_1based ({end_page_1based}) exceeds total pages in document ({doc.total_pages})"
            )
        if start_page_1based > end_page_1based:
            raise ValueError(
                f"start_page_1based ({start_page_1based}) cannot exceed end_page_1based ({end_page_1based})"
            )

        page_count = end_page_1based - start_page_1based + 1

        # Format slice ID e.g. robbins_review_p0001_p0015
        start_str = f"p{start_page_1based:04d}"
        end_str = f"p{end_page_1based:04d}"
        slice_id = f"{doc.short_name}_{start_str}_{end_str}"
        if slice_suffix:
            slice_id = f"{slice_id}_{slice_suffix}"

        slice_filename = f"{slice_id}.pdf"
        slice_path = self.slices_dir / slice_filename
        manifest_path = self.slices_dir / f"{slice_id}_manifest.json"

        # Build 1-based page offset map: local slice page (1..N) -> physical PDF page
        page_offset_map: Dict[int, int] = {}
        pdf_to_textbook_map: Dict[int, Optional[int]] = {}

        for local_idx in range(1, page_count + 1):
            pdf_page = start_page_1based + local_idx - 1
            page_offset_map[local_idx] = pdf_page
            pdf_to_textbook_map[pdf_page] = doc.get_textbook_page(pdf_page)

        textbook_start_page = doc.get_textbook_page(start_page_1based)
        textbook_end_page = doc.get_textbook_page(end_page_1based)

        # Extract pages using pypdf
        reader = pypdf.PdfReader(doc.file_path)
        writer = pypdf.PdfWriter()

        for page_num in range(start_page_1based - 1, end_page_1based):
            writer.add_page(reader.pages[page_num])

        with open(slice_path, "wb") as f_out:
            writer.write(f_out)

        slice_sha256 = compute_file_sha256(slice_path)

        manifest = SliceManifest(
            slice_id=slice_id,
            parent_doc_id=doc.doc_id,
            parent_doc_title=doc.title,
            parent_sha256=doc.sha256,
            start_page_1based=start_page_1based,
            end_page_1based=end_page_1based,
            page_count=page_count,
            slice_file_path=str(slice_path.resolve()),
            slice_file_name=slice_filename,
            slice_sha256=slice_sha256,
            page_offset_map=page_offset_map,
            textbook_page_offset=doc.textbook_page_offset,
            textbook_start_page=textbook_start_page,
            textbook_end_page=textbook_end_page,
            pdf_to_textbook_map=pdf_to_textbook_map,
            metadata=metadata or {},
        )

        # Write manifest JSON alongside slice PDF
        with open(manifest_path, "w", encoding="utf-8") as f_mf:
            json.dump(manifest.to_dict(), f_mf, indent=2, ensure_ascii=False)

        # Register in central registry
        self.registry.register_slice(manifest)
        logger.info(
            f"Successfully created slice '{slice_id}' (pages {start_page_1based}..{end_page_1based}) from '{doc.short_name}'"
        )
        return manifest

    def create_pilot_chunks(
        self,
        doc_id_or_short_name: str,
        max_slices: int = 3,
        pages_per_slice: int = MAX_ONLINE_PAGES,
        start_offset_1based: int = 1,
    ) -> List[SliceManifest]:
        """
        Creates a sequential sequence of pilot slices for a document, each strictly <= pages_per_slice.
        """
        doc = self.registry.get_document(doc_id_or_short_name)
        if not doc:
            raise KeyError(f"Document '{doc_id_or_short_name}' not found.")

        slices: List[SliceManifest] = []
        curr_start = start_offset_1based

        for _ in range(max_slices):
            if curr_start > doc.total_pages:
                break
            curr_end = min(curr_start + pages_per_slice - 1, doc.total_pages)
            manifest = self.split_slice(
                doc_id_or_short_name=doc.doc_id,
                start_page_1based=curr_start,
                end_page_1based=curr_end,
                metadata={"pilot": True, "pages_per_slice": pages_per_slice},
            )
            slices.append(manifest)
            curr_start = curr_end + 1

        return slices
