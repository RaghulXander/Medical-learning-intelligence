"""
backend/api/routes/multimodal.py

REST API Endpoints for Pathology Image Catalog & Multimodal Question Generation.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.models import (
    ClassificationSource,
    ClassificationStatus,
    CognitiveLevel,
    DifficultyLevel,
    Question,
    QuestionStatus,
    QuestionType,
    TopicMappingStatus,
    User,
)
from backend.api.dependencies import require_permission
from backend.core.authorization import Permission
from backend.services.multimodal.image_catalog import get_image_catalog
from backend.services.multimodal.models import (
    MultimodalGenerationApiRequest,
    MultimodalQuestionBlueprint,
    StainType,
)
from backend.services.multimodal.generator import MultimodalMCQGenerator

router = APIRouter(prefix="/api/multimodal", tags=["Multimodal"])
catalog = get_image_catalog()
multimodal_generator = MultimodalMCQGenerator()


def get_db():
    from database.db import get_engine, get_session_factory
    engine = get_engine()
    session_factory = get_session_factory(engine)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


@router.get("/images")
def list_pathology_images(
    organ_system: Optional[str] = Query(None, description="Filter by organ system (Breast, Kidney, etc.)"),
    stain_type: Optional[str] = Query(None, description="Filter by stain (H&E, IHC_HER2, CONGO_RED, etc.)"),
    search: Optional[str] = Query(None, description="Search term in title, diagnosis, or caption"),
):
    """Lists cataloged reference pathology images with morphological metadata."""
    stain_enum = None
    if stain_type:
        try:
            stain_enum = StainType(stain_type)
        except ValueError:
            pass

    images = catalog.list_images(organ_system=organ_system, stain_type=stain_enum, search=search)
    return {
        "total": len(images),
        "items": [img.to_dict() for img in images],
    }


@router.get("/images/{image_id}")
def get_pathology_image(image_id: str):
    """Retrieves a single pathology image asset with high-resolution metadata."""
    img = catalog.get_image(image_id)
    if not img:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pathology image '{image_id}' not found in catalog.",
        )
    return img.to_dict()


@router.post("/generate")
def generate_multimodal_question(
    req: MultimodalGenerationApiRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUESTIONS_EDIT)),
):
    """
    Synthesizes vision-grounded multiple-choice questions anchored on pathology images.
    """
    image_asset = catalog.get_image(req.image_id) if req.image_id else None
    if req.image_id and not image_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image ID '{req.image_id}' not found.",
        )

    blueprint = MultimodalQuestionBlueprint(
        topic=req.topic,
        learning_objective=req.learning_objective,
        difficulty=req.difficulty,
        cognitive_level=req.cognitive_level,
        target_exam=req.target_exam,
        target_image_id=req.image_id,
    )

    try:
        mcq = multimodal_generator.generate_image_mcq(blueprint=blueprint, image_asset=image_asset)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Multimodal generation failed: {str(e)}",
        )

    # Format options
    opt_dicts = [
        {
            "id": opt.key,
            "text": opt.text,
            "is_correct": opt.is_correct,
            "rationale": opt.rationale,
        }
        for opt in mcq.options
    ]

    exact_stem_hash = hashlib.sha256(mcq.stem.encode("utf-8")).hexdigest()
    norm_stem_hash = hashlib.sha256(" ".join(mcq.stem.lower().split()).encode("utf-8")).hexdigest()
    content_hash = hashlib.sha256(f"{mcq.stem}|{mcq.correct_option}".encode("utf-8")).hexdigest()

    question = Question(
        id=str(uuid.uuid4()),
        external_source="MULTIMODAL_AI",
        external_source_id=f"mm-gen-{uuid.uuid4().hex[:12]}",
        speciality="Pathology",
        subject="Surgical Pathology",
        topic_name_original=req.topic,
        topic_name_normalized=req.topic.lower().strip(),
        topic_mapping_status=TopicMappingStatus.MAPPED,
        learning_objective=req.learning_objective,
        question_type=QuestionType.CASE_BASED,
        stem=mcq.stem,
        options=opt_dicts,
        correct_option=mcq.correct_option,
        correct_index=0,
        is_labeled=True,
        explanation=mcq.explanation,
        difficulty=DifficultyLevel(req.difficulty.lower()) if req.difficulty.lower() in [e.value for e in DifficultyLevel] else DifficultyLevel.MEDIUM,
        cognitive_level=CognitiveLevel(req.cognitive_level.lower()) if req.cognitive_level.lower() in [e.value for e in CognitiveLevel] else CognitiveLevel.APPLICATION,
        target_exam_levels=[req.target_exam],
        status=QuestionStatus.GENERATED,
        quality_score=0.95,
        classification_source=ClassificationSource.AI_CLASSIFIED,
        classification_status=ClassificationStatus.PENDING_REVIEW,
        classification_confidence=0.98,
        knowledge_era="CURRENT",
        origin_cohort="MULTIMODAL_IMAGE_MCQ",
        tags=["MULTIMODAL_IMAGE_MCQ", "HISTOLOGY_VIGNETTE", req.topic.upper()],
        has_images=True,
        image_assets=mcq.metadata.get("image_assets", []),
        content_hash=content_hash,
        exact_stem_hash=exact_stem_hash,
        norm_stem_hash=norm_stem_hash,
        metadata_json={
            "citations": mcq.citations,
            "generator": "multimodal_pathology_engine",
        },
        created_by="multimodal_image_generator",
    )

    db.add(question)
    db.commit()
    db.refresh(question)

    return {
        "status": "success",
        "question_id": question.id,
        "stem": question.stem,
        "options": question.options,
        "correct_option": question.correct_option,
        "explanation": question.explanation,
        "has_images": question.has_images,
        "image_assets": question.image_assets,
        "origin_cohort": question.origin_cohort,
    }
