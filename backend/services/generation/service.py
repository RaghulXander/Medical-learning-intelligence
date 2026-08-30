"""
backend/services/generation/service.py

Orchestration Service for Evidence-Grounded AI Question Generation,
Multi-Signal Evaluation, and Cryptographic Evidence Attachment.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from database.models import (
    ClassificationSource,
    ClassificationStatus,
    CognitiveLevel,
    DifficultyLevel,
    DocumentChunk,
    Question,
    QuestionEvidence,
    QuestionStatus,
    QuestionType,
    TopicMappingStatus,
    VerificationStatus,
)
from backend.services.generation.evaluator import QuestionEvaluator
from backend.services.generation.generator import (
    MCQGeneratorInterface,
    get_mcq_generator,
)
from backend.services.generation.models import (
    EvaluationResult,
    GeneratedMCQPayload,
    QuestionBlueprint,
)
from backend.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class QuestionGenerationService:
    """
    Orchestration Engine managing blueprint resolution, authoritative evidence retrieval,
    model synthesis, evaluation audits, and database persistence.
    """

    def __init__(
        self,
        retrieval_service: Optional[RetrievalService] = None,
        evaluator: Optional[QuestionEvaluator] = None,
    ):
        self.retrieval_service = retrieval_service or RetrievalService()
        self.evaluator = evaluator or QuestionEvaluator()

    def generate_question_from_blueprint(
        self,
        db: Session,
        blueprint: QuestionBlueprint,
        generator: Optional[MCQGeneratorInterface] = None,
        persist: bool = True,
    ) -> Tuple[Question, EvaluationResult, GeneratedMCQPayload]:
        """
        Executes end-to-end evidence-grounded question generation pipeline.
        """
        # Step 1: Retrieve Authoritative Evidence
        evidence_query = f"{blueprint.topic} {blueprint.learning_objective}"
        evidence_results = self.retrieval_service.search_evidence(
            db=db,
            query=evidence_query,
            top_k=3,
            min_score=0.1,
            chapter_filter=blueprint.subtopic,
        )

        if not evidence_results:
            # Fallback to broader query on topic
            evidence_results = self.retrieval_service.search_evidence(
                db=db,
                query=blueprint.topic,
                top_k=3,
                min_score=0.05,
            )

        if not evidence_results:
            raise ValueError(
                f"No authoritative Robbins pathology evidence blocks found for topic '{blueprint.topic}'. "
                "Generation cannot proceed without verified reference grounding."
            )

        # Step 2: Model Generation
        mcq_gen = generator or get_mcq_generator()
        mcq_payload = mcq_gen.generate_mcq(blueprint=blueprint, evidence=evidence_results)

        # Step 3: Multi-Signal Evaluation
        eval_result = self.evaluator.evaluate_mcq(mcq=mcq_payload, db=db)

        # Map enum values safely
        diff_val = DifficultyLevel(blueprint.difficulty.lower()) if blueprint.difficulty.lower() in [e.value for e in DifficultyLevel] else DifficultyLevel.MEDIUM
        cog_val = CognitiveLevel(blueprint.cognitive_level.lower()) if blueprint.cognitive_level.lower() in [e.value for e in CognitiveLevel] else CognitiveLevel.APPLICATION
        qtype_val = QuestionType(blueprint.question_type.lower()) if blueprint.question_type.lower() in [e.value for e in QuestionType] else QuestionType.SINGLE_BEST_ANSWER

        # Format options dictionary
        opt_dicts = [
            {
                "id": opt.key,
                "text": opt.text,
                "is_correct": opt.is_correct,
                "rationale": opt.rationale,
            }
            for opt in mcq_payload.options
        ]

        correct_idx = ["A", "B", "C", "D"].index(mcq_payload.correct_option) if mcq_payload.correct_option in ["A", "B", "C", "D"] else 0

        # Hashes for deduplication
        norm_stem = " ".join(mcq_payload.stem.lower().split())
        exact_stem_hash = hashlib.sha256(mcq_payload.stem.encode("utf-8")).hexdigest()
        norm_stem_hash = hashlib.sha256(norm_stem.encode("utf-8")).hexdigest()
        content_hash = hashlib.sha256(
            f"{mcq_payload.stem}|{mcq_payload.correct_option}|{mcq_payload.explanation}".encode("utf-8")
        ).hexdigest()

        status_enum = QuestionStatus(eval_result.status_assigned)

        question = Question(
            id=str(uuid.uuid4()),
            external_source="AI_GENERATED",
            external_source_id=f"ai-gen-{uuid.uuid4().hex[:12]}",
            speciality=blueprint.speciality,
            subject=blueprint.subject,
            topic_name_original=blueprint.topic,
            topic_name_normalized=blueprint.topic.lower().strip(),
            topic_mapping_status=TopicMappingStatus.MAPPED,
            learning_objective=blueprint.learning_objective,
            question_type=qtype_val,
            stem=mcq_payload.stem,
            options=opt_dicts,
            correct_option=mcq_payload.correct_option,
            correct_index=correct_idx,
            is_labeled=True,
            explanation=mcq_payload.explanation,
            difficulty=diff_val,
            cognitive_level=cog_val,
            target_exam_levels=[blueprint.target_exam],
            status=status_enum,
            quality_score=eval_result.overall_score,
            classification_source=ClassificationSource.AI_CLASSIFIED,
            classification_status=ClassificationStatus.PENDING_REVIEW,
            classification_confidence=0.95,
            knowledge_era="CURRENT",
            content_hash=content_hash,
            exact_stem_hash=exact_stem_hash,
            norm_stem_hash=norm_stem_hash,
            metadata_json={
                "generator_metadata": mcq_payload.metadata,
                "evaluation_checks": [c.to_dict() for c in eval_result.checks],
                "citations": mcq_payload.citations,
            },
            created_by="ai_question_generator",
        )

        # Attach QuestionEvidence records linking directly to Robbins chunks
        for ev in evidence_results:
            chunk = db.query(DocumentChunk).filter(DocumentChunk.id == ev.chunk_id).first()
            if chunk and chunk.document:
                evidence_link = QuestionEvidence(
                    id=str(uuid.uuid4()),
                    question_id=question.id,
                    source_id=chunk.document.source_id,
                    document_id=chunk.document_id,
                    chunk_id=chunk.id,
                    chapter=chunk.chapter_name,
                    section=chunk.section_heading,
                    page_range=str(chunk.textbook_page or chunk.pdf_page),
                    excerpt=chunk.content[:400],
                    verification_status=VerificationStatus.AI_SUGGESTED,
                    confidence=0.95,
                )
                question.evidence_links.append(evidence_link)

        if persist:
            db.add(question)
            db.commit()
            db.refresh(question)
            logger.info(
                f"✨ Successfully generated & persisted Question {question.id} "
                f"(Status: {question.status.value}, Score: {eval_result.overall_score})"
            )

        return question, eval_result, mcq_payload
