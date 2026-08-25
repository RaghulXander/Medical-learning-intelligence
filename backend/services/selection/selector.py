"""
backend/services/selection/selector.py

Main Orchestrator for the Intelligent Question Selection Layer (Milestone 6).
Coordinates blueprint parsing, hard eligibility filtering, learner model enrichment,
soft priority ranking, distribution balancing, diversity deduplication, and explainable auditing.
"""

import random
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session
from database.models import Question
from backend.services.selection.models import (
    BlueprintConfig,
    CandidateQuestion,
    QuestionSelectionResult,
    SelectionPolicy,
    InvalidBlueprintError,
    InsufficientQuestionPoolError,
)
from backend.services.selection.eligibility import HardEligibilityFilter
from backend.services.selection.learner_model import LearnerModelService
from backend.services.selection.ranker import QuestionRanker
from backend.services.selection.diversity import DiversityController


class UniversalQuestionSelector:
    """
    Universal Question Selection Service interpreting declarative blueprints
    and learner history to deterministically construct tailored assessments.
    """

    @classmethod
    def parse_blueprint(
        cls,
        blueprint: Union[Dict[str, Any], BlueprintConfig],
        default_count: int = 10,
    ) -> BlueprintConfig:
        """
        Parses and validates a raw blueprint dictionary into a strongly typed BlueprintConfig.
        """
        if isinstance(blueprint, BlueprintConfig):
            return blueprint

        if not isinstance(blueprint, dict):
            raise InvalidBlueprintError("Blueprint must be a dictionary or BlueprintConfig instance.")

        q_count = int(blueprint.get("question_count") or default_count)
        if q_count <= 0:
            raise InvalidBlueprintError(f"question_count must be a positive integer, got {q_count}.")

        # Parse educational levels
        edu_levels = blueprint.get("educational_level") or blueprint.get("educational_levels") or []
        if isinstance(edu_levels, str):
            edu_levels = [edu_levels]

        # Parse topics
        topic_ids = blueprint.get("topic_ids") or []
        if "topic_id" in blueprint and blueprint["topic_id"]:
            topic_ids.append(blueprint["topic_id"])
        topic_dist = blueprint.get("topic_distribution") or blueprint.get("topics") or {}

        # Parse difficulty
        diff_dist = blueprint.get("difficulty_distribution") or blueprint.get("difficulty") or {}

        # Mode & Policies
        mode = (blueprint.get("assessment_mode") or blueprint.get("mode") or "PRACTICE").upper()
        strict_meta = bool(blueprint.get("strict_metadata_mode", False))
        min_conf = float(blueprint.get("min_confidence_threshold", 0.50))
        seed = blueprint.get("seed")
        if seed is not None:
            seed = int(seed)

        # Policy overrides if provided
        policy_dict = blueprint.get("selection_policy") or {}
        policy = SelectionPolicy.get_preset_for_mode(mode)
        if policy_dict:
            for k, v in policy_dict.items():
                if hasattr(policy, k):
                    setattr(policy, k, float(v))

        return BlueprintConfig(
            question_count=q_count,
            target_exam=blueprint.get("target_exam"),
            educational_levels=edu_levels,
            speciality=blueprint.get("speciality", "Pathology"),
            subject=blueprint.get("subject"),
            topic_ids=topic_ids,
            topic_distribution=topic_dist,
            difficulty_distribution=diff_dist,
            cognitive_distribution=blueprint.get("cognitive_distribution") or {},
            assessment_mode=mode,
            strict_metadata_mode=strict_meta,
            min_confidence_threshold=min_conf,
            seed=seed,
            selection_policy=policy,
        )

    @classmethod
    def select_questions(
        cls,
        db: Session,
        blueprint: Union[Dict[str, Any], BlueprintConfig],
        user_id: Optional[str] = None,
        default_count: int = 10,
    ) -> QuestionSelectionResult:
        """
        Executes the full Intelligent Question Selection Pipeline:
        1. Parse & Validate Blueprint
        2. Set Seed (if specified) for deterministic reproducibility
        3. Hard Eligibility Filtering (Exam level, course, specialty, status)
        4. Validate Candidate Pool Sufficiency
        5. Enrich Candidates with Learner Model History
        6. Soft Priority Ranking
        7. Blueprint Distribution Balancing
        8. Diversity & Deduplication Control
        9. Generate Explainable Selection Result
        """
        cfg = cls.parse_blueprint(blueprint, default_count)

        # Apply deterministic seed if present
        if cfg.seed is not None:
            random.seed(cfg.seed)

        # Step 3: Hard Eligibility Filter
        eligible_candidates, ineligible_candidates = HardEligibilityFilter.filter_candidates(db, cfg)

        # Step 4: Validate Pool Sufficiency
        HardEligibilityFilter.check_pool_sufficiency(eligible_candidates, cfg)

        # Step 5: Learner Model Enrichment
        LearnerModelService.enrich_candidates(db, eligible_candidates, user_id)

        # Step 6 & 7: Ranking & Distribution Balancing
        selected_candidates: List[CandidateQuestion] = []
        warnings: List[str] = []

        if cfg.topic_distribution:
            # Partitioned by topic
            topic_buckets: Dict[str, List[CandidateQuestion]] = {}
            for c in eligible_candidates:
                t_id = c.question.primary_topic_id or "UNASSIGNED"
                if t_id not in topic_buckets:
                    topic_buckets[t_id] = []
                topic_buckets[t_id].append(c)

            for req_topic, req_count in cfg.topic_distribution.items():
                bucket = topic_buckets.get(req_topic, [])
                ranked_bucket = QuestionRanker.rank_candidates(bucket, cfg)
                picked = DiversityController.deduplicate(ranked_bucket, req_count)
                selected_candidates.extend(picked)

        elif cfg.difficulty_distribution:
            # Partitioned by difficulty
            diff_buckets: Dict[str, List[CandidateQuestion]] = {}
            for c in eligible_candidates:
                d_val = c.question.difficulty.value.upper() if c.question.difficulty else "MEDIUM"
                if d_val not in diff_buckets:
                    diff_buckets[d_val] = []
                diff_buckets[d_val].append(c)

            for req_diff, req_count in cfg.difficulty_distribution.items():
                bucket = diff_buckets.get(req_diff.upper(), [])
                ranked_bucket = QuestionRanker.rank_candidates(bucket, cfg)
                picked = DiversityController.deduplicate(ranked_bucket, req_count)
                selected_candidates.extend(picked)

        # Fill remaining slots up to question_count from global ranked candidates
        remaining_needed = cfg.question_count - len(selected_candidates)
        if remaining_needed > 0:
            already_picked_ids = {c.question.id for c in selected_candidates}
            remaining_pool = [c for c in eligible_candidates if c.question.id not in already_picked_ids]
            ranked_remaining = QuestionRanker.rank_candidates(remaining_pool, cfg)
            picked_remaining = DiversityController.deduplicate(ranked_remaining, remaining_needed)
            selected_candidates.extend(picked_remaining)

        # Fallback deduplication pass on entire selection
        final_candidates = DiversityController.deduplicate(selected_candidates, cfg.question_count)

        if len(final_candidates) < cfg.question_count:
            deficit = cfg.question_count - len(final_candidates)
            raise InsufficientQuestionPoolError(
                message=f"Could not fulfill complete question count after diversity filters: got {len(final_candidates)} of {cfg.question_count}.",
                required_count=cfg.question_count,
                eligible_count=len(final_candidates),
                deficit=deficit,
            )

        # Step 8: Build Result Breakdown & Maps
        final_questions = [c.question for c in final_candidates]
        reasons_map = {c.question.id: c.selection_reasons for c in final_candidates}
        scores_map = {c.question.id: c.priority_score for c in final_candidates}

        topic_breakdown: Dict[str, int] = {}
        diff_breakdown: Dict[str, int] = {}
        edu_breakdown: Dict[str, int] = {}

        for c in final_candidates:
            t = c.question.primary_topic_id or "UNASSIGNED"
            topic_breakdown[t] = topic_breakdown.get(t, 0) + 1

            d = c.question.difficulty.value if c.question.difficulty else "medium"
            diff_breakdown[d] = diff_breakdown.get(d, 0) + 1

            lvl = c.effective_educational_level or "UNKNOWN"
            edu_breakdown[lvl] = edu_breakdown.get(lvl, 0) + 1

        return QuestionSelectionResult(
            selected_questions=final_questions,
            selection_reasons_map=reasons_map,
            priority_scores_map=scores_map,
            total_eligible_count=len(eligible_candidates),
            topic_breakdown=topic_breakdown,
            difficulty_breakdown=diff_breakdown,
            educational_level_breakdown=edu_breakdown,
            warnings=warnings,
        )
