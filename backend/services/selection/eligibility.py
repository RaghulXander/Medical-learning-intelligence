"""
backend/services/selection/eligibility.py

Hard Eligibility Filtering Layer for Milestone 6.
Ensures hard educational level, exam target, specialty, curriculum, and status rules
strictly gate the candidate pool before soft personalization.
"""

from typing import List, Optional, Tuple, Set
from sqlalchemy.orm import Session, joinedload
from database.models import (
    Question,
    QuestionStatus,
    DepthLevel,
    EducationalLevel,
    ClassificationSource,
    CurriculumTopic,
    CourseCurriculumMapping,
)
from backend.services.selection.models import (
    BlueprintConfig,
    CandidateQuestion,
    InsufficientQuestionPoolError,
)


class HardEligibilityFilter:
    """
    Evaluates questions against non-negotiable examination and curriculum eligibility gates.
    """

    @classmethod
    def evaluate_question(
        cls,
        q: Question,
        blueprint: BlueprintConfig,
    ) -> CandidateQuestion:
        """
        Evaluates a single question against all hard eligibility rules.
        Applies cascading classification fallback (KNOWN -> INFERRED -> UNKNOWN).
        """
        ineligibility_reasons: List[str] = []

        # 1. Status Filter (Only APPROVED questions in exams)
        if q.status != QuestionStatus.APPROVED:
            ineligibility_reasons.append(f"STATUS_{q.status.value}_NOT_APPROVED")

        # 2. Specialty Filter
        if blueprint.speciality and q.speciality.strip().lower() != blueprint.speciality.strip().lower():
            ineligibility_reasons.append(f"SPECIALITY_MISMATCH_{q.speciality}_VS_{blueprint.speciality}")

        # 3. Topic Scope Filter
        requested_topics = set(blueprint.topic_ids)
        if blueprint.topic_distribution:
            requested_topics.update(blueprint.topic_distribution.keys())

        if requested_topics:
            if not q.primary_topic_id or q.primary_topic_id not in requested_topics:
                ineligibility_reasons.append(f"TOPIC_OUT_OF_SCOPE_{q.primary_topic_id}")

        # 4. Cascading Educational Level & Exam Target Inference
        effective_level: Optional[str] = None
        source: str = q.classification_source.value if hasattr(q.classification_source, "value") else str(q.classification_source)
        confidence: float = q.classification_confidence or 1.0

        if q.educational_level and source != "UNKNOWN":
            effective_level = q.educational_level.value if hasattr(q.educational_level, "value") else str(q.educational_level)
            source = "KNOWN"
        elif (
            source == "CURRICULUM_INFERENCE"
            and q.primary_topic
            and hasattr(q.primary_topic, "course_mappings")
            and q.primary_topic.course_mappings
        ):
            # Inferred from curriculum course mapping depths
            depths = [cm.depth_level for cm in q.primary_topic.course_mappings if cm.depth_level]
            if DepthLevel.SUPER_SPECIALTY in depths:
                effective_level = EducationalLevel.SUPER_SPECIALTY.value
                source = "CURRICULUM_INFERENCE"
                confidence = min(confidence, 0.85)
            elif DepthLevel.POSTGRADUATE in depths:
                effective_level = EducationalLevel.MD.value
                source = "CURRICULUM_INFERENCE"
                confidence = min(confidence, 0.85)
            elif DepthLevel.UNDERGRADUATE in depths:
                effective_level = EducationalLevel.MBBS.value
                source = "CURRICULUM_INFERENCE"
                confidence = min(confidence, 0.80)
        else:
            effective_level = "UNKNOWN"
            source = "UNKNOWN"
            confidence = min(confidence, 0.50)

        # 5. Examination Level & Educational Level Precedence Gates
        target_exam = (blueprint.target_exam or "").upper()
        
        # Rule: NEET-SS strictly excludes MBBS-level questions
        if target_exam == "NEET_SS":
            if effective_level == EducationalLevel.MBBS.value:
                ineligibility_reasons.append("NEET_SS_EXCLUDES_MBBS_LEVEL")
        
        # Rule: Explicit Educational Level Filter
        if blueprint.educational_levels:
            req_levels = [lvl.upper() for lvl in blueprint.educational_levels]
            if effective_level != "UNKNOWN" and effective_level.upper() not in req_levels:
                ineligibility_reasons.append(f"EDUCATIONAL_LEVEL_MISMATCH_{effective_level}_NOT_IN_{req_levels}")

        # Rule: Target Exam Levels match if question has target_exam_levels explicitly tagged
        if q.target_exam_levels and target_exam:
            q_exams = [e.upper() for e in q.target_exam_levels]
            if target_exam not in q_exams and "ALL" not in q_exams:
                # If question explicitly targets other exams and not this target_exam
                if len(q_exams) > 0:
                    ineligibility_reasons.append(f"TARGET_EXAM_MISMATCH_{q_exams}_DOES_NOT_INCLUDE_{target_exam}")

        # 6. Strict Metadata Mode Gate
        if blueprint.strict_metadata_mode:
            if source == "UNKNOWN":
                ineligibility_reasons.append("STRICT_METADATA_EXCLUDES_UNKNOWN")
            elif confidence < blueprint.min_confidence_threshold:
                ineligibility_reasons.append(f"CONFIDENCE_{confidence}_BELOW_THRESHOLD_{blueprint.min_confidence_threshold}")

        is_eligible = len(ineligibility_reasons) == 0

        return CandidateQuestion(
            question=q,
            effective_educational_level=effective_level,
            classification_source=source,
            classification_confidence=confidence,
            is_eligible=is_eligible,
            ineligibility_reasons=ineligibility_reasons,
        )

    @classmethod
    def filter_candidates(
        cls,
        db: Session,
        blueprint: BlueprintConfig,
    ) -> Tuple[List[CandidateQuestion], List[CandidateQuestion]]:
        """
        Fetches active question candidates from the database and filters them through hard eligibility gates.
        Returns (eligible_candidates, ineligible_candidates).
        """
        query = db.query(Question).options(
            joinedload(Question.primary_topic).joinedload(CurriculumTopic.course_mappings)
        )

        # Baseline query filter on approved status & speciality
        query = query.filter(Question.status == QuestionStatus.APPROVED)
        if blueprint.speciality:
            query = query.filter(Question.speciality.ilike(blueprint.speciality.strip()))

        raw_questions = query.all()

        eligible: List[CandidateQuestion] = []
        ineligible: List[CandidateQuestion] = []

        for q in raw_questions:
            cand = cls.evaluate_question(q, blueprint)
            if cand.is_eligible:
                eligible.append(cand)
            else:
                ineligible.append(cand)

        return eligible, ineligible

    @classmethod
    def check_pool_sufficiency(
        cls,
        eligible_candidates: List[CandidateQuestion],
        blueprint: BlueprintConfig,
    ) -> None:
        """
        Validates whether eligible candidates can satisfy total count and individual topic constraints.
        Raises InsufficientQuestionPoolError if count is deficient.
        """
        total_eligible = len(eligible_candidates)
        required = blueprint.question_count

        if total_eligible < required:
            deficit = required - total_eligible
            raise InsufficientQuestionPoolError(
                message=f"Insufficient question pool: required {required} questions, but only {total_eligible} eligible questions found (shortage of {deficit}).",
                required_count=required,
                eligible_count=total_eligible,
                deficit=deficit,
                details={"target_exam": blueprint.target_exam, "speciality": blueprint.speciality},
            )

        # Check topic-specific distribution sufficiency
        if blueprint.topic_distribution:
            topic_counts = {}
            for c in eligible_candidates:
                t_id = c.question.primary_topic_id or "UNASSIGNED"
                topic_counts[t_id] = topic_counts.get(t_id, 0) + 1

            for req_topic, req_count in blueprint.topic_distribution.items():
                avail = topic_counts.get(req_topic, 0)
                if avail < req_count:
                    deficit = req_count - avail
                    raise InsufficientQuestionPoolError(
                        message=f"Insufficient questions for topic '{req_topic}': required {req_count}, but only {avail} available (shortage of {deficit}).",
                        required_count=req_count,
                        eligible_count=avail,
                        deficit=deficit,
                        details={"topic_id": req_topic},
                    )
