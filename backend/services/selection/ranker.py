"""
backend/services/selection/ranker.py

Soft Ranking Layer for Milestone 6.
Applies transparent, explainable scoring formulas combining weakness, repeated mistakes,
exploration, difficulty fit, and discrete recency penalties.
"""

from typing import List, Optional
from database.models import DifficultyLevel
from backend.services.selection.models import (
    BlueprintConfig,
    CandidateQuestion,
    SelectionPolicy,
)


class QuestionRanker:
    """
    Computes priority scores and attaches transparent selection reasons to candidates.
    """

    @classmethod
    def calculate_recency_penalty(
        cls,
        days_since_seen: Optional[float],
        policy: SelectionPolicy,
    ) -> float:
        """
        Computes discrete recency penalty based on time elapsed since last exposure.
        """
        if days_since_seen is None:
            return 0.0  # Unseen question has zero recency penalty

        if days_since_seen < 1.0:
            return policy.day_0_recency_penalty
        elif days_since_seen < 4.0:
            return policy.days_1_3_recency_penalty
        elif days_since_seen < 8.0:
            return policy.days_4_7_recency_penalty
        elif days_since_seen < 15.0:
            return policy.days_8_14_recency_penalty
        else:
            return policy.days_15_plus_recency_penalty

    @classmethod
    def score_candidate(
        cls,
        c: CandidateQuestion,
        blueprint: BlueprintConfig,
    ) -> float:
        """
        Computes the priority score and populates selection_reasons for a candidate question.
        """
        policy = blueprint.selection_policy or SelectionPolicy.get_preset_for_mode(blueprint.assessment_mode)
        reasons: List[str] = []

        # 1. Weakness Signal (0 - 100)
        # Topics with lower accuracy produce higher remediation scores
        acc = c.smoothed_node_accuracy if c.smoothed_node_accuracy is not None else 50.0
        weakness_score = max(0.0, 100.0 - acc)
        if acc < 45.0:
            reasons.append("WEAK_TOPIC_REMEDIATION")

        # 2. Repeated Mistake Signal (0 - 100)
        err_score = 0.0
        if c.consecutive_errors >= 2:
            err_score = min(100.0, (c.consecutive_errors * 35.0) + (c.historical_error_count * 15.0))
            reasons.append("REPEATED_MISTAKE_PRIORITY")
        elif c.consecutive_errors == 1:
            err_score = 40.0
            reasons.append("PREVIOUS_ERROR_REVIEW")

        # 3. New Question Exploration Signal (0 - 100)
        exploration_score = 0.0
        if c.is_unseen:
            exploration_score = 80.0
            reasons.append("NEW_QUESTION_EXPLORATION")

        # 4. Difficulty Fit Signal (0 - 50)
        difficulty_score = 0.0
        q_diff = c.question.difficulty.value.upper() if c.question.difficulty else "MEDIUM"
        if blueprint.difficulty_distribution:
            target_diffs = [d.upper() for d in blueprint.difficulty_distribution.keys()]
            if q_diff in target_diffs:
                difficulty_score = 50.0
                reasons.append("DIFFICULTY_TARGET_MATCH")
        else:
            difficulty_score = 25.0

        # 5. Penalties
        recency_penalty = cls.calculate_recency_penalty(c.days_since_seen, policy)
        if recency_penalty > 50.0:
            reasons.append("RECENT_EXPOSURE_PENALTY")

        unknown_penalty = 0.0
        if c.classification_source == "UNKNOWN":
            unknown_penalty = policy.unknown_metadata_penalty
            reasons.append("UNKNOWN_METADATA_PENALTY")

        # 6. Weighted Sum Formulation
        # Priority Score = Personalized Remediation + Exploration + Difficulty Fit - Penalties
        personalization_component = (
            (policy.remediation_weight * weakness_score)
            + (policy.personalization_weight * err_score)
        )
        exploration_component = policy.new_question_weight * exploration_score
        difficulty_component = policy.difficulty_weight * difficulty_score
        penalty_component = (policy.recency_penalty_weight * recency_penalty) + unknown_penalty

        raw_score = (
            personalization_component
            + exploration_component
            + difficulty_component
            - penalty_component
        )

        if not reasons:
            reasons.append("EXAM_BLUEPRINT_CORE")

        c.priority_score = round(raw_score, 3)
        c.selection_reasons = reasons
        return c.priority_score

    @classmethod
    def rank_candidates(
        cls,
        candidates: List[CandidateQuestion],
        blueprint: BlueprintConfig,
    ) -> List[CandidateQuestion]:
        """
        Ranks all candidate questions by priority score in descending order.
        """
        for c in candidates:
            cls.score_candidate(c, blueprint)

        # Sort descending by priority_score
        return sorted(candidates, key=lambda x: x.priority_score, reverse=True)
