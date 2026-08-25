"""
backend/services/student_service.py

Student Core & Adaptive Assessment Services for Milestone 7:
- Adaptive Medical Learner Onboarding profile management
- Daily High-Yield Quiz generation & streak tracking
- Continue Learning & In-progress Attempt Resumption
- Spaced Repetition & Smart Mistake Review
- Composite Exam Readiness Index calculation
- Resilient Draft Answer Synchronization
"""

import hashlib
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database.models import (
    User,
    AssessmentAttempt,
    AttemptStatus,
    AttemptQuestion,
    Question,
    QuestionStatus,
    CurriculumTopic,
    CurriculumLevel,
    UserMastery,
    UserQuestionHistory,
)
from backend.services.selection import UniversalQuestionSelector


class StudentService:
    """
    Service powering student personalization, onboarding, daily quizzes,
    spaced mistake drills, and readiness analytics.
    """

    # -------------------------------------------------------------------------
    # 0. Static / Dynamic Curriculum & Examination Taxonomies
    # -------------------------------------------------------------------------
    @staticmethod
    def get_taxonomies(db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Returns structured examinations, specialities (with leaf nodes),
        residency stages, and target attempt years for dynamic data-driven UI.
        """
        return {
            "examinations": [
                {
                    "id": "NEET_SS",
                    "title": "NEET-SS / DrNB Super-Specialty",
                    "badge": "Super-Specialty",
                    "category": "super_specialty",
                    "description": "High-yield oncology, sub-specialty IHC algorithms, flow cytometry & molecular diagnostics.",
                    "has_specialities": True,
                    "specialities": [
                        {
                            "id": "Oncopathology",
                            "name": "Oncopathology & Tumor Markers",
                            "is_default": True,
                            "description": "Solid tumors, WHO classifications, theranostic IHC & molecular biomarkers.",
                        },
                        {
                            "id": "Hematopathology",
                            "name": "Hematopathology & Flow Cytometry",
                            "description": "Leukemias, lymphomas, bone marrow pathology & immunophenotyping.",
                        },
                        {
                            "id": "Neuropathology",
                            "name": "Neuropathology & CNS Tumors",
                            "description": "CNS neoplasia, WHO CNS5 molecular entities, neuro-degenerative pathology.",
                        },
                        {
                            "id": "Nephropathology",
                            "name": "Nephropathology & Renal Biopsies",
                            "description": "Glomerular diseases, transplant pathology, immunofluorescence.",
                        },
                        {
                            "id": "Cytopathology",
                            "name": "Cytopathology & FNAC",
                            "description": "Bethesda systems, Paris system, Milan system, serous effusions.",
                        },
                        {
                            "id": "Molecular Diagnostics",
                            "name": "Molecular Diagnostics & Precision Oncology",
                            "description": "NGS mutation panels, FISH translocations, liquid biopsies.",
                        },
                    ],
                },
                {
                    "id": "MD_PATH",
                    "title": "MD / MS / DNB Residency Exit Exam",
                    "badge": "Residency Exit",
                    "category": "postgraduate",
                    "description": "Comprehensive postgraduate surgical pathology, hematology, autopsy & clinical pathology.",
                    "has_specialities": True,
                    "specialities": [
                        {
                            "id": "General & Surgical Pathology",
                            "name": "General & Surgical Pathology",
                            "is_default": True,
                            "description": "Core systemic surgical pathology, grossing protocols, diagnostic IHC.",
                        },
                        {
                            "id": "Hematopathology",
                            "name": "Clinical Hematology & Transfusion Medicine",
                            "description": "Coagulation, blood banking, flow cytometry, hemoglobinopathies.",
                        },
                        {
                            "id": "Cytopathology",
                            "name": "Diagnostic Cytology & Exfoliative Smears",
                            "description": "Pap smears, thyroid FNA, fluid cytology, cell blocks.",
                        },
                        {
                            "id": "Chemical Pathology",
                            "name": "Clinical Biochemistry & Lab Management",
                            "description": "QC charts, automated analyzers, reference ranges.",
                        },
                    ],
                },
                {
                    "id": "NEET_PG",
                    "title": "NEET-PG / INI-CET Entrance",
                    "badge": "Postgraduate Entrance",
                    "category": "postgraduate",
                    "description": "Comprehensive clinical vignettes across 19 subjects with deep pathology & medicine core.",
                    "has_specialities": False,
                    "default_speciality": "General Medicine & Pathology Core",
                    "specialities": [],
                },
                {
                    "id": "MBBS",
                    "title": "MBBS Professional University Exam",
                    "badge": "Undergraduate",
                    "category": "undergraduate",
                    "description": "Undergraduate disease mechanisms, systemic pathology & clinical vignettes.",
                    "has_specialities": False,
                    "default_speciality": "2nd Professional Pathology",
                    "specialities": [],
                },
                {
                    "id": "FELLOWSHIP",
                    "title": "Post-Doctoral Clinical Fellowship",
                    "badge": "Sub-Specialty Board",
                    "category": "fellowship",
                    "description": "Advanced subspecialty certification in oncopathology, hematopathology, or neuropathology.",
                    "has_specialities": True,
                    "specialities": [
                        {
                            "id": "Oncopathology Fellowship",
                            "name": "Oncopathology Fellowship (Tata / AIIMS Pattern)",
                            "is_default": True,
                        },
                        {
                            "id": "Hematopathology Fellowship",
                            "name": "Hematopathology & Flow Cytometry Fellowship",
                        },
                        {
                            "id": "Dermatopathology Fellowship",
                            "name": "Dermatopathology & Skin Biopsy Fellowship",
                        },
                    ],
                },
            ],
            "experience_stages": [
                {"id": "MBBS", "label": "MBBS Student / Intern"},
                {"id": "JR", "label": "Junior Resident (MD / MS / DNB Trainee)"},
                {"id": "SR", "label": "Senior Resident (Post-MD / Post-MS)"},
                {"id": "FELLOW", "label": "Post-Doctoral Fellow"},
                {"id": "CONSULTANT", "label": "Practicing Specialist / Consultant"},
            ],
            "target_years": [2026, 2027, 2028],
            "metadata_version": "1.1.0",
        }

    # -------------------------------------------------------------------------
    # 1. Adaptive Onboarding
    # -------------------------------------------------------------------------
    @staticmethod
    def update_onboarding_profile(
        db: Session,
        user_id: str,
        target_exam: Optional[str] = None,
        target_year: Optional[int] = None,
        residency_stage: Optional[str] = None,
        medical_college: Optional[str] = None,
        primary_speciality: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Updates a user's adaptive medical onboarding preferences.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        if target_exam:
            user.target_exam = target_exam.strip()
        if target_year is not None:
            user.target_year = target_year
        if residency_stage:
            user.residency_stage = residency_stage.strip()
        if medical_college:
            user.medical_college = medical_college.strip()
        if primary_speciality:
            user.primary_speciality = primary_speciality.strip()

        db.commit()
        db.refresh(user)

        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "target_exam": user.target_exam,
            "target_year": user.target_year,
            "residency_stage": user.residency_stage,
            "medical_college": user.medical_college,
            "primary_speciality": user.primary_speciality,
        }

    # -------------------------------------------------------------------------
    # 2. Daily High-Yield Quiz & Streak Engine
    # -------------------------------------------------------------------------
    @staticmethod
    def get_daily_quiz(db: Session, user_id: str) -> Dict[str, Any]:
        """
        Returns today's deterministic 5-question high-yield pathology quiz.
        Updates learner streak metrics based on activity date.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        today_utc = datetime.now(timezone.utc).date()
        today_str = today_utc.isoformat()
        
        # Compute deterministic integer seed from date string (e.g. "2026-08-25")
        seed_val = int(hashlib.sha256(today_str.encode("utf-8")).hexdigest()[:8], 16)

        # Update streak counter
        if user.last_active_date:
            last_date = user.last_active_date.date() if isinstance(user.last_active_date, datetime) else user.last_active_date
            if last_date == today_utc - timedelta(days=1):
                user.current_streak += 1
            elif last_date < today_utc - timedelta(days=1):
                user.current_streak = 1
        else:
            user.current_streak = 1

        if user.current_streak > user.longest_streak:
            user.longest_streak = user.current_streak
        
        user.last_active_date = datetime.now(timezone.utc)
        db.commit()

        # Select 5 daily questions
        blueprint = {
            "speciality": user.primary_speciality or "Pathology",
            "question_count": 5,
            "seed": seed_val,
            "assessment_mode": "PRACTICE",
            "strict_metadata_mode": False,
        }
        selection = UniversalQuestionSelector.select_questions(db, blueprint, user_id=user.id)

        return {
            "date": today_str,
            "title": f"Daily High-Yield Pathology Quiz ({today_str})",
            "question_count": len(selection.selected_questions),
            "current_streak": user.current_streak,
            "longest_streak": user.longest_streak,
            "questions": [
                {
                    "id": q.id,
                    "stem": q.stem,
                    "options": q.options,
                    "difficulty": q.difficulty.value if hasattr(q.difficulty, "value") else str(q.difficulty),
                    "primary_topic_id": q.primary_topic_id,
                }
                for q in selection.selected_questions
            ],
        }

    # -------------------------------------------------------------------------
    # 3. Continue Learning & In-Progress Attempts
    # -------------------------------------------------------------------------
    @staticmethod
    def get_continue_learning(db: Session, user_id: str) -> Dict[str, Any]:
        """
        Fetches active in-progress assessment attempts and top 3 weak topic recommendations.
        """
        # 1. In-progress attempts
        active_attempts = (
            db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.user_id == user_id,
                AssessmentAttempt.status == AttemptStatus.IN_PROGRESS,
            )
            .order_by(desc(AssessmentAttempt.started_at))
            .limit(5)
            .all()
        )

        resumable = []
        for att in active_attempts:
            answered_count = db.query(AttemptQuestion).filter(
                AttemptQuestion.attempt_id == att.id,
                AttemptQuestion.selected_answer.isnot(None),
            ).count()
            total_count = db.query(AttemptQuestion).filter(
                AttemptQuestion.attempt_id == att.id
            ).count()

            resumable.append({
                "attempt_id": att.id,
                "assessment_id": att.assessment_id,
                "assessment_title": att.assessment.title if att.assessment else "Medical Assessment",
                "started_at": att.started_at.isoformat() if att.started_at else None,
                "answered_count": answered_count,
                "total_questions": total_count,
            })

        # 2. Top 3 Weak Topics from UserMastery
        weak_masteries = (
            db.query(UserMastery)
            .filter(UserMastery.user_id == user_id, UserMastery.attempted_count >= 2)
            .order_by(UserMastery.smoothed_accuracy.asc())
            .limit(3)
            .all()
        )

        weak_topics = []
        for m in weak_masteries:
            topic_name = m.curriculum_node.name if m.curriculum_node else m.curriculum_node_id
            weak_topics.append({
                "curriculum_node_id": m.curriculum_node_id,
                "topic_name": topic_name,
                "smoothed_accuracy": round(m.smoothed_accuracy, 1),
                "attempted_count": m.attempted_count,
                "incorrect_count": m.incorrect_count,
                "remediation_blueprint": {
                    "topic_id": m.curriculum_node_id,
                    "question_count": 10,
                    "assessment_mode": "LEARNING",
                },
            })

        return {
            "resumable_attempts": resumable,
            "weak_topic_recommendations": weak_topics,
        }

    # -------------------------------------------------------------------------
    # 4. Composite Exam Readiness Index
    # -------------------------------------------------------------------------
    @staticmethod
    def get_exam_readiness(db: Session, user_id: str, target_exam: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates a composite exam readiness score (0–100%) from coverage, accuracy, and mock consistency.
        Readiness = 0.40 * Coverage + 0.35 * Accuracy + 0.15 * MockAvg + 0.10 * PacingConsistency
        """
        # 1. Total Curriculum Topics vs Attempted Topics
        total_topics_count = db.query(CurriculumTopic).filter(CurriculumTopic.level == CurriculumLevel.TOPIC).count()
        if total_topics_count == 0:
            total_topics_count = 1

        masteries = db.query(UserMastery).filter(UserMastery.user_id == user_id).all()
        attempted_topics_count = len([m for m in masteries if m.attempted_count > 0])
        coverage_pct = min(100.0, (attempted_topics_count / total_topics_count) * 100.0)

        # 2. Average Smoothed Accuracy
        if masteries:
            avg_accuracy = sum(m.smoothed_accuracy for m in masteries) / len(masteries)
        else:
            avg_accuracy = 50.0

        # 3. Recent Submitted Mocks (last 5)
        recent_mocks = (
            db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.user_id == user_id,
                AssessmentAttempt.status == AttemptStatus.SUBMITTED,
            )
            .order_by(desc(AssessmentAttempt.submitted_at))
            .limit(5)
            .all()
        )

        if recent_mocks:
            mock_avg = sum(m.percentage for m in recent_mocks) / len(recent_mocks)
        else:
            mock_avg = avg_accuracy

        # 4. Composite Score
        readiness_score = (
            0.40 * coverage_pct +
            0.35 * avg_accuracy +
            0.15 * mock_avg +
            0.10 * min(100.0, avg_accuracy * 1.1)
        )
        readiness_score = round(min(100.0, max(0.0, readiness_score)), 1)

        return {
            "readiness_score": readiness_score,
            "breakdown": {
                "curriculum_coverage_pct": round(coverage_pct, 1),
                "topics_covered": attempted_topics_count,
                "total_topics": total_topics_count,
                "average_accuracy_pct": round(avg_accuracy, 1),
                "mock_average_pct": round(mock_avg, 1),
            },
            "rating": "EXCELLENT" if readiness_score >= 80 else "GOOD" if readiness_score >= 60 else "NEEDS_FOCUS",
        }

    # -------------------------------------------------------------------------
    # 5. Smart Mistake Review & Spaced Drill
    # -------------------------------------------------------------------------
    @staticmethod
    def get_mistake_review(
        db: Session,
        user_id: str,
        topic_id: Optional[str] = None,
        repeated_only: bool = False,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Aggregates failed questions with error counts, explanations, and citations.
        """
        query = db.query(UserQuestionHistory).filter(
            UserQuestionHistory.user_id == user_id,
            UserQuestionHistory.is_correct == False,
        )

        history_rows = query.order_by(desc(UserQuestionHistory.answered_at)).all()

        # Group by question_id
        mistake_map: Dict[str, Dict[str, Any]] = {}
        for h in history_rows:
            qid = h.question_id
            if qid not in mistake_map:
                mistake_map[qid] = {
                    "question_id": qid,
                    "error_count": 0,
                    "last_failed_at": h.answered_at.isoformat() if h.answered_at else None,
                    "last_selected_answer": h.selected_answer,
                }
            mistake_map[qid]["error_count"] += 1

        mistakes_list = list(mistake_map.values())
        if repeated_only:
            mistakes_list = [m for m in mistakes_list if m["error_count"] >= 2]

        mistakes_list = mistakes_list[:limit]

        # Fetch questions
        q_ids = [m["question_id"] for m in mistakes_list]
        questions = db.query(Question).filter(Question.id.in_(q_ids)).all() if q_ids else []
        q_lookup = {q.id: q for q in questions}

        items = []
        for m in mistakes_list:
            q = q_lookup.get(m["question_id"])
            if q:
                if topic_id and q.primary_topic_id != topic_id:
                    continue
                items.append({
                    "question_id": q.id,
                    "stem": q.stem,
                    "options": q.options,
                    "correct_option": q.correct_option,
                    "explanation": q.explanation,
                    "error_count": m["error_count"],
                    "last_selected_answer": m["last_selected_answer"],
                    "last_failed_at": m["last_failed_at"],
                    "primary_topic_id": q.primary_topic_id,
                })

        return {
            "total_mistakes": len(items),
            "mistakes": items,
            "remediation_blueprint": {
                "question_ids": [it["question_id"] for it in items],
                "question_count": len(items),
                "assessment_mode": "LEARNING",
            },
        }

    # -------------------------------------------------------------------------
    # 6. Draft Answer Synchronization (Network Resilience)
    # -------------------------------------------------------------------------
    @staticmethod
    def sync_draft_answers(
        db: Session,
        attempt_id: str,
        user_id: Optional[str],
        answers_payload: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Idempotently synchronizes batch draft answers from Web/Mobile client.
        """
        attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == attempt_id).first()
        if not attempt:
            raise ValueError("Assessment attempt not found")

        if attempt.status == AttemptStatus.SUBMITTED:
            raise ValueError("Cannot sync answers to an already submitted assessment")

        updated_count = 0
        for ans in answers_payload:
            qid = ans.get("question_id")
            selected = ans.get("selected_answer")
            time_spent = ans.get("time_spent_seconds", 0)

            if not qid:
                continue

            aq = db.query(AttemptQuestion).filter(
                AttemptQuestion.attempt_id == attempt_id,
                AttemptQuestion.question_id == qid,
            ).first()

            if aq:
                if selected is not None:
                    aq.selected_answer = selected
                if time_spent:
                    aq.time_spent_seconds = time_spent
                updated_count += 1

        db.commit()
        return {
            "success": True,
            "attempt_id": attempt_id,
            "synced_count": updated_count,
        }
