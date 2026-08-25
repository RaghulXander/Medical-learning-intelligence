"""
backend/services/selection/models.py

Data structures, dataclasses, and exceptions for the Intelligent Question Selection Layer (M6).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from database.models import Question


class SelectionError(Exception):
    """Base exception for question selection errors."""
    pass


class InsufficientQuestionPoolError(SelectionError):
    """Raised when the eligible question pool cannot satisfy the requested blueprint."""
    def __init__(self, message: str, required_count: int, eligible_count: int, deficit: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.required_count = required_count
        self.eligible_count = eligible_count
        self.deficit = deficit
        self.details = details or {}


class InvalidBlueprintError(SelectionError):
    """Raised when the assessment blueprint is structurally or logically invalid."""
    pass


@dataclass
class SelectionPolicy:
    """Configurable weights and discrete penalties for soft ranking and mode tuning."""
    personalization_weight: float = 0.30
    remediation_weight: float = 0.25
    new_question_weight: float = 0.15
    recency_penalty_weight: float = 0.15
    difficulty_weight: float = 0.15
    unknown_metadata_penalty: float = 25.0
    min_metadata_confidence: float = 0.50
    
    # Discrete recency penalty tiers (configurable, not prematurely hardcoded)
    day_0_recency_penalty: float = 100.0
    days_1_3_recency_penalty: float = 60.0
    days_4_7_recency_penalty: float = 30.0
    days_8_14_recency_penalty: float = 10.0
    days_15_plus_recency_penalty: float = 0.0

    @classmethod
    def get_preset_for_mode(cls, mode: str) -> "SelectionPolicy":
        """Returns specialized weight presets based on assessment mode."""
        m = (mode or "PRACTICE").upper()
        if m == "LEARNING":
            return cls(
                personalization_weight=0.45,
                remediation_weight=0.35,
                new_question_weight=0.10,
                recency_penalty_weight=0.20,
                difficulty_weight=0.10,
            )
        elif m == "MOCK":
            return cls(
                personalization_weight=0.15,
                remediation_weight=0.10,
                new_question_weight=0.20,
                recency_penalty_weight=0.15,
                difficulty_weight=0.40,
            )
        elif m == "GRAND_TEST":
            return cls(
                personalization_weight=0.05,
                remediation_weight=0.05,
                new_question_weight=0.35,
                recency_penalty_weight=0.15,
                difficulty_weight=0.40,
            )
        else:  # PRACTICE / DEFAULT
            return cls(
                personalization_weight=0.30,
                remediation_weight=0.25,
                new_question_weight=0.15,
                recency_penalty_weight=0.15,
                difficulty_weight=0.15,
            )


@dataclass
class BlueprintConfig:
    """Normalized, validated configuration derived from an Assessment blueprint."""
    question_count: int = 10
    target_exam: Optional[str] = None
    educational_levels: List[str] = field(default_factory=list)
    speciality: str = "Pathology"
    subject: Optional[str] = None
    topic_ids: List[str] = field(default_factory=list)
    topic_distribution: Dict[str, int] = field(default_factory=dict)
    difficulty_distribution: Dict[str, int] = field(default_factory=dict)
    cognitive_distribution: Dict[str, int] = field(default_factory=dict)
    assessment_mode: str = "PRACTICE"
    strict_metadata_mode: bool = False
    min_confidence_threshold: float = 0.50
    seed: Optional[int] = None
    selection_policy: SelectionPolicy = field(default_factory=SelectionPolicy)


@dataclass
class CandidateQuestion:
    """Wrapper tracking question metadata, learner history signals, and ranking scores."""
    question: Question
    effective_educational_level: Optional[str] = None
    classification_source: str = "UNKNOWN"
    classification_confidence: float = 1.0
    is_eligible: bool = True
    ineligibility_reasons: List[str] = field(default_factory=list)
    historical_error_count: int = 0
    consecutive_errors: int = 0
    days_since_seen: Optional[float] = None
    is_unseen: bool = True
    smoothed_node_accuracy: Optional[float] = None
    priority_score: float = 0.0
    selection_reasons: List[str] = field(default_factory=list)


@dataclass
class QuestionSelectionResult:
    """The final result of the question selection pipeline."""
    selected_questions: List[Question]
    selection_reasons_map: Dict[str, List[str]]
    priority_scores_map: Dict[str, float]
    total_eligible_count: int
    topic_breakdown: Dict[str, int]
    difficulty_breakdown: Dict[str, int]
    educational_level_breakdown: Dict[str, int]
    warnings: List[str] = field(default_factory=list)
