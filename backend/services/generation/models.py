"""
backend/services/generation/models.py

Domain models and Pydantic schemas for the Evidence-Grounded AI Question Generation Subsystem.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TargetExam(str, Enum):
    NEET_PG = "NEET_PG"
    NEET_SS = "NEET_SS"
    INICET = "INICET"
    MD_PATHOLOGY = "MD_PATHOLOGY"
    USMLE_STEP1 = "USMLE_STEP1"


class CognitiveLevelEnum(str, Enum):
    RECALL = "RECALL"
    UNDERSTANDING = "UNDERSTANDING"
    APPLICATION = "APPLICATION"
    ANALYSIS = "ANALYSIS"


class DifficultyEnum(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class QuestionTypeEnum(str, Enum):
    SINGLE_BEST_ANSWER = "SINGLE_BEST_ANSWER"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    CASE_BASED = "CASE_BASED"


@dataclass
class QuestionBlueprint:
    """
    Blueprint specification used to retrieve targeted evidence and generate questions.
    """
    topic: str
    learning_objective: str
    speciality: str = "Pathology"
    subject: str = "General Pathology"
    subtopic: Optional[str] = None
    target_exam: str = "NEET_PG"
    difficulty: str = "MEDIUM"
    cognitive_level: str = "APPLICATION"
    question_type: str = "SINGLE_BEST_ANSWER"
    source_requirements: List[str] = field(default_factory=lambda: ["robbins_pathologic_basis_11th"])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class QuestionBlueprintRequest(BaseModel):
    """Pydantic schema for API requests initiating question generation."""
    topic: str = Field(..., min_length=2, description="Pathology topic (e.g. 'Breast Carcinoma')")
    learning_objective: str = Field(..., min_length=5, description="Specific learning objective (e.g. 'HER2 testing and ISH equivocal criteria')")
    speciality: str = Field(default="Pathology")
    subject: str = Field(default="General Pathology")
    subtopic: Optional[str] = Field(default=None)
    target_exam: str = Field(default="NEET_PG")
    difficulty: str = Field(default="MEDIUM")
    cognitive_level: str = Field(default="APPLICATION")
    question_type: str = Field(default="SINGLE_BEST_ANSWER")
    count: int = Field(default=1, ge=1, le=10, description="Number of questions to generate")


@dataclass
class GeneratedOption:
    key: str  # "A", "B", "C", "D"
    text: str
    is_correct: bool
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GeneratedMCQPayload:
    stem: str
    options: List[GeneratedOption]
    correct_option: str  # "A", "B", "C", "D"
    explanation: str
    learning_objective: str
    difficulty: str
    cognitive_level: str
    question_type: str
    evidence_chunk_ids: List[str]
    citations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stem": self.stem,
            "options": [opt.to_dict() for opt in self.options],
            "correct_option": self.correct_option,
            "explanation": self.explanation,
            "learning_objective": self.learning_objective,
            "difficulty": self.difficulty,
            "cognitive_level": self.cognitive_level,
            "question_type": self.question_type,
            "evidence_chunk_ids": self.evidence_chunk_ids,
            "citations": self.citations,
            "metadata": self.metadata,
        }


@dataclass
class EvaluationCheck:
    name: str
    passed: bool
    score: float
    details: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluationResult:
    overall_score: float
    passed: bool
    checks: List[EvaluationCheck]
    status_assigned: str  # "GENERATED", "AI_REVIEW", "REJECTED"
    reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "passed": self.passed,
            "checks": [c.to_dict() for c in self.checks],
            "status_assigned": self.status_assigned,
            "reasons": self.reasons,
        }
