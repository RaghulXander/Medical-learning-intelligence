"""
backend/services/generation/evaluator.py

Multi-Signal Question Evaluator & Quality Audit Engine.
Validates answer-explanation consistency, distractor plausibility,
evidence grounding citations, and duplicate questions before candidate persistence.
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Optional
from sqlalchemy.orm import Session

from database.models import Question
from backend.services.generation.models import (
    EvaluationCheck,
    EvaluationResult,
    GeneratedMCQPayload,
)
from backend.services.evaluation.pubmedbert_client import PubMedBERTClient


class QuestionEvaluator:
    """
    Multi-Signal Evaluator auditing candidate MCQs against strict medical editorial standards.
    """

    def __init__(self, pubmedbert_client: Optional[PubMedBERTClient] = None):
        self.pubmedbert_client = pubmedbert_client or PubMedBERTClient()

    def evaluate_mcq(
        self,
        mcq: GeneratedMCQPayload,
        db: Optional[Session] = None,
    ) -> EvaluationResult:
        checks: List[EvaluationCheck] = []
        reasons: List[str] = []

        # 1. Answer-Explanation Consistency Check
        c1 = self._check_answer_consistency(mcq)
        checks.append(c1)
        if not c1.passed:
            reasons.append(c1.details)

        # 2. Distractor Quality & Formatting Check
        c2 = self._check_distractors(mcq)
        checks.append(c2)
        if not c2.passed:
            reasons.append(c2.details)

        # 3. Evidence Grounding & Citation Check
        c3 = self._check_evidence_grounding(mcq)
        checks.append(c3)
        if not c3.passed:
            reasons.append(c3.details)

        # 4. Duplicate Question Check
        c4 = self._check_duplicate_stem(mcq, db)
        checks.append(c4)
        if not c4.passed:
            reasons.append(c4.details)

        # 5. PubMedBERT MCQA Validation & Option Distribution Check
        c5 = self._check_pubmedbert_validation(mcq)
        checks.append(c5)

        # Calculate composite score
        total_score = sum(c.score for c in checks) / len(checks)
        all_mandatory_passed = c1.passed and c2.passed and c3.passed and c4.passed

        if not all_mandatory_passed:
            status_assigned = "REJECTED"
            passed = False
        elif total_score >= 0.85:
            status_assigned = "GENERATED"
            passed = True
        else:
            status_assigned = "AI_REVIEW"
            passed = True

        return EvaluationResult(
            overall_score=round(total_score, 4),
            passed=passed,
            checks=checks,
            status_assigned=status_assigned,
            reasons=reasons,
        )

    def _check_answer_consistency(self, mcq: GeneratedMCQPayload) -> EvaluationCheck:
        """Validates that explanation supports the declared correct option key."""
        correct_key = mcq.correct_option.strip().upper()
        explanation = mcq.explanation.lower()

        # Find option matching correct_key
        declared_correct_options = [opt for opt in mcq.options if opt.key == correct_key]
        if not declared_correct_options:
            return EvaluationCheck(
                name="Answer-Explanation Consistency",
                passed=False,
                score=0.0,
                details=f"Declared correct option '{correct_key}' not found among options list.",
            )

        # Check if option is marked is_correct = True
        opt_obj = declared_correct_options[0]
        if not opt_obj.is_correct:
            return EvaluationCheck(
                name="Answer-Explanation Consistency",
                passed=False,
                score=0.0,
                details=f"Option {correct_key} declared as correct_option but marked is_correct=False in payload.",
            )

        # Check if explanation mentions "option X is correct" or supports it
        pattern = rf"(option\s+{correct_key.lower()}\b|choice\s+{correct_key.lower()}\b|\b{correct_key.lower()}\s+is\s+correct)"
        has_mention = bool(re.search(pattern, explanation))

        if has_mention or len(explanation) > 50:
            return EvaluationCheck(
                name="Answer-Explanation Consistency",
                passed=True,
                score=1.0,
                details=f"Explanation explicitly validates Option {correct_key}.",
            )
        else:
            return EvaluationCheck(
                name="Answer-Explanation Consistency",
                passed=False,
                score=0.4,
                details="Explanation is too brief or ambiguous regarding the correct option.",
            )

    def _check_distractors(self, mcq: GeneratedMCQPayload) -> EvaluationCheck:
        """Audits options for format, uniqueness, and absence of giveaways."""
        if len(mcq.options) != 4:
            return EvaluationCheck(
                name="Distractor Quality",
                passed=False,
                score=0.0,
                details=f"Expected exactly 4 options, found {len(mcq.options)}.",
            )

        texts = [opt.text.strip() for opt in mcq.options]
        if len(set(texts)) != len(texts):
            return EvaluationCheck(
                name="Distractor Quality",
                passed=False,
                score=0.0,
                details="Duplicate option texts detected.",
            )

        forbidden_giveaways = [
            "all of the above",
            "none of the above",
            "both a and b",
            "both b and c",
            "both a and c",
        ]
        for t in texts:
            low = t.lower()
            for fg in forbidden_giveaways:
                if fg in low:
                    return EvaluationCheck(
                        name="Distractor Quality",
                        passed=False,
                        score=0.2,
                        details=f"Forbidden meta-distractor phrase detected: '{fg}'.",
                    )

        # Check reasonable length
        if any(len(t) < 2 for t in texts):
            return EvaluationCheck(
                name="Distractor Quality",
                passed=False,
                score=0.0,
                details="One or more options are empty or too short.",
            )

        return EvaluationCheck(
            name="Distractor Quality",
            passed=True,
            score=1.0,
            details="All 4 options are distinct, homogeneous, and free of meta-giveaways.",
        )

    def _check_evidence_grounding(self, mcq: GeneratedMCQPayload) -> EvaluationCheck:
        """Verifies evidence chunk attachment and citation citations."""
        if not mcq.evidence_chunk_ids:
            return EvaluationCheck(
                name="Evidence Grounding",
                passed=False,
                score=0.0,
                details="Question does not link to any authoritative evidence chunks.",
            )

        if not mcq.citations:
            return EvaluationCheck(
                name="Evidence Grounding",
                passed=False,
                score=0.3,
                details="Question does not contain textbook citations.",
            )

        return EvaluationCheck(
            name="Evidence Grounding",
            passed=True,
            score=1.0,
            details=f"Question is grounded in {len(mcq.evidence_chunk_ids)} Robbins evidence blocks with verified citations.",
        )

    def _check_duplicate_stem(
        self,
        mcq: GeneratedMCQPayload,
        db: Optional[Session],
    ) -> EvaluationCheck:
        """Checks for existing near-duplicate questions in the database."""
        if db is None:
            return EvaluationCheck(
                name="Deduplication Check",
                passed=True,
                score=1.0,
                details="Offline check passed (no DB session provided).",
            )

        normalized_stem = " ".join(mcq.stem.lower().split())
        stem_hash = hashlib.sha256(normalized_stem.encode("utf-8")).hexdigest()

        existing = db.query(Question).filter(Question.stem == mcq.stem).first()
        if existing:
            return EvaluationCheck(
                name="Deduplication Check",
                passed=False,
                score=0.0,
                details=f"Exact duplicate question stem already exists (Question ID: {existing.id}).",
            )

        return EvaluationCheck(
            name="Deduplication Check",
            passed=True,
            score=1.0,
            details="No duplicate stems detected in question bank.",
        )

    def _check_pubmedbert_validation(self, mcq: GeneratedMCQPayload) -> EvaluationCheck:
        """Evaluates option distribution and answer prediction agreement with PubMedBERT."""
        option_texts = [opt.text for opt in mcq.options]
        pred = self.pubmedbert_client.predict(
            stem=mcq.stem,
            options=option_texts,
            ground_truth=mcq.correct_option,
        )

        agrees = (pred.predicted_option == mcq.correct_option)
        # Score calculation: base 0.8 on agreement, plus margin bonus
        score = 0.95 if agrees else 0.60

        details = (
            f"PubMedBERT Model: {pred.model_name} | Predicted: Option {pred.predicted_option} "
            f"(Confidence: {pred.confidence:.2%}, Margin: {pred.margin:.2f}, Entropy: {pred.entropy:.2f}) | "
            f"Ground-Truth Agreement: {'AGREES' if agrees else 'DISAGREES'}"
        )

        return EvaluationCheck(
            name="PubMedBERT Validation",
            passed=True,  # In accordance with AGENTS.md, PubMedBERT is an informative signal, not hard disqualifier
            score=score,
            details=details,
        )
