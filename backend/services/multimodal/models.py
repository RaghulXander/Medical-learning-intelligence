"""
backend/services/multimodal/models.py

Domain models and schemas for the Multimodal Pathology Image Engine.
Supports histology microscopic slides, IHC stain panels, cytology, and gross pathology.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.services.generation.models import (
    GeneratedMCQPayload,
    GeneratedOption,
    QuestionBlueprint,
)


class StainType(str, Enum):
    HE = "H&E"
    IHC_HER2 = "IHC_HER2"
    IHC_KI67 = "IHC_KI67"
    IHC_ER_PR = "IHC_ER_PR"
    IHC_CD30_CD15 = "IHC_CD30_CD15"
    PAS = "PAS"
    CONGO_RED = "CONGO_RED"
    GIEMSA = "GIEMSA"
    PAP = "PAP"
    GROSS_SURGICAL = "GROSS_SURGICAL"
    CYTOLOGY = "CYTOLOGY"
    ELECTRON_MICROSCOPY = "ELECTRON_MICROSCOPY"


class MagnificationLevel(str, Enum):
    GROSS = "GROSS"
    SCAN_4X = "4X"
    LOW_10X = "10X"
    MED_20X = "20X"
    HIGH_40X = "40X"
    OIL_100X = "100X"


@dataclass
class PathologyImageAsset:
    """Pathology image artifact with morphological metadata and citation provenance."""

    image_id: str
    title: str
    file_path: str
    stain_type: StainType
    magnification: MagnificationLevel
    organ_system: str
    diagnosis: str
    source_citation: str
    caption: str
    diagnostic_features: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_id": self.image_id,
            "title": self.title,
            "file_path": self.file_path,
            "stain_type": self.stain_type.value if hasattr(self.stain_type, "value") else str(self.stain_type),
            "magnification": self.magnification.value if hasattr(self.magnification, "value") else str(self.magnification),
            "organ_system": self.organ_system,
            "diagnosis": self.diagnosis,
            "source_citation": self.source_citation,
            "caption": self.caption,
            "diagnostic_features": self.diagnostic_features,
            "metadata": self.metadata,
        }


@dataclass
class MultimodalQuestionBlueprint(QuestionBlueprint):
    """Question Blueprint extended with image and stain requirements."""

    target_image_id: Optional[str] = None
    required_stain: Optional[StainType] = None
    min_magnification: Optional[MagnificationLevel] = None


class MultimodalGenerationApiRequest(BaseModel):
    image_id: Optional[str] = Field(default=None, description="Specific catalog image ID to anchor question")
    topic: str = Field(default="Breast Pathology", description="Pathology organ or topic")
    learning_objective: str = Field(default="Morphological diagnosis and immunohistochemical correlation")
    difficulty: str = Field(default="MEDIUM")
    cognitive_level: str = Field(default="APPLICATION")
    target_exam: str = Field(default="NEET_SS")
    force_mock: bool = Field(default=False)
