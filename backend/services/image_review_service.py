"""Human curation gate for private pathology images and their text evidence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select

from database.models import (
    DocumentChunk,
    ImageAsset,
    ImageOccurrence,
    ImageReview,
    ImageTextEvidenceLink,
    Source,
    SourceDocument,
)


FINAL_STATES = {
    "APPROVED_INTERNAL_STUDY",
    "APPROVED_INTERNAL_QUESTION_CANDIDATE",
    "REJECTED_NON_EDUCATIONAL",
    "REJECTED_UNUSABLE_QUALITY",
    "PROVENANCE_UNRESOLVED",
}
ALLOWED_UTILITY_CLASSES = {
    "PATHOLOGY_MICROSCOPY",
    "GROSS_PATHOLOGY",
    "IHC_OR_SPECIAL_STAIN",
    "CYTOLOGY_OR_HEMATOLOGY",
    "MEDICAL_DIAGRAM",
    "CHART_OR_GRAPH",
    "TABLE_OR_TEXT_FIGURE",
    "MULTI_PANEL_FIGURE",
    "LOGO_ICON_OR_DECORATION",
    "PAGE_FRAGMENT_OR_RULE",
    "BLANK_OR_NEAR_BLANK",
    "DUPLICATE",
    "UNKNOWN_REVIEW_REQUIRED",
}


class ImageReviewConflictError(RuntimeError):
    pass


class ImageReviewService:
    @staticmethod
    def _asset(db, asset_id: str) -> ImageAsset:
        asset = db.query(ImageAsset).filter_by(id=asset_id).first()
        if not asset:
            raise ValueError(f"Image asset not found: {asset_id}")
        return asset

    @staticmethod
    def _snapshot(asset: ImageAsset) -> dict[str, Any]:
        return {
            "curation_status": asset.curation_status,
            "reviewed_utility_class": asset.reviewed_utility_class,
            "reviewed_diagnosis": asset.reviewed_diagnosis,
            "reviewed_stain": asset.reviewed_stain,
            "reviewed_magnification": asset.reviewed_magnification,
            "reviewed_caption": asset.reviewed_caption,
            "metadata_verification_status": asset.metadata_verification_status,
            "storage_access_status": asset.storage_access_status,
            "curation_reviewed_by": asset.curation_reviewed_by,
            "curation_reviewed_at": asset.curation_reviewed_at.isoformat()
            if asset.curation_reviewed_at
            else None,
            "review_revision": asset.review_revision,
        }

    @staticmethod
    def summary(db) -> dict[str, Any]:
        status_counts = dict(
            db.query(ImageAsset.curation_status, func.count(ImageAsset.id))
            .group_by(ImageAsset.curation_status)
            .all()
        )
        total = sum(status_counts.values())
        verified_links = (
            db.query(func.count(ImageTextEvidenceLink.id))
            .filter(ImageTextEvidenceLink.verification_status == "HUMAN_VERIFIED")
            .scalar()
            or 0
        )
        eligible_assets = ImageReviewService._eligible_query(db).all()
        distribution = ImageReviewService._distribution(eligible_assets)
        gate_open = ImageReviewService._distribution_gate(len(eligible_assets), distribution)
        return {
            "total_assets": total,
            "status_counts": status_counts,
            "human_verified_links": verified_links,
            "eligible_question_assets": len(eligible_assets),
            "pilot_target": 30,
            "pilot_gate_open": gate_open,
        }

    @staticmethod
    def list_assets(
        db,
        *,
        curation_status: Optional[str] = None,
        utility_class: Optional[str] = None,
        source: Optional[str] = None,
        pilot_shortlisted: bool = False,
        page: int = 1,
        limit: int = 50,
    ) -> dict[str, Any]:
        first_occurrence_id = (
            select(ImageOccurrence.id)
            .where(ImageOccurrence.image_asset_id == ImageAsset.id)
            .order_by(ImageOccurrence.is_canonical.desc(), ImageOccurrence.pdf_page, ImageOccurrence.id)
            .limit(1)
            .correlate(ImageAsset)
            .scalar_subquery()
        )
        source_name = (
            select(Source.short_name)
            .join(SourceDocument, SourceDocument.source_id == Source.id)
            .join(ImageOccurrence, ImageOccurrence.source_document_id == SourceDocument.id)
            .where(ImageOccurrence.id == first_occurrence_id)
            .scalar_subquery()
        )
        physical_page = (
            select(ImageOccurrence.pdf_page)
            .where(ImageOccurrence.id == first_occurrence_id)
            .scalar_subquery()
        )
        verified_link_count = (
            select(func.count(ImageTextEvidenceLink.id))
            .where(
                ImageTextEvidenceLink.image_asset_id == ImageAsset.id,
                ImageTextEvidenceLink.verification_status == "HUMAN_VERIFIED",
            )
            .correlate(ImageAsset)
            .scalar_subquery()
        )
        query = db.query(
            ImageAsset,
            source_name.label("source_short_name"),
            physical_page.label("pdf_page"),
            verified_link_count.label("verified_link_count"),
        )
        if curation_status:
            query = query.filter(ImageAsset.curation_status == curation_status)
        if utility_class:
            query = query.filter(
                func.coalesce(ImageAsset.reviewed_utility_class, ImageAsset.triage_class)
                == utility_class
            )
        if source:
            source_occurrence_exists = (
                db.query(ImageOccurrence.id)
                .join(SourceDocument, ImageOccurrence.source_document_id == SourceDocument.id)
                .join(Source, SourceDocument.source_id == Source.id)
                .filter(
                    ImageOccurrence.image_asset_id == ImageAsset.id,
                    Source.short_name == source,
                )
                .exists()
            )
            query = query.filter(source_occurrence_exists)
        if pilot_shortlisted:
            query = query.filter(ImageAsset.pilot_shortlisted.is_(True))
        total = query.with_entities(func.count(ImageAsset.id)).scalar() or 0
        rows = (
            query.order_by(
                ImageAsset.pilot_shortlisted.desc(),
                ImageAsset.automated_rank_score.desc().nullslast(),
                ImageAsset.created_at,
                ImageAsset.id,
            )
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        items = []
        for asset, row_source, row_page, row_verified_count in rows:
            items.append(
                {
                    "id": asset.id,
                    "filename": asset.filename,
                    "width": asset.width,
                    "height": asset.height,
                    "triage_class": asset.triage_class,
                    "reviewed_utility_class": asset.reviewed_utility_class,
                    "curation_status": asset.curation_status,
                    "metadata_verification_status": asset.metadata_verification_status,
                    "storage_access_status": asset.storage_access_status,
                    "review_revision": asset.review_revision,
                    "automated_rank_score": asset.automated_rank_score,
                    "automated_suggested_utility_class": asset.automated_suggested_utility_class,
                    "automated_tags": asset.automated_tags or [],
                    "pilot_shortlisted": asset.pilot_shortlisted,
                    "source_short_name": row_source,
                    "pdf_page": row_page,
                    "verified_link_count": row_verified_count or 0,
                }
            )
        return {"items": items, "total": total, "page": page, "limit": limit}

    @staticmethod
    def get_asset(db, asset_id: str) -> dict[str, Any]:
        asset = ImageReviewService._asset(db, asset_id)
        occurrences = (
            db.query(ImageOccurrence, SourceDocument, Source)
            .join(SourceDocument, ImageOccurrence.source_document_id == SourceDocument.id)
            .join(Source, SourceDocument.source_id == Source.id)
            .filter(ImageOccurrence.image_asset_id == asset.id)
            .order_by(Source.short_name, ImageOccurrence.pdf_page)
            .all()
        )
        links = (
            db.query(ImageTextEvidenceLink, DocumentChunk, SourceDocument, Source)
            .join(DocumentChunk, ImageTextEvidenceLink.document_chunk_id == DocumentChunk.id)
            .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
            .join(Source, SourceDocument.source_id == Source.id)
            .filter(ImageTextEvidenceLink.image_asset_id == asset.id)
            .order_by(Source.short_name, DocumentChunk.pdf_page, DocumentChunk.chunk_index)
            .all()
        )
        history = (
            db.query(ImageReview)
            .filter_by(image_asset_id=asset.id)
            .order_by(ImageReview.created_at.desc())
            .limit(20)
            .all()
        )
        return {
            **ImageReviewService._snapshot(asset),
            "id": asset.id,
            "filename": asset.filename,
            "sha256": asset.sha256,
            "width": asset.width,
            "height": asset.height,
            "format": asset.format,
            "triage_class": asset.triage_class,
            "reviewed_utility_class": asset.reviewed_utility_class,
            "rights_status": asset.rights_status,
            "has_resolvable_object": bool(asset.storage_uri and asset.sha256),
            "automated_rank_score": asset.automated_rank_score,
            "automated_suggested_utility_class": asset.automated_suggested_utility_class,
            "automated_tags": asset.automated_tags or [],
            "pilot_shortlisted": asset.pilot_shortlisted,
            "verified_link_count": sum(
                1 for link, _chunk, _document, _source in links
                if link.verification_status == "HUMAN_VERIFIED"
            ),
            "source_short_name": occurrences[0][2].short_name if occurrences else None,
            "pdf_page": occurrences[0][0].pdf_page if occurrences else None,
            "occurrences": [
                {
                    "id": occurrence.id,
                    "source_document_id": occurrence.source_document_id,
                    "source_short_name": source.short_name,
                    "source_title": source.title,
                    "pdf_page": occurrence.pdf_page,
                    "textbook_page": occurrence.textbook_page,
                    "figure_label": occurrence.figure_label,
                    "is_canonical": occurrence.is_canonical,
                }
                for occurrence, _document, source in occurrences
            ],
            "links": [
                {
                    "id": link.id,
                    "occurrence_id": link.image_occurrence_id,
                    "document_chunk_id": chunk.id,
                    "source_short_name": source.short_name,
                    "pdf_page": chunk.pdf_page,
                    "textbook_page": chunk.textbook_page,
                    "section_heading": chunk.section_heading,
                    "content": chunk.content,
                    "confidence": link.confidence,
                    "verification_status": link.verification_status,
                }
                for link, chunk, _document, source in links
            ],
            "history": [
                {
                    "id": review.id,
                    "action": review.action,
                    "reviewer_id": review.reviewer_id,
                    "notes": review.notes,
                    "created_at": review.created_at,
                }
                for review in history
            ],
        }

    @staticmethod
    def _resolve_pair(db, asset: ImageAsset, occurrence_id: Optional[str], link_id: Optional[str]):
        if not occurrence_id or not link_id:
            return None, None
        occurrence = (
            db.query(ImageOccurrence)
            .filter_by(id=occurrence_id, image_asset_id=asset.id)
            .first()
        )
        link = (
            db.query(ImageTextEvidenceLink)
            .filter_by(id=link_id, image_asset_id=asset.id)
            .first()
        )
        if not occurrence or not link:
            raise ValueError("Selected occurrence or evidence link does not belong to this image")
        chunk = db.query(DocumentChunk).filter_by(id=link.document_chunk_id).one()
        if occurrence.source_document_id != chunk.document_id or occurrence.pdf_page != chunk.pdf_page:
            raise ValueError("Evidence must match the selected image occurrence source and PDF page")
        return occurrence, link

    @staticmethod
    def save(
        db,
        asset_id: str,
        *,
        reviewer_id: str,
        expected_revision: int,
        utility_class: str,
        diagnosis: Optional[str],
        stain: Optional[str],
        magnification: Optional[str],
        caption: Optional[str],
        occurrence_id: Optional[str],
        link_id: Optional[str],
        notes: str,
        action: str = "SAVE_DRAFT",
    ) -> dict[str, Any]:
        asset = ImageReviewService._asset(db, asset_id)
        if asset.review_revision != expected_revision:
            raise ImageReviewConflictError("Image changed since it was opened; reload before saving")
        if utility_class not in ALLOWED_UTILITY_CLASSES:
            raise ValueError("Unsupported utility class")
        if len(notes.strip()) < 3:
            raise ValueError("Concise review notes are required")
        occurrence, link = ImageReviewService._resolve_pair(db, asset, occurrence_id, link_id)
        previous = ImageReviewService._snapshot(asset)
        asset.reviewed_utility_class = utility_class
        asset.reviewed_diagnosis = diagnosis.strip() if diagnosis else None
        asset.reviewed_stain = stain.strip() if stain else None
        asset.reviewed_magnification = magnification.strip() if magnification else None
        asset.reviewed_caption = caption.strip() if caption else None
        asset.curation_reviewed_by = reviewer_id
        asset.curation_reviewed_at = datetime.now(timezone.utc)
        asset.review_revision += 1

        if action == "SAVE_DRAFT":
            asset.curation_status = "HUMAN_REVIEW"
            asset.metadata_verification_status = "HUMAN_REVIEW"
        elif action == "APPROVE_INTERNAL_STUDY":
            asset.curation_status = "APPROVED_INTERNAL_STUDY"
            asset.metadata_verification_status = "HUMAN_VERIFIED"
        elif action == "APPROVE_INTERNAL_QUESTION_CANDIDATE":
            if asset.rights_status not in {"RESTRICTED_INTERNAL", "INTERNAL_EDUCATIONAL_USE"}:
                raise ValueError("Image rights do not permit internal educational question use")
            if not asset.storage_uri or not asset.sha256:
                raise ValueError("Question candidates require a resolvable catalog object and SHA-256")
            if not occurrence or not link:
                raise ValueError("Question candidates require an exact occurrence and evidence link")
            if not asset.reviewed_diagnosis or not asset.reviewed_caption:
                raise ValueError("Question candidates require a reviewed diagnosis and caption")
            link.image_occurrence_id = occurrence.id
            link.verification_status = "HUMAN_VERIFIED"
            link.verified_by = reviewer_id
            link.verified_at = datetime.now(timezone.utc)
            asset.curation_status = "APPROVED_INTERNAL_QUESTION_CANDIDATE"
            asset.metadata_verification_status = "HUMAN_VERIFIED"
        elif action in FINAL_STATES:
            asset.curation_status = action
            asset.metadata_verification_status = "REJECTED"
        else:
            raise ValueError("Unsupported image review action")

        db.flush()
        db.add(
            ImageReview(
                id=str(uuid.uuid4()),
                image_asset_id=asset.id,
                reviewer_id=reviewer_id,
                action=action,
                notes=notes.strip(),
                previous_snapshot=previous,
                new_snapshot=ImageReviewService._snapshot(asset),
            )
        )
        db.commit()
        return ImageReviewService.get_asset(db, asset.id)

    @staticmethod
    def _eligible_query(db):
        return (
            db.query(ImageAsset)
            .join(ImageTextEvidenceLink, ImageTextEvidenceLink.image_asset_id == ImageAsset.id)
            .join(
                ImageOccurrence,
                ImageOccurrence.id == ImageTextEvidenceLink.image_occurrence_id,
            )
            .filter(
                ImageAsset.curation_status == "APPROVED_INTERNAL_QUESTION_CANDIDATE",
                ImageAsset.metadata_verification_status == "HUMAN_VERIFIED",
                ImageAsset.storage_uri.isnot(None),
                ImageAsset.storage_access_status == "PRIVATE_VERIFIED",
                ImageAsset.rights_status.in_(["RESTRICTED_INTERNAL", "INTERNAL_EDUCATIONAL_USE"]),
                ImageTextEvidenceLink.verification_status == "HUMAN_VERIFIED",
                ImageAsset.reviewed_diagnosis.isnot(None),
                ImageAsset.reviewed_caption.isnot(None),
            )
            .distinct()
        )

    @staticmethod
    def pilot_readiness(db) -> dict[str, Any]:
        eligible = ImageReviewService._eligible_query(db).all()
        distribution = ImageReviewService._distribution(eligible)
        gate_open = ImageReviewService._distribution_gate(len(eligible), distribution)
        missing_count = max(0, 30 - len(eligible))
        missing_distribution = []
        if distribution.get("IHC_OR_SPECIAL_STAIN", 0) < 8:
            missing_distribution.append("8 IHC/special-stain assets")
        morphology = distribution.get("PATHOLOGY_MICROSCOPY", 0) + distribution.get("MULTI_PANEL_FIGURE", 0)
        if morphology < 10:
            missing_distribution.append("10 morphology/recognition assets")
        supporting = sum(
            distribution.get(key, 0)
            for key in ("GROSS_PATHOLOGY", "CYTOLOGY_OR_HEMATOLOGY", "MEDICAL_DIAGRAM")
        )
        if supporting < 6:
            missing_distribution.append("6 gross/cytology/hematology/diagram assets")
        return {
            "target": 30,
            "eligible": len(eligible),
            "gate_open": gate_open,
            "distribution": distribution,
            "required_distribution": {
                "MORPHOLOGY_OR_RECOGNITION": 10,
                "IHC_OR_SPECIAL_STAIN": 8,
                "INTEGRATED_CLINICOPATHOLOGIC": 6,
                "GROSS_CYTOLOGY_HEMATOLOGY_OR_DIAGRAM": 6,
            },
            "generation_allowed": False,
            "message": (
                "Curation count reached; blueprint allocation and explicit paid-run approval are next."
                if gate_open
                else "Curation gate incomplete: "
                + "; ".join(
                    ([f"{missing_count} additional eligible assets"] if missing_count else [])
                    + missing_distribution
                )
            ),
        }

    @staticmethod
    def _distribution(assets) -> dict[str, int]:
        distribution: dict[str, int] = {}
        for asset in assets:
            key = asset.reviewed_utility_class or asset.triage_class
            distribution[key] = distribution.get(key, 0) + 1
        return distribution

    @staticmethod
    def _distribution_gate(total: int, distribution: dict[str, int]) -> bool:
        morphology = distribution.get("PATHOLOGY_MICROSCOPY", 0) + distribution.get(
            "MULTI_PANEL_FIGURE", 0
        )
        supporting = sum(
            distribution.get(key, 0)
            for key in ("GROSS_PATHOLOGY", "CYTOLOGY_OR_HEMATOLOGY", "MEDICAL_DIAGRAM")
        )
        return (
            total >= 30
            and morphology >= 10
            and distribution.get("IHC_OR_SPECIAL_STAIN", 0) >= 8
            and supporting >= 6
        )
