"""
backend/services/selection/learner_model.py

Learner Modeling Service for Milestone 6.
Handles UserQuestionHistory recording, UserMastery Laplace-smoothed accuracy calculations,
and enrichment of candidate questions with learner-specific historical signals.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from database.models import (
    AssessmentAttempt,
    Question,
    UserMastery,
    UserQuestionHistory,
)
from backend.services.selection.models import CandidateQuestion


class LearnerModelService:
    """
    Manages learner interaction history and mastery computations.
    """

    @classmethod
    def record_attempt_history(
        cls,
        db: Session,
        attempt: AssessmentAttempt,
    ) -> None:
        """
        Persists detailed question-level attempt interactions to UserQuestionHistory
        and updates Laplace-smoothed UserMastery for associated curriculum nodes.
        """
        if not attempt.user_id or not attempt.attempt_questions:
            return

        now = datetime.now(timezone.utc)
        node_updates: Dict[str, Dict[str, Any]] = {}

        for aq in attempt.attempt_questions:
            # 1. Insert UserQuestionHistory
            history = UserQuestionHistory(
                user_id=attempt.user_id,
                question_id=aq.question_id,
                attempt_id=attempt.id,
                selected_answer=aq.selected_answer,
                is_correct=aq.is_correct,
                marks_awarded=aq.marks_awarded,
                time_spent_seconds=aq.time_spent_seconds,
                answered_at=now,
            )
            db.add(history)

            # 2. Accumulate topic & curriculum node mastery updates
            q = aq.question or db.get(Question, aq.question_id)
            if q and q.primary_topic_id:
                topic_id = q.primary_topic_id
                if topic_id not in node_updates:
                    node_updates[topic_id] = {
                        "attempted": 0,
                        "correct": 0,
                        "incorrect": 0,
                        "exposure": 0,
                        "time_spent": 0,
                    }

                stats = node_updates[topic_id]
                stats["exposure"] += 1
                if aq.selected_answer is not None:
                    stats["attempted"] += 1
                    stats["time_spent"] += aq.time_spent_seconds
                    if aq.is_correct is True:
                        stats["correct"] += 1
                    elif aq.is_correct is False:
                        stats["incorrect"] += 1

        # 3. Update UserMastery records
        for node_id, delta in node_updates.items():
            mastery = (
                db.query(UserMastery)
                .filter(
                    UserMastery.user_id == attempt.user_id,
                    UserMastery.curriculum_node_id == node_id,
                )
                .first()
            )

            if not mastery:
                mastery = UserMastery(
                    user_id=attempt.user_id,
                    curriculum_node_id=node_id,
                    smoothed_accuracy=50.0,
                    attempted_count=0,
                    correct_count=0,
                    incorrect_count=0,
                    exposure_count=0,
                    average_time_seconds=0.0,
                    last_seen_at=now,
                )
                db.add(mastery)
                db.flush()

            mastery.attempted_count += delta["attempted"]
            mastery.correct_count += delta["correct"]
            mastery.incorrect_count += delta["incorrect"]
            mastery.exposure_count += delta["exposure"]

            # Laplace-smoothed accuracy: (correct + 1) / (attempted + 2) * 100
            mastery.smoothed_accuracy = round(
                ((mastery.correct_count + 1) / (mastery.attempted_count + 2)) * 100.0,
                2,
            )

            if mastery.attempted_count > 0:
                # Running average time
                mastery.average_time_seconds = round(
                    ((mastery.average_time_seconds * (mastery.attempted_count - delta["attempted"])) + delta["time_spent"])
                    / mastery.attempted_count,
                    2,
                )
            mastery.last_seen_at = now
            mastery.updated_at = now

        db.commit()

    @classmethod
    def get_user_question_history_map(
        cls,
        db: Session,
        user_id: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Retrieves user's question interactions and computes error stats, recency, and consecutive errors.
        """
        records = (
            db.query(UserQuestionHistory)
            .filter(UserQuestionHistory.user_id == user_id)
            .order_by(UserQuestionHistory.answered_at.asc())
            .all()
        )

        now = datetime.now(timezone.utc)
        stats_map: Dict[str, Dict[str, Any]] = {}

        for rec in records:
            qid = rec.question_id
            if qid not in stats_map:
                stats_map[qid] = {
                    "total_attempts": 0,
                    "error_count": 0,
                    "consecutive_errors": 0,
                    "last_answered_at": rec.answered_at,
                    "days_since_seen": 0.0,
                }

            s = stats_map[qid]
            s["total_attempts"] += 1
            s["last_answered_at"] = rec.answered_at

            if rec.is_correct is False:
                s["error_count"] += 1
                s["consecutive_errors"] += 1
            elif rec.is_correct is True:
                s["consecutive_errors"] = 0  # Reset on correct answer

        # Compute days since last exposure
        for qid, s in stats_map.items():
            last_dt = s["last_answered_at"]
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            diff_days = (now - last_dt).total_seconds() / 86400.0
            s["days_since_seen"] = max(0.0, diff_days)

        return stats_map

    @classmethod
    def get_user_mastery_map(
        cls,
        db: Session,
        user_id: str,
    ) -> Dict[str, float]:
        """
        Retrieves {curriculum_node_id: smoothed_accuracy} mapping for a user.
        """
        records = db.query(UserMastery).filter(UserMastery.user_id == user_id).all()
        return {r.curriculum_node_id: r.smoothed_accuracy for r in records}

    @classmethod
    def enrich_candidates(
        cls,
        db: Session,
        candidates: List[CandidateQuestion],
        user_id: Optional[str] = None,
    ) -> None:
        """
        Populates candidate questions with learner history metrics and topic mastery.
        """
        if not user_id:
            for c in candidates:
                c.is_unseen = True
                c.days_since_seen = None
                c.historical_error_count = 0
                c.consecutive_errors = 0
                c.smoothed_node_accuracy = 50.0
            return

        history_map = cls.get_user_question_history_map(db, user_id)
        mastery_map = cls.get_user_mastery_map(db, user_id)

        for c in candidates:
            qid = c.question.id
            t_id = c.question.primary_topic_id

            if qid in history_map:
                h = history_map[qid]
                c.is_unseen = False
                c.days_since_seen = h["days_since_seen"]
                c.historical_error_count = h["error_count"]
                c.consecutive_errors = h["consecutive_errors"]
            else:
                c.is_unseen = True
                c.days_since_seen = None
                c.historical_error_count = 0
                c.consecutive_errors = 0

            # Topic mastery score (default 50.0 neutral if untouched)
            c.smoothed_node_accuracy = mastery_map.get(t_id, 50.0) if t_id else 50.0
