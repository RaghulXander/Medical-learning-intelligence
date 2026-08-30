"""
backend/ingestion/provenance_manifest.py

Book-Level Provenance Manifest & Hard Quality Gate.
Enforces that a textbook is NEVER embedded or ingested into vector storage
if any physical pages are missing, slices failed, or page mappings are invalid.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from backend.ingestion.document_registry import DocumentRegistry, RegisteredDocument
from backend.ingestion.medical_normalizer import DEFAULT_EVIDENCE_DIR
from backend.ingestion.gcp_docai_client import LIVE_PROCESSING_MODE

logger = logging.getLogger(__name__)

DEFAULT_MANIFEST_DIR = Path("data/processed/reference_documents/provenance_manifests")
NORMALIZATION_VERSION = "1.2.0"


class ProvenanceGateError(Exception):
    """Raised when a book fails the Provenance QC Hard Gate and cannot proceed to embedding."""
    pass


@dataclass
class BookProvenanceManifest:
    """Immutable audit record validating complete coverage and provenance before embedding."""
    document_id: str
    short_name: str
    title: str
    sha256: str
    total_pdf_pages: int
    pages_per_chunk: int
    expected_chunks: int
    completed_chunks: int
    failed_chunks: List[str] = field(default_factory=list)
    missing_pages: List[int] = field(default_factory=list)
    duplicate_pages: List[int] = field(default_factory=list)
    ocr_anomalies: List[str] = field(default_factory=list)
    page_mapping_valid: bool = True
    normalization_version: str = NORMALIZATION_VERSION
    status: str = "INCOMPLETE"  # PASSED, FAILED, INCOMPLETE
    is_ready_for_embedding: bool = False
    verified_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    total_words: int = 0
    total_evidence_blocks: int = 0
    processing_modes: List[str] = field(default_factory=list)
    processor_version_ids: List[str] = field(default_factory=list)
    rights_verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BookProvenanceManifest:
        return cls(**data)

    def to_markdown(self) -> str:
        status_badge = "✅ PASSED (READY FOR EMBEDDING)" if self.is_ready_for_embedding else f"❌ {self.status} (EMBEDDING BLOCKED)"
        missing_summary = f"{len(self.missing_pages)} pages" if self.missing_pages else "0 (Full Coverage)"
        
        md = f"""# 🛡️ Book Provenance Manifest: {self.title}

**Status:** {status_badge}  
**Document ID:** `{self.document_id}`  
**Short Name:** `{self.short_name}`  
**SHA-256:** `{self.sha256}`  
**Audit Timestamp:** `{self.verified_at}`  
**Normalization Version:** `{self.normalization_version}`  

---

## 1. Chunk Coverage & Extraction Matrix

| Metric | Required / Expected | Actual / Extracted | Status |
|---|---|---|---|
| **Total Physical PDF Pages** | {self.total_pdf_pages} | {self.total_pdf_pages - len(self.missing_pages)} | {'✅ 100%' if not self.missing_pages else '❌ Incomplete'} |
| **Pages Per Chunk** | <= 15 | {self.pages_per_chunk} | ✅ OK |
| **Total Chunks** | {self.expected_chunks} | {self.completed_chunks} Completed | {'✅ Complete' if self.completed_chunks == self.expected_chunks else '⚠️ Partial'} |
| **Failed Chunks** | 0 | {len(self.failed_chunks)} | {'✅ None' if not self.failed_chunks else '❌ ' + str(len(self.failed_chunks))} |
| **Missing Pages** | 0 | {missing_summary} | {'✅ 0' if not self.missing_pages else '❌ Missing: ' + str(self.missing_pages[:10])} |
| **Duplicate Pages** | 0 | {len(self.duplicate_pages)} | {'✅ 0' if not self.duplicate_pages else '⚠️ Duplicates: ' + str(self.duplicate_pages)} |
| **Dual Page Calibration** | Valid | {self.page_mapping_valid} | {'✅ Verified' if self.page_mapping_valid else '❌ Invalid'} |
| **Processing Modes** | LIVE_DOCAI only | {', '.join(self.processing_modes) or 'None'} | {'✅ Verified' if self.processing_modes == [LIVE_PROCESSING_MODE] else '❌ Non-live/unknown output'} |
| **Processor Version** | One pinned version | {', '.join(self.processor_version_ids) or 'None'} | {'✅ Pinned' if len(self.processor_version_ids) == 1 else '❌ Missing/mixed'} |
| **Source Rights** | AUTHORIZED | {self.rights_verified} | {'✅ Attested' if self.rights_verified else '❌ Unverified'} |

---

## 2. Statistical Aggregations

- **Total Page-Level Evidence Blocks:** `{self.total_evidence_blocks:,}`
- **Total Normalized Word Count:** `{self.total_words:,}`
- **Embedding Gate Decision:** **{'ALLOWED' if self.is_ready_for_embedding else 'BLOCKED - HARD GATE PREVENTS EMBEDDING'}**

---

## 3. Anomalies & Quality Findings

"""
        if not self.ocr_anomalies and not self.missing_pages and not self.failed_chunks:
            md += "✅ **No blocking anomalies detected.** All physical pages have verified 1-to-1 page provenance.\n"
        else:
            if self.missing_pages:
                md += f"### ❌ Missing Pages ({len(self.missing_pages)} total):\n"
                md += f"Pages: `{self.missing_pages[:50]}`" + ("..." if len(self.missing_pages) > 50 else "") + "\n\n"
            if self.failed_chunks:
                md += f"### ❌ Failed Chunks ({len(self.failed_chunks)} total):\n"
                for fc in self.failed_chunks:
                    md += f"- `{fc}`\n"
                md += "\n"
            if self.ocr_anomalies:
                md += f"### ⚠️ OCR / Quality Anomalies ({len(self.ocr_anomalies)} total):\n"
                for anom in self.ocr_anomalies[:20]:
                    md += f"- {anom}\n"
        return md


class ProvenanceManifestAuditor:
    """Builds and enforces book-level provenance manifests before vector embedding."""

    def __init__(
        self,
        manifest_dir: Path | str = DEFAULT_MANIFEST_DIR,
        evidence_dir: Path | str = DEFAULT_EVIDENCE_DIR,
    ):
        self.manifest_dir = Path(manifest_dir)
        self.evidence_dir = Path(evidence_dir)
        self.manifest_dir.mkdir(parents=True, exist_ok=True)

    def generate_manifest(
        self,
        doc_id_or_short_name: str,
        registry: DocumentRegistry,
        pages_per_chunk: int = 15,
    ) -> BookProvenanceManifest:
        """
        Audits all processed slices and evidence blocks for a document,
        computing missing pages, failed chunks, and hard gate readiness.
        """
        doc = registry.get_document(doc_id_or_short_name)
        if not doc:
            raise ValueError(f"Document '{doc_id_or_short_name}' not found in registry.")

        total_pdf_pages = doc.total_pages
        expected_chunks = math.ceil(total_pdf_pages / pages_per_chunk)

        # Inspect all evidence blocks on disk for this document
        evidence_files = list(self.evidence_dir.glob(f"{doc.short_name}_*_evidence.json"))
        
        covered_pages: Set[int] = set()
        page_occurrence_count: Dict[int, int] = {}
        completed_chunk_ids: Set[str] = set()
        failed_chunks: List[str] = []
        ocr_anomalies: List[str] = []
        total_words = 0
        total_evidence_blocks = 0
        page_mapping_valid = True
        processing_modes: Set[str] = set()
        processor_ids: Set[str] = set()
        processor_version_ids: Set[str] = set()

        for ev_file in evidence_files:
            try:
                with open(ev_file, "r", encoding="utf-8") as f:
                    ev_data = json.load(f)
                
                slice_id = ev_data.get("slice_id", "")
                completed_chunk_ids.add(slice_id)
                blocks = ev_data.get("evidence_blocks", [])
                processing_mode = ev_data.get("processing_mode", "UNSPECIFIED")
                processing_modes.add(processing_mode)
                processor_id = ev_data.get("processor_metadata", {}).get(
                    "processor_id"
                )
                if processor_id:
                    processor_ids.add(str(processor_id))
                processor_version_id = ev_data.get("processor_metadata", {}).get(
                    "processor_version_id"
                )
                if processor_version_id:
                    processor_version_ids.add(str(processor_version_id))

                processed_pages = ev_data.get("processed_pages")
                if not isinstance(processed_pages, list):
                    # Backward compatibility for old artifacts. New artifacts must
                    # carry explicit page receipts so blank pages count as processed.
                    processed_pages = [b.get("pdf_page") for b in blocks]

                for pdf_p in processed_pages:
                    if isinstance(pdf_p, int):
                        covered_pages.add(pdf_p)
                        page_occurrence_count[pdf_p] = (
                            page_occurrence_count.get(pdf_p, 0) + 1
                        )

                for b in blocks:
                    pdf_p = b.get("pdf_page")
                    tb_p = b.get("textbook_page")
                    if pdf_p is not None:
                        # Validate textbook calibration consistency
                        expected_tb = doc.get_textbook_page(pdf_p)
                        if tb_p != expected_tb:
                            page_mapping_valid = False
                            ocr_anomalies.append(
                                f"Inconsistent textbook page for PDF page {pdf_p}: found {tb_p}, expected {expected_tb}"
                            )

                    total_words += b.get("word_count", 0)
                    total_evidence_blocks += 1

            except Exception as e:
                failed_chunks.append(f"{ev_file.name}: {str(e)}")

        # Calculate missing pages from 1 to total_pdf_pages
        expected_page_set = set(range(1, total_pdf_pages + 1))
        missing_pages = sorted(list(expected_page_set - covered_pages))
        
        # Calculate duplicate pages (pages extracted more than once across chunks)
        duplicate_pages = sorted([p for p, count in page_occurrence_count.items() if count > 1])

        completed_chunks = len(completed_chunk_ids)
        sorted_processing_modes = sorted(processing_modes)
        sorted_processor_version_ids = sorted(processor_version_ids)
        sorted_processor_ids = sorted(processor_ids)
        live_only = sorted_processing_modes == [LIVE_PROCESSING_MODE]
        processor_pinned = (len(sorted_processor_version_ids) == 1) or (
            len(sorted_processor_version_ids) == 0 and len(sorted_processor_ids) == 1
        )
        rights_verified = (
            doc.rights_status == "AUTHORIZED" and bool(doc.rights_basis)
        )

        if not live_only:
            ocr_anomalies.append(
                "Only LIVE_DOCAI artifacts may pass the embedding gate; found "
                f"{sorted_processing_modes or ['NONE']}"
            )
        if not rights_verified:
            ocr_anomalies.append(
                "Source rights are not attested; rights_status=AUTHORIZED and a rights basis are required"
            )
        if not processor_pinned:
            ocr_anomalies.append(
                "Exactly one Document AI processor or pinned version is required across the canonical run"
            )

        # Gate Evaluation Rules:
        # 1. 0 missing pages
        # 2. 0 failed chunks
        # 3. completed_chunks == expected_chunks
        # 4. page_mapping_valid is True
        if (
            len(missing_pages) == 0
            and len(failed_chunks) == 0
            and len(duplicate_pages) == 0
            and (completed_chunks >= expected_chunks or len(covered_pages) == total_pdf_pages)
            and page_mapping_valid
            and live_only
            and processor_pinned
            and rights_verified
        ):
            status = "PASSED"
            is_ready = True
        elif completed_chunks < expected_chunks or len(missing_pages) > 0:
            status = "INCOMPLETE"
            is_ready = False
        else:
            status = "FAILED"
            is_ready = False

        manifest = BookProvenanceManifest(
            document_id=doc.doc_id,
            short_name=doc.short_name,
            title=doc.title,
            sha256=doc.sha256,
            total_pdf_pages=total_pdf_pages,
            pages_per_chunk=pages_per_chunk,
            expected_chunks=expected_chunks,
            completed_chunks=completed_chunks,
            failed_chunks=failed_chunks,
            missing_pages=missing_pages,
            duplicate_pages=duplicate_pages,
            ocr_anomalies=ocr_anomalies,
            page_mapping_valid=page_mapping_valid,
            normalization_version=NORMALIZATION_VERSION,
            status=status,
            is_ready_for_embedding=is_ready,
            total_words=total_words,
            total_evidence_blocks=total_evidence_blocks,
            processing_modes=sorted_processing_modes,
            processor_version_ids=sorted_processor_version_ids,
            rights_verified=rights_verified,
            metadata={
                "textbook_page_offset": doc.textbook_page_offset,
                "version": doc.version,
            },
        )

        # Save JSON & Markdown to disk
        self.save_manifest(manifest)
        return manifest

    def save_manifest(self, manifest: BookProvenanceManifest) -> None:
        """Persists JSON and Markdown versions of the manifest."""
        json_path = self.manifest_dir / f"{manifest.short_name}_provenance_manifest.json"
        md_path = self.manifest_dir / f"{manifest.short_name}_provenance_manifest.md"

        with open(json_path, "w", encoding="utf-8") as f_json:
            json.dump(manifest.to_dict(), f_json, indent=2, ensure_ascii=False)

        with open(md_path, "w", encoding="utf-8") as f_md:
            f_md.write(manifest.to_markdown())

        logger.info(f"🛡️ Provenance Manifest saved: {json_path}")

    def enforce_embedding_gate(
        self,
        doc_id_or_short_name: str,
        registry: DocumentRegistry,
        pages_per_chunk: int = 15,
    ) -> BookProvenanceManifest:
        """
        Hard Gate: Audits document provenance.
        Raises ProvenanceGateError if any pages are missing, chunks failed, or mappings invalid.
        """
        manifest = self.generate_manifest(
            doc_id_or_short_name=doc_id_or_short_name,
            registry=registry,
            pages_per_chunk=pages_per_chunk,
        )

        if not manifest.is_ready_for_embedding:
            raise ProvenanceGateError(
                f"🛑 HARD GATE STOP: Cannot embed '{manifest.title}'. "
                f"Status: {manifest.status}. "
                f"Missing pages: {len(manifest.missing_pages)} / {manifest.total_pdf_pages}, "
                f"Completed chunks: {manifest.completed_chunks} / {manifest.expected_chunks}, "
                f"Failed chunks: {len(manifest.failed_chunks)}. "
                f"Refer to {self.manifest_dir / (manifest.short_name + '_provenance_manifest.md')} for details."
            )

        logger.info(f"✅ PROVENANCE HARD GATE PASSED: '{manifest.title}' is 100% complete and ready for pgvector embedding.")
        return manifest
