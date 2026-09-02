"""
backend/curation/image_triage.py

Milestone 18A: Automated Image Triage Engine.
Applies deterministic heuristics and statistical profiling to classify
extracted images into candidate utility classes and decision statuses without
permanently deleting or modifying raw files.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Tuple

from backend.curation.image_inventory import ImageRecord

logger = logging.getLogger(__name__)


class TriageClass(str, Enum):
    """Utility classification for extracted textbook images."""
    PATHOLOGY_MICROSCOPY = "PATHOLOGY_MICROSCOPY"
    GROSS_PATHOLOGY = "GROSS_PATHOLOGY"
    IHC_OR_SPECIAL_STAIN = "IHC_OR_SPECIAL_STAIN"
    CYTOLOGY_OR_HEMATOLOGY = "CYTOLOGY_OR_HEMATOLOGY"
    MEDICAL_DIAGRAM = "MEDICAL_DIAGRAM"
    CHART_OR_GRAPH = "CHART_OR_GRAPH"
    TABLE_OR_TEXT_FIGURE = "TABLE_OR_TEXT_FIGURE"
    MULTI_PANEL_FIGURE = "MULTI_PANEL_FIGURE"
    LOGO_ICON_OR_DECORATION = "LOGO_ICON_OR_DECORATION"
    PAGE_FRAGMENT_OR_RULE = "PAGE_FRAGMENT_OR_RULE"
    BLANK_OR_NEAR_BLANK = "BLANK_OR_NEAR_BLANK"
    DUPLICATE = "DUPLICATE"
    UNKNOWN_REVIEW_REQUIRED = "UNKNOWN_REVIEW_REQUIRED"


class DecisionStatus(str, Enum):
    """Non-destructive automated candidate decision status."""
    AUTO_KEEP_CANDIDATE = "AUTO_KEEP_CANDIDATE"
    AUTO_REJECT_CANDIDATE = "AUTO_REJECT_CANDIDATE"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    QUARANTINED_CORRUPT = "QUARANTINED_CORRUPT"


@dataclass
class TriageResult:
    """Evaluation result for an individual image record."""
    extraction_id: str
    filename: str
    sha256: str
    triage_class: TriageClass
    decision_status: DecisionStatus
    confidence: float
    reasons: List[str]
    width: int
    height: int
    aspect_ratio: float
    pixel_area: int
    file_size_bytes: int
    pdf_page: int | None
    textbook_page: int | None
    is_exact_duplicate: bool

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["triage_class"] = self.triage_class.value
        data["decision_status"] = self.decision_status.value
        return data


class ImageTriageEngine:
    """
    Evaluates extracted image records against deterministic rules,
    assigning provisional utility classes and candidate triage statuses.
    """

    def __init__(
        self,
        min_auto_keep_area: int = 150_000,
        min_auto_keep_bytes: int = 80_000,
        max_micro_dim: int = 24,
        extreme_aspect_ratio_high: float = 12.0,
        extreme_aspect_ratio_low: float = 0.08,
    ):
        self.min_auto_keep_area = min_auto_keep_area
        self.min_auto_keep_bytes = min_auto_keep_bytes
        self.max_micro_dim = max_micro_dim
        self.extreme_aspect_ratio_high = extreme_aspect_ratio_high
        self.extreme_aspect_ratio_low = extreme_aspect_ratio_low

    def evaluate_record(self, record: ImageRecord) -> TriageResult:
        """Evaluates a single ImageRecord and produces its TriageResult."""
        reasons: List[str] = []

        # 1. Corrupt files
        if record.is_corrupt:
            return TriageResult(
                extraction_id=record.extraction_id,
                filename=record.filename,
                sha256=record.sha256,
                triage_class=TriageClass.UNKNOWN_REVIEW_REQUIRED,
                decision_status=DecisionStatus.QUARANTINED_CORRUPT,
                confidence=1.0,
                reasons=["File could not be parsed as a valid PNG"],
                width=record.width,
                height=record.height,
                aspect_ratio=record.aspect_ratio,
                pixel_area=record.pixel_area,
                file_size_bytes=record.file_size_bytes,
                pdf_page=record.pdf_page,
                textbook_page=record.textbook_page,
                is_exact_duplicate=record.is_exact_duplicate,
            )

        # 2. Exact Duplicates (non-canonical occurrences)
        if record.is_exact_duplicate and not record.is_canonical:
            reasons.append(
                f"Exact SHA-256 duplicate of canonical asset in cluster {record.duplicate_cluster_id}"
            )
            return TriageResult(
                extraction_id=record.extraction_id,
                filename=record.filename,
                sha256=record.sha256,
                triage_class=TriageClass.DUPLICATE,
                decision_status=DecisionStatus.AUTO_REJECT_CANDIDATE,
                confidence=1.0,
                reasons=reasons,
                width=record.width,
                height=record.height,
                aspect_ratio=record.aspect_ratio,
                pixel_area=record.pixel_area,
                file_size_bytes=record.file_size_bytes,
                pdf_page=record.pdf_page,
                textbook_page=record.textbook_page,
                is_exact_duplicate=True,
            )

        # 3. Micro decorations, bullets, and dots (e.g. 3x4 px, <24x24 px)
        if record.width <= self.max_micro_dim and record.height <= self.max_micro_dim:
            reasons.append(
                f"Micro dimensions ({record.width}x{record.height} <= {self.max_micro_dim}px): decorative bullet/dot"
            )
            return TriageResult(
                extraction_id=record.extraction_id,
                filename=record.filename,
                sha256=record.sha256,
                triage_class=TriageClass.LOGO_ICON_OR_DECORATION,
                decision_status=DecisionStatus.AUTO_REJECT_CANDIDATE,
                confidence=0.98,
                reasons=reasons,
                width=record.width,
                height=record.height,
                aspect_ratio=record.aspect_ratio,
                pixel_area=record.pixel_area,
                file_size_bytes=record.file_size_bytes,
                pdf_page=record.pdf_page,
                textbook_page=record.textbook_page,
                is_exact_duplicate=record.is_exact_duplicate,
            )

        # 4. Thin Page Rules / Horizontal or Vertical Dividers
        if (
            (record.aspect_ratio >= self.extreme_aspect_ratio_high and record.height <= 12)
            or (record.aspect_ratio <= self.extreme_aspect_ratio_low and record.width <= 12)
        ):
            reasons.append(
                f"Extreme aspect ratio ({record.aspect_ratio}) with thin boundary: page rule/divider fragment"
            )
            return TriageResult(
                extraction_id=record.extraction_id,
                filename=record.filename,
                sha256=record.sha256,
                triage_class=TriageClass.PAGE_FRAGMENT_OR_RULE,
                decision_status=DecisionStatus.AUTO_REJECT_CANDIDATE,
                confidence=0.95,
                reasons=reasons,
                width=record.width,
                height=record.height,
                aspect_ratio=record.aspect_ratio,
                pixel_area=record.pixel_area,
                file_size_bytes=record.file_size_bytes,
                pdf_page=record.pdf_page,
                textbook_page=record.textbook_page,
                is_exact_duplicate=record.is_exact_duplicate,
            )

        # 5. Blank or near-blank content
        if record.blank_score >= 0.90:
            reasons.append(f"High blank score ({record.blank_score:.2f}) and low entropy: uniform background")
            return TriageResult(
                extraction_id=record.extraction_id,
                filename=record.filename,
                sha256=record.sha256,
                triage_class=TriageClass.BLANK_OR_NEAR_BLANK,
                decision_status=DecisionStatus.AUTO_REJECT_CANDIDATE,
                confidence=0.92,
                reasons=reasons,
                width=record.width,
                height=record.height,
                aspect_ratio=record.aspect_ratio,
                pixel_area=record.pixel_area,
                file_size_bytes=record.file_size_bytes,
                pdf_page=record.pdf_page,
                textbook_page=record.textbook_page,
                is_exact_duplicate=record.is_exact_duplicate,
            )

        # 6. High-Confidence Educational / Pathology Visuals (AUTO_KEEP)
        if record.pixel_area >= self.min_auto_keep_area and record.file_size_bytes >= self.min_auto_keep_bytes:
            # Distinguish Multi-panel vs Single Panel vs Diagram
            if 0.6 <= record.aspect_ratio <= 1.8:
                triage_cls = TriageClass.PATHOLOGY_MICROSCOPY
                reasons.append("High resolution, standard aspect ratio, high entropy medical plate")
            elif record.aspect_ratio > 2.0 or record.aspect_ratio < 0.5:
                triage_cls = TriageClass.MULTI_PANEL_FIGURE
                reasons.append("Large composite multi-panel figure")
            else:
                triage_cls = TriageClass.PATHOLOGY_MICROSCOPY
                reasons.append("Substantial pixel area and byte density consistent with pathology plate")

            return TriageResult(
                extraction_id=record.extraction_id,
                filename=record.filename,
                sha256=record.sha256,
                triage_class=triage_cls,
                decision_status=DecisionStatus.AUTO_KEEP_CANDIDATE,
                confidence=0.90,
                reasons=reasons,
                width=record.width,
                height=record.height,
                aspect_ratio=record.aspect_ratio,
                pixel_area=record.pixel_area,
                file_size_bytes=record.file_size_bytes,
                pdf_page=record.pdf_page,
                textbook_page=record.textbook_page,
                is_exact_duplicate=record.is_exact_duplicate,
            )

        # 7. Intermediate / Ambiguous Insets & Panels (HUMAN_REVIEW_REQUIRED)
        # Never automatically reject small insets that might contain valuable histology or cytopathology!
        reasons.append("Intermediate dimensions / file size: human review required to verify educational utility")
        triage_cls = TriageClass.UNKNOWN_REVIEW_REQUIRED
        if record.width >= 100 and record.height >= 100:
            triage_cls = TriageClass.MEDICAL_DIAGRAM

        return TriageResult(
            extraction_id=record.extraction_id,
            filename=record.filename,
            sha256=record.sha256,
            triage_class=triage_cls,
            decision_status=DecisionStatus.HUMAN_REVIEW_REQUIRED,
            confidence=0.60,
            reasons=reasons,
            width=record.width,
            height=record.height,
            aspect_ratio=record.aspect_ratio,
            pixel_area=record.pixel_area,
            file_size_bytes=record.file_size_bytes,
            pdf_page=record.pdf_page,
            textbook_page=record.textbook_page,
            is_exact_duplicate=record.is_exact_duplicate,
        )

    def run_triage(self, records: List[ImageRecord]) -> Tuple[List[TriageResult], Dict[str, Any]]:
        """Evaluates all records and returns individual triage results with an aggregate summary."""
        results: List[TriageResult] = []
        for rec in records:
            res = self.evaluate_record(rec)
            results.append(res)

        status_counts = {
            DecisionStatus.AUTO_KEEP_CANDIDATE.value: sum(1 for r in results if r.decision_status == DecisionStatus.AUTO_KEEP_CANDIDATE),
            DecisionStatus.AUTO_REJECT_CANDIDATE.value: sum(1 for r in results if r.decision_status == DecisionStatus.AUTO_REJECT_CANDIDATE),
            DecisionStatus.HUMAN_REVIEW_REQUIRED.value: sum(1 for r in results if r.decision_status == DecisionStatus.HUMAN_REVIEW_REQUIRED),
            DecisionStatus.QUARANTINED_CORRUPT.value: sum(1 for r in results if r.decision_status == DecisionStatus.QUARANTINED_CORRUPT),
        }

        class_counts = {}
        for cls in TriageClass:
            class_counts[cls.value] = sum(1 for r in results if r.triage_class == cls)

        summary = {
            "total_evaluated": len(results),
            "decision_statuses": status_counts,
            "utility_classes": class_counts,
        }

        logger.info(
            f"🎯 Triage Evaluation Complete:\n"
            f"   - AUTO_KEEP_CANDIDATE:   {status_counts[DecisionStatus.AUTO_KEEP_CANDIDATE.value]:,} ({status_counts[DecisionStatus.AUTO_KEEP_CANDIDATE.value]/len(results)*100:.1f}%)\n"
            f"   - AUTO_REJECT_CANDIDATE: {status_counts[DecisionStatus.AUTO_REJECT_CANDIDATE.value]:,} ({status_counts[DecisionStatus.AUTO_REJECT_CANDIDATE.value]/len(results)*100:.1f}%)\n"
            f"   - HUMAN_REVIEW_REQUIRED: {status_counts[DecisionStatus.HUMAN_REVIEW_REQUIRED.value]:,} ({status_counts[DecisionStatus.HUMAN_REVIEW_REQUIRED.value]/len(results)*100:.1f}%)\n"
            f"   - QUARANTINED_CORRUPT:   {status_counts[DecisionStatus.QUARANTINED_CORRUPT.value]:,}"
        )

        return results, summary
