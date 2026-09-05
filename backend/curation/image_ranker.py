"""Deterministic, non-diagnostic ranking for pathology image review queues."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable


TAG_PATTERNS = {
    "IHC_OR_SPECIAL_STAIN": re.compile(
        r"\b(?:immunohistochem|immunostain|special stain|PAS|GMS|congo red|reticulin|"
        r"cytokeratin|vimentin|desmin|chromogranin|synaptophysin|TTF-?1|PAX8|"
        r"CD(?:3|4|8|10|15|20|30|34|45|56|68|117|138)|ER|PR|HER2|Ki-?67)\b",
        re.IGNORECASE,
    ),
    "CYTOLOGY_OR_HEMATOLOGY": re.compile(
        r"\b(?:cytolog|smear|aspirat|bone marrow|peripheral blood|blast|Pap stain|cell block)\w*\b",
        re.IGNORECASE,
    ),
    "GROSS_PATHOLOGY": re.compile(
        r"\b(?:gross|cut surface|resection specimen|macroscopic|well circumscribed|"
        r"hemorrhagic|necrotic mass)\b",
        re.IGNORECASE,
    ),
    "MEDICAL_DIAGRAM": re.compile(
        r"\b(?:diagram|schematic|algorithm|pathway|classification|flowchart)\b",
        re.IGNORECASE,
    ),
    "INTEGRATED_CLINICOPATHOLOGIC": re.compile(
        r"\b(?:patient|year-old|clinical|syndrome|prognos|therapy|treatment|mutation|"
        r"translocation|survival|stage|grade)\w*\b",
        re.IGNORECASE,
    ),
}


@dataclass(frozen=True)
class RankInput:
    width: int
    height: int
    file_size_bytes: int
    entropy: float
    blank_score: float
    aspect_ratio: float
    is_exact_duplicate: bool
    triage_class: str
    link_confidence: float
    link_type: str
    has_exact_page_provenance: bool
    evidence_text: str = ""


@dataclass(frozen=True)
class RankResult:
    score: float
    suggested_utility_class: str
    tags: tuple[str, ...]
    signals: tuple[str, ...]
    requires_human_verification: bool = True


def _text_tags(text: str) -> list[str]:
    return [tag for tag, pattern in TAG_PATTERNS.items() if pattern.search(text)]


def rank_image(candidate: RankInput) -> RankResult:
    """Rank review value without asserting diagnosis, stain, or approval."""
    score = 10.0
    signals: list[str] = []
    short_side = min(candidate.width, candidate.height)
    area = max(0, candidate.width * candidate.height)

    if short_side >= 300:
        score += 18
        signals.append("diagnostic-size")
    elif short_side >= 150:
        score += 10
        signals.append("reviewable-size")
    elif short_side < 40:
        score -= 25
        signals.append("tiny-fragment-risk")

    if area:
        score += min(14.0, max(0.0, math.log10(area) - 3.0) * 5.0)
    if 3.0 <= candidate.entropy <= 8.0:
        score += 8
        signals.append("information-rich")
    elif candidate.entropy < 1.5:
        score -= 16
        signals.append("low-entropy-risk")
    score -= min(24.0, max(0.0, candidate.blank_score) * 24.0)

    if 0.15 <= candidate.aspect_ratio <= 8.0:
        score += 6
    else:
        score -= 18
        signals.append("extreme-aspect-risk")
    if candidate.file_size_bytes >= 80_000:
        score += 7
    if candidate.is_exact_duplicate:
        score -= 22
        signals.append("duplicate-review-lower-priority")

    if candidate.has_exact_page_provenance:
        score += 14
        signals.append("exact-page-provenance")
    else:
        score -= 30
        signals.append("provenance-unresolved")
    score += min(12.0, max(0.0, candidate.link_confidence) * 12.0)
    if candidate.link_type == "FIGURE_CITATION":
        score += 8
        signals.append("explicit-figure-citation")

    tags = _text_tags(candidate.evidence_text)
    if tags:
        score += min(10.0, len(tags) * 3.0)
        signals.append("context-tags-available")
    suggested = next(
        (tag for tag in ("IHC_OR_SPECIAL_STAIN", "CYTOLOGY_OR_HEMATOLOGY", "GROSS_PATHOLOGY", "MEDICAL_DIAGRAM") if tag in tags),
        candidate.triage_class if candidate.triage_class else "UNKNOWN_REVIEW_REQUIRED",
    )
    return RankResult(
        score=round(min(100.0, max(0.0, score)), 2),
        suggested_utility_class=suggested,
        tags=tuple(sorted(set(tags))),
        signals=tuple(signals),
    )


def allocate_shortlist(rows: Iterable[dict], total: int = 72) -> list[dict]:
    """Allocate roughly 2× pilot quota while preserving category coverage."""
    rows = sorted(rows, key=lambda row: (-row["priority_score"], row["image_asset_id"], row["occurrence_id"]))
    quotas = {
        "MORPHOLOGY_OR_RECOGNITION": 24,
        "IHC_OR_SPECIAL_STAIN": 18,
        "INTEGRATED_CLINICOPATHOLOGIC": 15,
        "GROSS_CYTOLOGY_HEMATOLOGY_OR_DIAGRAM": 15,
    }
    selected: list[dict] = []
    used_assets: set[str] = set()

    def cohort(row: dict) -> str:
        tags = set(row.get("suggested_tags") or [])
        utility = row.get("suggested_utility_class")
        if utility == "IHC_OR_SPECIAL_STAIN":
            return "IHC_OR_SPECIAL_STAIN"
        if utility in {"GROSS_PATHOLOGY", "CYTOLOGY_OR_HEMATOLOGY", "MEDICAL_DIAGRAM"}:
            return "GROSS_CYTOLOGY_HEMATOLOGY_OR_DIAGRAM"
        if "INTEGRATED_CLINICOPATHOLOGIC" in tags:
            return "INTEGRATED_CLINICOPATHOLOGIC"
        return "MORPHOLOGY_OR_RECOGNITION"

    for cohort_name, quota in quotas.items():
        matches = [row for row in rows if cohort(row) == cohort_name]
        by_source: dict[str, list[dict]] = {}
        for row in matches:
            by_source.setdefault(row.get("source_short_name") or "UNKNOWN", []).append(row)
        source_names = sorted(by_source)
        source_offsets = {name: 0 for name in source_names}
        cohort_count = 0
        while cohort_count < quota:
            made_progress = False
            for source_name in source_names:
                source_rows = by_source[source_name]
                while source_offsets[source_name] < len(source_rows):
                    row = source_rows[source_offsets[source_name]]
                    source_offsets[source_name] += 1
                    if row["image_asset_id"] in used_assets:
                        continue
                    selected.append({**row, "shortlist_cohort": cohort_name})
                    used_assets.add(row["image_asset_id"])
                    cohort_count += 1
                    made_progress = True
                    break
                if cohort_count >= quota:
                    break
            if not made_progress:
                break
    for row in rows:
        if len(selected) >= total:
            break
        if row["image_asset_id"] not in used_assets:
            selected.append({**row, "shortlist_cohort": cohort(row)})
            used_assets.add(row["image_asset_id"])
    return selected[:total]
