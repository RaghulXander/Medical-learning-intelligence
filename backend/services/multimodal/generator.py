"""
backend/services/multimodal/generator.py

Vision-Grounded Multimodal Pathology MCQ Generator.
Synthesizes image-anchored clinical vignette MCQs with attached histology/IHC assets.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from backend.services.generation.models import GeneratedMCQPayload, GeneratedOption
from backend.services.multimodal.image_catalog import get_image_catalog
from backend.services.multimodal.models import (
    MultimodalQuestionBlueprint,
    PathologyImageAsset,
)

logger = logging.getLogger(__name__)


class MultimodalMCQGenerator:
    """
    Generator creating vision-grounded multiple-choice questions anchored on pathology image assets.
    """

    def __init__(self, force_mock: bool = False):
        self.force_mock = force_mock
        self.catalog = get_image_catalog()

    def generate_image_mcq(
        self,
        blueprint: MultimodalQuestionBlueprint,
        image_asset: Optional[PathologyImageAsset] = None,
    ) -> GeneratedMCQPayload:
        """
        Generates an image-anchored question from blueprint and image asset.
        """
        # Resolve target image asset
        if image_asset is None:
            if blueprint.target_image_id:
                image_asset = self.catalog.get_image(blueprint.target_image_id)
            else:
                matches = self.catalog.list_images(organ_system=blueprint.topic)
                image_asset = matches[0] if matches else self.catalog.list_images()[0]

        if not image_asset:
            raise ValueError("No matching pathology image found in catalog to generate multimodal question.")

        # Construct Image-anchored Vignette
        stem = (
            f"A patient undergoes diagnostic tissue sampling for evaluation of an abnormal lesion in the {image_asset.organ_system.lower()}. "
            f"The representative microscopic and immunohistochemical findings are illustrated in the attached image ({image_asset.stain_type.value} stain, {image_asset.magnification.value} magnification). "
            f"Based on the characteristic morphological and immunophenotypic features shown, which of the following is the most accurate diagnostic interpretation?"
        )

        correct_text = f"{image_asset.diagnosis} with {image_asset.diagnostic_features[0].lower()}."
        distractor_1 = "Benign reactive hyperplasia without cellular atypia or architecture distortion."
        distractor_2 = "Undifferentiated high-grade sarcoma requiring complete wide surgical margin excision."
        distractor_3 = "Metastatic adenoid cystic carcinoma displaying basaloid cribriform architecture."

        options = [
            GeneratedOption(
                key="A",
                text=correct_text,
                is_correct=True,
                rationale=f"Correct. As demonstrated in {image_asset.source_citation}: {image_asset.caption}",
            ),
            GeneratedOption(
                key="B",
                text=distractor_1,
                is_correct=False,
                rationale="Incorrect. The morphological hallmarks and stain patterns definitively indicate a malignant process.",
            ),
            GeneratedOption(
                key="C",
                text=distractor_2,
                is_correct=False,
                rationale="Incorrect. The architectural pattern and specific stain expression rule out undifferentiated sarcoma.",
            ),
            GeneratedOption(
                key="D",
                text=distractor_3,
                is_correct=False,
                rationale="Incorrect. Cribriform basaloid features and myoepithelial differentiation are not present.",
            ),
        ]

        explanation = (
            f"Visual Diagnostic Breakdown:\n"
            f"- Image Caption: {image_asset.caption}\n"
            f"- Key Diagnostic Features: {'; '.join(image_asset.diagnostic_features)}\n"
            f"- Reference Citation: {image_asset.source_citation}\n\n"
            f"Option A is correct. Options B, C, and D are excluded based on the visual immunophenotype."
        )

        return GeneratedMCQPayload(
            stem=stem,
            options=options,
            correct_option="A",
            explanation=explanation,
            learning_objective=blueprint.learning_objective,
            difficulty=blueprint.difficulty,
            cognitive_level=blueprint.cognitive_level,
            question_type=blueprint.question_type,
            evidence_chunk_ids=[],
            citations=[image_asset.source_citation],
            metadata={
                "has_images": True,
                "image_assets": [image_asset.to_dict()],
                "origin_cohort": "MULTIMODAL_IMAGE_MCQ",
                "tags": ["MULTIMODAL_IMAGE_MCQ", "HISTOLOGY_VIGNETTE", image_asset.organ_system.upper()],
            },
        )
