"""
backend/ingestion/quality_report.py

Extraction Quality and Provenance Audit Engine.
Evaluates OCR/layout confidence, structural element distribution, character/word density,
and verifies source/page provenance. It does not claim medical extraction accuracy;
that requires a human-reviewed ground-truth sample.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.ingestion.docai_normalizer import NormalizedDocumentSlice
from backend.ingestion.document_registry import DocumentRegistry
from backend.ingestion.gcp_docai_client import LIVE_PROCESSING_MODE

logger = logging.getLogger(__name__)

DEFAULT_REPORTS_DIR = Path("data/processed/reference_documents/reports")


@dataclass
class QualityReport:
    """Audit report of extraction quality and provenance retention."""
    report_id: str
    slice_id: str
    parent_doc_id: str
    parent_doc_title: str
    start_page_1based: int
    end_page_1based: int
    page_count: int
    total_blocks: int
    total_words: int
    total_characters: int
    structure_counts: Dict[str, int]
    average_confidence: Optional[float]
    low_confidence_block_count: int
    valid_provenance_block_count: int
    processed_page_count: int
    provenance_integrity_score: float  # 1.0 = 100% provenance verification
    provenance_verified: bool
    page_coverage_complete: bool
    processing_mode: str
    eligible_for_evidence: bool
    extraction_accuracy_verified: bool
    anomalies: List[str]
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        """Renders report as a clean GitHub-flavored markdown document."""
        status_badge = (
            "✅ PROVENANCE PASSED"
            if self.provenance_verified
            else "❌ PROVENANCE FAILED"
        )
        evidence_status = "✅ ELIGIBLE" if self.eligible_for_evidence else "🛑 BLOCKED"
        anomaly_list = (
            "\n".join(f"- ⚠️ {a}" for a in self.anomalies)
            if self.anomalies
            else "- *No automated anomalies detected.*"
        )

        conf_display = (
            f"{self.average_confidence * 100:.2f}%"
            if self.average_confidence is not None
            else "N/A (Structural Layout Tree)"
        )

        md = f"""# Document AI Extraction Quality Report: `{self.slice_id}`

**Audit Status:** {status_badge}  
**Evidence Gate:** {evidence_status}
**Processing Mode:** `{self.processing_mode}`
**Parent Document:** {self.parent_doc_title} (`{self.parent_doc_id}`)  
**Original Page Span:** Pages {self.start_page_1based} – {self.end_page_1based} ({self.page_count} pages)  
**Generated At:** {self.generated_at}  

---

## 1. Provenance Verification

| Provenance Metric | Value | Threshold / Target | Status |
|---|---|---|---|
| **Provenance Integrity Score** | **{self.provenance_integrity_score * 100:.1f}%** | 100.0% | {"✅ Verified" if self.provenance_verified else "❌ Violated"} |
| **Blocks with Valid Source/Page** | {self.valid_provenance_block_count} / {self.total_blocks} | 100% | {"✅ OK" if self.valid_provenance_block_count == self.total_blocks and self.total_blocks else "❌ Violated"} |
| **Page Processing Coverage** | {self.processed_page_count} / {self.page_count} pages | 100% | {"✅ Complete" if self.page_coverage_complete else "❌ Incomplete"} |

---

## 2. Statistical & Structural Metrics

| Metric | Count / Score | Details |
|---|---|---|
| **Total Extracted Blocks** | {self.total_blocks} | Structured units |
| **Total Word Count** | {self.total_words:,} | Extracted tokens |
| **Total Character Count** | {self.total_characters:,} | Normalized characters |
| **Average Parser Confidence** | **{conf_display}** | Parser-reported; not medical accuracy |
| **Low Confidence Blocks (<75%)** | {self.low_confidence_block_count} | Flagged for review |

### Structural Element Distribution
- **Headings (H1/H2/H3):** {self.structure_counts.get("headings", 0)}
- **Paragraphs:** {self.structure_counts.get("paragraphs", 0)}
- **Tables:** {self.structure_counts.get("tables", 0)}
- **Lists / Bullets:** {self.structure_counts.get("lists", 0)}
- **Figure Captions:** {self.structure_counts.get("figures", 0)}

---

## 3. Anomaly & Quality Findings

{anomaly_list}

## 4. Interpretation Boundary

`extraction_accuracy_verified = {str(self.extraction_accuracy_verified).lower()}`. Automated provenance checks only prove that retained blocks point to a registered source and physical PDF page. They do not prove that OCR text, tables, figures, reading order, or medical meaning are correct. A stratified human-reviewed gold sample is required before this flag may become true.
"""
        return md


class QualityReportGenerator:
    """Generates and persists quality and provenance inspection reports."""

    def __init__(self, reports_dir: Path | str = DEFAULT_REPORTS_DIR):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        normalized_slice: NormalizedDocumentSlice,
        registry: Optional[DocumentRegistry] = None,
    ) -> QualityReport:
        """Audits a normalized slice for quality, density, and 100% provenance retention."""
        blocks = normalized_slice.blocks
        total_blocks = len(blocks)

        total_characters = sum(len(b.content) for b in blocks)
        total_words = sum(len(b.content.split()) for b in blocks)

        structure_counts = {
            "headings": sum(1 for b in blocks if "HEADING" in b.block_type),
            "paragraphs": sum(1 for b in blocks if b.block_type == "PARAGRAPH"),
            "tables": sum(1 for b in blocks if b.block_type == "TABLE"),
            "lists": sum(1 for b in blocks if b.block_type == "LIST_ITEM"),
            "figures": sum(1 for b in blocks if b.block_type == "FIGURE_CAPTION"),
        }

        confidences = [b.confidence for b in blocks if b.confidence is not None]
        if confidences:
            avg_confidence = round(sum(confidences) / len(confidences), 4)
            low_confidence_count = sum(1 for c in confidences if c < 0.75)
        else:
            avg_confidence = None
            low_confidence_count = 0

        # Provenance verification audit
        anomalies: List[str] = []
        valid_provenance_blocks = 0

        parent_doc = None
        if registry:
            parent_doc = registry.get_document(normalized_slice.parent_doc_id)

        pages_found = set(
            normalized_slice.summary_stats.get("processed_pages", [])
        )

        for b in blocks:
            pages_found.add(b.original_page_number)
            has_doc_id = bool(b.original_doc_id and b.original_doc_id == normalized_slice.parent_doc_id)
            has_valid_page = (
                normalized_slice.start_page_1based
                <= b.original_page_number
                <= normalized_slice.end_page_1based
            )
            if parent_doc and b.original_page_number > parent_doc.total_pages:
                has_valid_page = False
                anomalies.append(
                    f"Block {b.block_id} has page {b.original_page_number} exceeding parent total pages ({parent_doc.total_pages})"
                )

            # OCR corruption check
            if "\ufffd" in b.content or "\x00" in b.content:
                anomalies.append(f"OCR corruption detected in block {b.block_id}: contained invalid replacement characters")

            # Table column integrity check
            if b.block_type == "TABLE" and b.table_data:
                headers = b.table_data.get("headers", [])
                rows = b.table_data.get("rows", [])
                if headers and rows:
                    expected_cols = len(headers)
                    if any(len(r) != expected_cols for r in rows):
                        anomalies.append(f"Table {b.block_id} has ragged column count mismatch across rows")

            if has_doc_id and has_valid_page:
                valid_provenance_blocks += 1
            else:
                anomalies.append(
                    f"Provenance failure in block {b.block_id}: doc_id={b.original_doc_id}, page={b.original_page_number}"
                )

        # Check for missing pages in span
        expected_pages = set(
            range(
                normalized_slice.start_page_1based,
                normalized_slice.end_page_1based + 1,
            )
        )
        missing_pages = expected_pages - pages_found
        if missing_pages:
            anomalies.append(
                f"Pages with no processing receipt: {sorted(list(missing_pages))}"
            )

        if low_confidence_count > 0:
            anomalies.append(
                f"Found {low_confidence_count} blocks with OCR confidence < 75%"
            )

        provenance_score = (
            valid_provenance_blocks / total_blocks if total_blocks else 1.0
        )
        page_coverage_complete = not missing_pages
        provenance_verified = (
            provenance_score == 1.0
            and total_blocks > 0
            and page_coverage_complete
        )
        processing_mode = normalized_slice.processing_mode
        processor_id = normalized_slice.processor_metadata.get("processor_id")
        processor_version_id = normalized_slice.processor_metadata.get(
            "processor_version_id"
        )
        eligible_for_evidence = (
            provenance_verified
            and processing_mode == LIVE_PROCESSING_MODE
            and bool(processor_id or processor_version_id)
        )
        if processing_mode != LIVE_PROCESSING_MODE:
            anomalies.append(
                f"Processing mode '{processing_mode}' is not eligible for medical evidence"
            )
        if not processor_id and not processor_version_id:
            anomalies.append(
                "A valid GCP Document AI processor_id is required for medical evidence"
            )

        report = QualityReport(
            report_id=f"qr_{normalized_slice.slice_id}",
            slice_id=normalized_slice.slice_id,
            parent_doc_id=normalized_slice.parent_doc_id,
            parent_doc_title=normalized_slice.parent_doc_title,
            start_page_1based=normalized_slice.start_page_1based,
            end_page_1based=normalized_slice.end_page_1based,
            page_count=normalized_slice.end_page_1based - normalized_slice.start_page_1based + 1,
            total_blocks=total_blocks,
            total_words=total_words,
            total_characters=total_characters,
            structure_counts=structure_counts,
            average_confidence=(
                round(avg_confidence, 4) if avg_confidence is not None else None
            ),
            low_confidence_block_count=low_confidence_count,
            valid_provenance_block_count=valid_provenance_blocks,
            processed_page_count=len(expected_pages & pages_found),
            provenance_integrity_score=round(provenance_score, 4),
            provenance_verified=provenance_verified,
            page_coverage_complete=page_coverage_complete,
            processing_mode=processing_mode,
            eligible_for_evidence=eligible_for_evidence,
            extraction_accuracy_verified=False,
            anomalies=anomalies,
        )

        # Persist report JSON & Markdown
        json_path = self.reports_dir / f"{normalized_slice.slice_id}_quality_report.json"
        md_path = self.reports_dir / f"{normalized_slice.slice_id}_quality_report.md"

        with open(json_path, "w", encoding="utf-8") as f_json:
            json.dump(report.to_dict(), f_json, indent=2, ensure_ascii=False)

        with open(md_path, "w", encoding="utf-8") as f_md:
            f_md.write(report.to_markdown())

        return report
