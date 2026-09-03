"""
backend/services/assessment_service.py

Universal Assessment Engine Service.
Provides end-to-end management for medical examinations, from blueprint generation and
multi-section test partitioning to live runner state synchronization, scoring, and review.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from database.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentQuestion,
    AssessmentSection,
    AssessmentType,
    AttemptQuestion,
    AttemptStatus,
    DifficultyLevel,
    MarkingScheme,
    NavigationPolicy,
    Question,
    QuestionStatus,
    UserMastery,
    UserQuestionHistory,
)
from backend.services.selection import (
    UniversalQuestionSelector,
    LearnerModelService,
    InsufficientQuestionPoolError,
    SelectionError,
)



class AssessmentServiceError(Exception):
    """Base exception for assessment service errors."""
    pass


class QuestionCountUnavailableError(AssessmentServiceError):
    """Raised when available questions matching blueprint is fewer than requested count."""
    pass


class AttemptNotFoundError(AssessmentServiceError):
    """Raised when an attempt cannot be found."""
    pass


class AttemptAlreadySubmittedError(AssessmentServiceError):
    """Raised when modifying an already submitted attempt."""
    pass


# -----------------------------------------------------------------------------
# 1. Preset Definitions
# -----------------------------------------------------------------------------
ASSESSMENT_PRESETS = [
    {
        "id": "neet-ss-mock",
        "title": "NEET-SS Grand Mock Examination",
        "type": AssessmentType.MOCK.value,
        "question_count": 150,
        "duration_seconds": 9000,  # 150 mins
        "marking_scheme_id": "NEET_4_1",
        "navigation_policy": NavigationPolicy.FREE.value,
        "description": "Full simulation of NEET-SS Super-Specialty examination with 150 questions (+4 / -1).",
        "depth_level": "super_specialty",
        "sections": [
            {"name": "Part A: General & Broad Feeder Pathology", "question_count": 50},
            {"name": "Part B: Oncopathology & Super-Specialty Core", "question_count": 100},
        ],
    },
    {
        "id": "neet-pg-mock",
        "title": "NEET-PG Comprehensive Mock",
        "type": AssessmentType.MOCK.value,
        "question_count": 200,
        "duration_seconds": 12600,  # 210 mins
        "marking_scheme_id": "NEET_4_1",
        "navigation_policy": NavigationPolicy.FREE.value,
        "description": "Full 200-question mock simulating NEET-PG standard exam conditions (+4 / -1).",
        "depth_level": "postgraduate",
    },
    {
        "id": "inicet-mock",
        "title": "INI-CET Clinical Mock Test",
        "type": AssessmentType.MOCK.value,
        "question_count": 200,
        "duration_seconds": 10800,  # 180 mins
        "marking_scheme_id": "INICET_1_033",
        "navigation_policy": NavigationPolicy.FREE.value,
        "description": "200-question clinical vignette mock with AIIMS/INI-CET marking (+1 / -0.33).",
        "depth_level": "postgraduate",
    },
    {
        "id": "pathology-subject-mastery",
        "title": "Pathology Subject-Wise Mastery Test",
        "type": AssessmentType.SUBJECT.value,
        "question_count": 100,
        "duration_seconds": 6000,  # 100 mins
        "marking_scheme_id": "NEET_4_1",
        "navigation_policy": NavigationPolicy.FREE.value,
        "description": "100 high-yield Pathology questions spanning General, Systemic, and Hematopathology.",
    },
    {
        "id": "topic-assessment",
        "title": "Topic Mastery Assessment",
        "type": AssessmentType.TOPIC.value,
        "question_count": 50,
        "duration_seconds": 3000,  # 50 mins
        "marking_scheme_id": "NEET_4_1",
        "navigation_policy": NavigationPolicy.FREE.value,
        "description": "50-question focused test on specific medical topics.",
    },
    {
        "id": "subtopic-micro-quiz",
        "title": "Subtopic Micro-Quiz",
        "type": AssessmentType.SUBTOPIC.value,
        "question_count": 20,
        "duration_seconds": 1200,  # 20 mins
        "marking_scheme_id": "NEET_4_1",
        "navigation_policy": NavigationPolicy.FREE.value,
        "description": "20 rapid-fire questions targeting specific diagnostic criteria.",
    },
    {
        "id": "daily-dose",
        "title": "Daily Rapid Fire (Daily Dose)",
        "type": AssessmentType.DAILY.value,
        "question_count": 5,
        "duration_seconds": 300,  # 5 mins
        "marking_scheme_id": "NEET_4_1",
        "navigation_policy": NavigationPolicy.FREE.value,
        "description": "5 daily high-yield questions to maintain consistency and recall.",
    },
]


class AssessmentService:
    """Core domain service for the Universal Assessment Engine."""

    @staticmethod
    def list_presets() -> List[Dict[str, Any]]:
        """Returns standard predefined 1-click assessment presets."""
        return ASSESSMENT_PRESETS

    @staticmethod
    def get_preset(preset_id: str) -> Dict[str, Any]:
        """Resolve a canonical preset or fail instead of silently using defaults."""
        preset = next((item for item in ASSESSMENT_PRESETS if item["id"] == preset_id), None)
        if not preset:
            raise AssessmentServiceError(f"Unknown assessment preset '{preset_id}'.")
        return preset

    @staticmethod
    def create_assessment(
        db: Session,
        title: str,
        assessment_type: AssessmentType = AssessmentType.CUSTOM,
        question_count: int = 50,
        duration_seconds: int = 3000,
        marking_scheme_id: str = "NEET_4_1",
        navigation_policy: NavigationPolicy = NavigationPolicy.FREE,
        blueprint: Optional[Dict[str, Any]] = None,
        sections_config: Optional[List[Dict[str, Any]]] = None,
    ) -> Assessment:
        """
        Creates an assessment, samples questions server-side based on blueprint,
        partitions into sections (if requested), and freezes immutable question snapshots.
        """
        blueprint = blueprint or {}
        
        # Verify marking scheme exists (with self-healing fallback for standard schemes)
        scheme = db.get(MarkingScheme, marking_scheme_id)
        if not scheme:
            standard_defaults = {
                "NEET_4_1": ("NEET Standard (+4, -1)", 4.0, 1.0, 0.0),
                "INICET_1_033": ("INI-CET Standard (+1, -0.3333)", 1.0, 0.3333, 0.0),
                "PROPORTIONAL_1_025": ("Proportional (+1, -0.25)", 1.0, 0.25, 0.0),
                "ZERO_PENALTY": ("Learning Mode (+1, 0)", 1.0, 0.0, 0.0),
            }
            if marking_scheme_id in standard_defaults:
                name, corr, pen, unans = standard_defaults[marking_scheme_id]
                scheme = MarkingScheme(
                    id=marking_scheme_id,
                    name=name,
                    correct_marks=corr,
                    penalty_marks=pen,
                    unanswered_marks=unans,
                )
                db.add(scheme)
                db.flush()
            else:
                raise AssessmentServiceError(f"Marking scheme '{marking_scheme_id}' not found.")

        # Execute Intelligent Question Selection (Milestone 6)
        selector_blueprint = dict(blueprint or {})
        selector_blueprint["question_count"] = question_count
        if "topic_id" in blueprint and blueprint["topic_id"] and "topic_ids" not in selector_blueprint:
            selector_blueprint["topic_ids"] = [blueprint["topic_id"]]

        try:
            selection_result = UniversalQuestionSelector.select_questions(
                db=db,
                blueprint=selector_blueprint,
                user_id=None,
                default_count=question_count,
            )
            selected_questions = selection_result.selected_questions
            reasons_map = selection_result.selection_reasons_map
            scores_map = selection_result.priority_scores_map
        except InsufficientQuestionPoolError as e:
            # Re-raise as QuestionCountUnavailableError for backward compatibility
            raise QuestionCountUnavailableError(str(e)) from e

        # Create Assessment record
        assessment = Assessment(
            title=title,
            type=assessment_type,
            question_count=len(selected_questions),
            duration_seconds=duration_seconds,
            marking_scheme_id=marking_scheme_id,
            navigation_policy=navigation_policy,
            blueprint=blueprint,
        )
        db.add(assessment)
        db.flush()

        # Handle Sections
        sections_map = {}
        if sections_config and len(sections_config) > 0:
            for idx, sec_cfg in enumerate(sections_config, start=1):
                sec = AssessmentSection(
                    assessment_id=assessment.id,
                    section_order=idx,
                    name=sec_cfg.get("name", f"Section {idx}"),
                    question_count=sec_cfg.get("question_count", len(selected_questions)),
                    duration_seconds=sec_cfg.get("duration_seconds"),
                    navigation_policy=NavigationPolicy(sec_cfg.get("navigation_policy", navigation_policy.value)),
                )
                db.add(sec)
                db.flush()
                sections_map[idx] = sec

        # Freeze immutable question snapshots
        for seq, q in enumerate(selected_questions, start=1):
            # Resolve section if configured
            sec_id = None
            if sections_config:
                accum = 0
                for s_idx, sec_cfg in enumerate(sections_config, start=1):
                    accum += sec_cfg.get("question_count", 0)
                    if seq <= accum:
                        sec_id = sections_map[s_idx].id
                        break

            # Options snapshot (handle list of dicts or direct dict)
            options_dict = {}
            if isinstance(q.options, list):
                for opt in q.options:
                    if isinstance(opt, dict):
                        key = opt.get("key") or opt.get("option_key") or ""
                        text = opt.get("text") or opt.get("option_text") or ""
                        if key:
                            options_dict[key] = text
            elif isinstance(q.options, dict):
                options_dict = q.options

            snapshot = {
                "question_id": q.id,
                "stem": q.stem,
                "options": options_dict,
                "correct_option": q.correct_option,
                "explanation": q.explanation,
                "primary_topic_id": q.primary_topic_id,
                "difficulty": q.difficulty.value if q.difficulty else "medium",
                "source_exam_id": q.source_exam_id,
                "external_source": q.external_source,
                "selection_reasons": reasons_map.get(q.id, ["EXAM_BLUEPRINT_CORE"]),
                "priority_score": scores_map.get(q.id, 0.0),
                "has_images": getattr(q, "has_images", False),
                "image_assets": getattr(q, "image_assets", []) or [],
            }

            aq = AssessmentQuestion(
                assessment_id=assessment.id,
                section_id=sec_id,
                question_id=q.id,
                sequence=seq,
                snapshot=snapshot,
            )
            db.add(aq)

        db.commit()
        db.refresh(assessment)
        return assessment

    @staticmethod
    def preview_assessment(
        db: Session,
        blueprint: Dict[str, Any],
        user_id: Optional[str] = None,
        question_count: int = 10,
    ) -> Dict[str, Any]:
        """
        Simulates question selection for a blueprint without creating an assessment record.
        Returns topic/difficulty breakdown, metadata confidence metrics, and selection reasons.
        """
        selector_blueprint = dict(blueprint or {})
        selector_blueprint["question_count"] = question_count
        if "topic_id" in blueprint and blueprint["topic_id"] and "topic_ids" not in selector_blueprint:
            selector_blueprint["topic_ids"] = [blueprint["topic_id"]]

        result = UniversalQuestionSelector.select_questions(
            db=db,
            blueprint=selector_blueprint,
            user_id=user_id,
            default_count=question_count,
        )

        sample_reasons = {}
        for q in result.selected_questions[:5]:
            sample_reasons[q.id] = {
                "stem_preview": q.stem[:80] + "..." if len(q.stem) > 80 else q.stem,
                "topic": q.primary_topic_id,
                "reasons": result.selection_reasons_map.get(q.id, []),
                "priority_score": result.priority_scores_map.get(q.id, 0.0),
            }

        return {
            "selected_question_count": len(result.selected_questions),
            "total_eligible_pool_count": result.total_eligible_count,
            "topic_breakdown": result.topic_breakdown,
            "difficulty_breakdown": result.difficulty_breakdown,
            "educational_level_breakdown": result.educational_level_breakdown,
            "sample_selection_reasons": sample_reasons,
            "warnings": result.warnings,
        }

    @staticmethod
    def start_attempt(
        db: Session,
        assessment_id: str,
        user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
    ) -> Tuple[AssessmentAttempt, List[Dict[str, Any]]]:
        """
        Initializes an assessment attempt session, returns sanitized questions
        (strictly zero answer/explanation leaks).
        """
        assessment = db.get(
            Assessment,
            assessment_id,
            options=[joinedload(Assessment.assessment_questions), joinedload(Assessment.sections)],
        )
        if not assessment:
            raise AssessmentServiceError(f"Assessment '{assessment_id}' not found.")

        # Calculate max score from marking scheme
        scheme = db.get(MarkingScheme, assessment.marking_scheme_id)
        max_score = assessment.question_count * (scheme.correct_marks if scheme else 4.0)

        # Create attempt
        attempt = AssessmentAttempt(
            assessment_id=assessment.id,
            user_id=user_id,
            guest_session_id=guest_session_id,
            started_at=datetime.now(timezone.utc),
            status=AttemptStatus.IN_PROGRESS,
            score=0.0,
            max_score=max_score,
            percentage=0.0,
            correct_count=0,
            incorrect_count=0,
            unanswered_count=assessment.question_count,
            time_spent_seconds=0,
        )
        db.add(attempt)
        db.flush()

        # Initialize AttemptQuestion records
        for aq in assessment.assessment_questions:
            att_q = AttemptQuestion(
                attempt_id=attempt.id,
                question_id=aq.question_id,
                selected_answer=None,
                correct_answer=aq.snapshot.get("correct_option", ""),
                is_correct=None,
                marks_awarded=0.0,
                time_spent_seconds=0,
                marked_for_review=False,
                question_snapshot=aq.snapshot,
            )
            db.add(att_q)

        db.commit()
        db.refresh(attempt)

        # Build sanitized questions for client
        sanitized_questions = AssessmentService._get_sanitized_questions(assessment, attempt)
        return attempt, sanitized_questions

    @staticmethod
    def _get_sanitized_questions(
        assessment: Assessment,
        attempt: AssessmentAttempt,
    ) -> List[Dict[str, Any]]:
        """
        Strips ground truth `correct_option` and `explanation` from client runner payload.
        Attaches active user responses, marked state, and Prometric status colors.
        """
        # Map existing responses
        responses_map = {
            aq.question_id: aq for aq in attempt.attempt_questions
        }

        sanitized = []
        for aq in assessment.assessment_questions:
            snap = aq.snapshot
            resp = responses_map.get(aq.question_id)

            selected_answer = resp.selected_answer if resp else None
            marked = resp.marked_for_review if resp else False

            # Compute Prometric 5-state status
            if selected_answer and marked:
                status = "ANSWERED_AND_MARKED"
            elif selected_answer:
                status = "ANSWERED"
            elif marked:
                status = "MARKED_FOR_REVIEW"
            else:
                status = "UNANSWERED"

            sanitized.append({
                "sequence": aq.sequence,
                "question_id": aq.question_id,
                "section_id": aq.section_id,
                "stem": snap.get("stem"),
                "options": snap.get("options", {}),
                "selected_answer": selected_answer,
                "marked_for_review": marked,
                "status": status,
                "topic_name": snap.get("topic_name") or snap.get("primary_topic_id") or "Pathology",
                "difficulty": snap.get("difficulty"),
                "has_images": snap.get("has_images", False),
                "image_assets": snap.get("image_assets", []),
            })

        return sanitized

    @staticmethod
    def get_attempt_state(
        db: Session,
        attempt_id: str,
    ) -> Dict[str, Any]:
        """Fetches active attempt state, remaining seconds, and question palette."""
        attempt = db.get(
            AssessmentAttempt,
            attempt_id,
            options=[
                joinedload(AssessmentAttempt.assessment).joinedload(Assessment.assessment_questions),
                joinedload(AssessmentAttempt.assessment).joinedload(Assessment.sections),
                joinedload(AssessmentAttempt.attempt_questions),
            ],
        )
        if not attempt:
            raise AttemptNotFoundError(f"Attempt '{attempt_id}' not found.")

        assessment = attempt.assessment
        
        # Calculate remaining seconds
        elapsed = attempt.time_spent_seconds
        remaining = max(0, assessment.duration_seconds - elapsed)

        sanitized_questions = AssessmentService._get_sanitized_questions(assessment, attempt)

        return {
            "attempt_id": attempt.id,
            "assessment_id": assessment.id,
            "title": assessment.title,
            "type": assessment.type.value,
            "status": attempt.status.value,
            "total_questions": assessment.question_count,
            "duration_seconds": assessment.duration_seconds,
            "time_spent_seconds": attempt.time_spent_seconds,
            "remaining_seconds": remaining,
            "navigation_policy": assessment.navigation_policy.value,
            "sections": [
                {
                    "id": s.id,
                    "section_order": s.section_order,
                    "name": s.name,
                    "question_count": s.question_count,
                }
                for s in assessment.sections
            ],
            "questions": sanitized_questions,
        }

    @staticmethod
    def record_heartbeat(
        db: Session,
        attempt_id: str,
        responses: List[Dict[str, Any]],
        elapsed_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Background heartbeat synchronization.
        Persists answers, marked states, and time spent on questions.
        """
        attempt = db.get(
            AssessmentAttempt,
            attempt_id,
            options=[joinedload(AssessmentAttempt.attempt_questions)],
        )
        if not attempt:
            raise AttemptNotFoundError(f"Attempt '{attempt_id}' not found.")

        if attempt.status != AttemptStatus.IN_PROGRESS:
            raise AttemptAlreadySubmittedError(f"Cannot update attempt in '{attempt.status.value}' state.")

        if elapsed_seconds is not None:
            attempt.time_spent_seconds = elapsed_seconds

        # Map attempt questions for fast updates
        q_map = {aq.question_id: aq for aq in attempt.attempt_questions}

        answered_count = 0
        for r in responses:
            qid = r.get("question_id")
            if qid in q_map:
                aq = q_map[qid]
                if "selected_answer" in r:
                    aq.selected_answer = r["selected_answer"]
                if "marked_for_review" in r:
                    aq.marked_for_review = bool(r["marked_for_review"])
                if "time_spent_seconds" in r:
                    aq.time_spent_seconds = int(r["time_spent_seconds"])

        for aq in attempt.attempt_questions:
            if aq.selected_answer:
                answered_count += 1

        attempt.unanswered_count = attempt.assessment.question_count - answered_count
        db.commit()

        return {
            "status": "success",
            "attempt_id": attempt.id,
            "time_spent_seconds": attempt.time_spent_seconds,
            "answered_count": answered_count,
            "unanswered_count": attempt.unanswered_count,
        }

    @staticmethod
    def submit_attempt(
        db: Session,
        attempt_id: str,
        responses: Optional[List[Dict[str, Any]]] = None,
        final_elapsed_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Finalizes and evaluates an attempt:
        - Calculates correct, incorrect, and unanswered counts.
        - Applies marking scheme penalties (+4 / -1 or +1 / -0.33).
        - Computes accuracy, percentage, and locks the attempt.
        """
        attempt = db.get(
            AssessmentAttempt,
            attempt_id,
            options=[
                joinedload(AssessmentAttempt.assessment).joinedload(Assessment.marking_scheme),
                joinedload(AssessmentAttempt.attempt_questions),
            ],
        )
        if not attempt:
            raise AttemptNotFoundError(f"Attempt '{attempt_id}' not found.")

        if attempt.status != AttemptStatus.IN_PROGRESS:
            return AssessmentService.get_results(db, attempt_id)

        # Apply final responses if provided
        if responses:
            AssessmentService.record_heartbeat(db, attempt_id, responses, final_elapsed_seconds)

        if final_elapsed_seconds is not None:
            attempt.time_spent_seconds = final_elapsed_seconds

        scheme = attempt.assessment.marking_scheme
        correct_marks = scheme.correct_marks if scheme else 4.0
        penalty_marks = scheme.penalty_marks if scheme else 1.0
        unanswered_marks = scheme.unanswered_marks if scheme else 0.0

        total_score = 0.0
        correct_count = 0
        incorrect_count = 0
        unanswered_count = 0
        negative_marks_lost = 0.0

        for aq in attempt.attempt_questions:
            user_ans = (aq.selected_answer or "").strip().upper()
            correct_ans = (aq.correct_answer or "").strip().upper()

            if not user_ans:
                aq.is_correct = None
                aq.marks_awarded = unanswered_marks
                unanswered_count += 1
                total_score += unanswered_marks
            elif user_ans == correct_ans:
                aq.is_correct = True
                aq.marks_awarded = correct_marks
                correct_count += 1
                total_score += correct_marks
            else:
                aq.is_correct = False
                aq.marks_awarded = -penalty_marks
                incorrect_count += 1
                negative_marks_lost += penalty_marks
                total_score -= penalty_marks

        total_questions = attempt.assessment.question_count
        max_score = total_questions * correct_marks
        percentage = (total_score / max_score * 100.0) if max_score > 0 else 0.0
        attempted = correct_count + incorrect_count
        accuracy = (correct_count / attempted * 100.0) if attempted > 0 else 0.0

        attempt.status = AttemptStatus.SUBMITTED
        attempt.submitted_at = datetime.now(timezone.utc)
        attempt.score = round(total_score, 2)
        attempt.max_score = round(max_score, 2)
        attempt.percentage = round(percentage, 2)
        attempt.correct_count = correct_count
        attempt.incorrect_count = incorrect_count
        attempt.unanswered_count = unanswered_count

        # Record learner interaction history and update topic mastery (Milestone 6)
        if attempt.user_id:
            LearnerModelService.record_attempt_history(db, attempt)

        db.commit()
        return AssessmentService.get_results(db, attempt_id)

    @staticmethod
    def get_results(
        db: Session,
        attempt_id: str,
    ) -> Dict[str, Any]:
        """Returns the diagnostic scorecard and breakdown metrics for an attempt."""
        attempt = db.get(
            AssessmentAttempt,
            attempt_id,
            options=[
                joinedload(AssessmentAttempt.assessment).joinedload(Assessment.marking_scheme),
                joinedload(AssessmentAttempt.attempt_questions),
            ],
        )
        if not attempt:
            raise AttemptNotFoundError(f"Attempt '{attempt_id}' not found.")

        assessment = attempt.assessment
        scheme = assessment.marking_scheme
        penalty = scheme.penalty_marks if scheme else 1.0
        negative_marks_lost = attempt.incorrect_count * penalty

        attempted = attempt.correct_count + attempt.incorrect_count
        accuracy = (attempt.correct_count / attempted * 100.0) if attempted > 0 else 0.0
        attempt_rate = (attempted / assessment.question_count * 100.0) if assessment.question_count > 0 else 0.0
        avg_seconds_per_q = (
            round(attempt.time_spent_seconds / attempted, 1) if attempted > 0 else 0.0
        )

        # Topic & difficulty breakdown
        topic_stats: Dict[str, Dict[str, Any]] = {}
        diff_stats: Dict[str, Dict[str, Any]] = {}

        for aq in attempt.attempt_questions:
            topic = aq.question_snapshot.get("primary_topic_id") or "General Pathology"
            diff = aq.question_snapshot.get("difficulty") or "medium"

            # Topic aggregation
            if topic not in topic_stats:
                topic_stats[topic] = {"topic": topic, "total": 0, "correct": 0, "incorrect": 0, "unanswered": 0}
            topic_stats[topic]["total"] += 1
            if aq.is_correct is True:
                topic_stats[topic]["correct"] += 1
            elif aq.is_correct is False:
                topic_stats[topic]["incorrect"] += 1
            else:
                topic_stats[topic]["unanswered"] += 1

            # Difficulty aggregation
            if diff not in diff_stats:
                diff_stats[diff] = {"difficulty": diff, "total": 0, "correct": 0, "incorrect": 0, "unanswered": 0}
            diff_stats[diff]["total"] += 1
            if aq.is_correct is True:
                diff_stats[diff]["correct"] += 1
            elif aq.is_correct is False:
                diff_stats[diff]["incorrect"] += 1
            else:
                diff_stats[diff]["unanswered"] += 1

        # Compute accuracy per topic & identify weak topics
        weak_topics = []
        topic_breakdown = []
        for t, stats in topic_stats.items():
            att = stats["correct"] + stats["incorrect"]
            acc = round((stats["correct"] / att * 100.0), 1) if att > 0 else 0.0
            stats["accuracy"] = acc
            topic_breakdown.append(stats)
            if att >= 2 and acc < 50.0:
                weak_topics.append(t)

        return {
            "attempt_id": attempt.id,
            "assessment_id": assessment.id,
            "title": assessment.title,
            "status": attempt.status.value,
            "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
            "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
            "score": attempt.score,
            "max_score": attempt.max_score,
            "percentage": attempt.percentage,
            "correct_count": attempt.correct_count,
            "incorrect_count": attempt.incorrect_count,
            "unanswered_count": attempt.unanswered_count,
            "attempted_count": attempted,
            "accuracy": round(accuracy, 1),
            "attempt_rate": round(attempt_rate, 1),
            "negative_marks_lost": round(negative_marks_lost, 2),
            "time_spent_seconds": attempt.time_spent_seconds,
            "avg_seconds_per_question": avg_seconds_per_q,
            "marking_scheme": {
                "name": scheme.name if scheme else "NEET Standard",
                "correct_marks": scheme.correct_marks if scheme else 4.0,
                "penalty_marks": scheme.penalty_marks if scheme else 1.0,
            },
            "topic_breakdown": topic_breakdown,
            "difficulty_breakdown": list(diff_stats.values()),
            "weak_topics": weak_topics,
        }

    @staticmethod
    def get_review(
        db: Session,
        attempt_id: str,
    ) -> Dict[str, Any]:
        """Returns deep question-by-question review with ground truth, explanations, and citations."""
        attempt = db.get(
            AssessmentAttempt,
            attempt_id,
            options=[
                joinedload(AssessmentAttempt.assessment),
                joinedload(AssessmentAttempt.attempt_questions),
            ],
        )
        if not attempt:
            raise AttemptNotFoundError(f"Attempt '{attempt_id}' not found.")

        questions_review = []
        for idx, aq in enumerate(attempt.attempt_questions, start=1):
            snap = aq.question_snapshot
            questions_review.append({
                "sequence": idx,
                "question_id": aq.question_id,
                "stem": snap.get("stem"),
                "options": snap.get("options", {}),
                "selected_answer": aq.selected_answer,
                "correct_answer": aq.correct_answer,
                "is_correct": aq.is_correct,
                "marks_awarded": aq.marks_awarded,
                "time_spent_seconds": aq.time_spent_seconds,
                "marked_for_review": aq.marked_for_review,
                "explanation": snap.get("explanation"),
                "primary_topic_id": snap.get("primary_topic_id"),
                "difficulty": snap.get("difficulty"),
                "source_exam_id": snap.get("source_exam_id"),
                "external_source": snap.get("external_source"),
            })

        return {
            "attempt_id": attempt.id,
            "assessment_id": attempt.assessment.id,
            "title": attempt.assessment.title,
            "score": attempt.score,
            "max_score": attempt.max_score,
            "percentage": attempt.percentage,
            "correct_count": attempt.correct_count,
            "incorrect_count": attempt.incorrect_count,
            "unanswered_count": attempt.unanswered_count,
            "review_questions": questions_review,
        }
