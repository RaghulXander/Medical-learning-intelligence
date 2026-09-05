"""
backend/services/generation/generator.py

Evidence-Grounded MCQ Generation Engine.
Synthesizes clinical-vignette and conceptual pathology MCQs strictly grounded in
retrieved Robbins & Cotran reference evidence blocks using Google Gemini API or Mock provider.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from backend.services.generation.models import (
    GeneratedMCQPayload,
    GeneratedOption,
    QuestionBlueprint,
)
from backend.services.retrieval_service import EvidenceSearchResult

logger = logging.getLogger(__name__)


class MCQGeneratorInterface:
    """Interface for MCQ generation implementations."""

    def generate_mcq(
        self,
        blueprint: QuestionBlueprint,
        evidence: List[EvidenceSearchResult],
    ) -> GeneratedMCQPayload:
        raise NotImplementedError


class GeminiMCQGenerator(MCQGeneratorInterface):
    """
    Evidence-grounded question generator using Google Gemini 2.5 Flash / Pro.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required for GeminiMCQGenerator.")

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
        except ImportError:
            raise ImportError("Please install google-genai: pip install google-genai")

    def generate_mcq(
        self,
        blueprint: QuestionBlueprint,
        evidence: List[EvidenceSearchResult],
    ) -> GeneratedMCQPayload:
        if not evidence:
            raise ValueError("Cannot generate MCQ without supporting reference evidence.")

        evidence_text_blocks = []
        citations = []
        chunk_ids = []

        for idx, ev in enumerate(evidence, start=1):
            chunk_ids.append(ev.chunk_id)
            citations.append(ev.citation_label)
            evidence_text_blocks.append(
                f"--- EVIDENCE BLOCK {idx} ({ev.citation_label}) ---\n{ev.content}\n"
            )

        combined_evidence = "\n".join(evidence_text_blocks)

        system_instruction = (
            "You are a Senior Professor of Pathology and Master Medical Examiner for NEET-PG, NEET-SS, and MD Pathology. "
            "Your task is to write a high-yield, conceptually rigorous Multiple Choice Question (Single Best Answer) "
            "based STRICTLY on the authoritative Robbins & Cotran textbook evidence provided below. "
            "CRITICAL INVARIANTS:\n"
            "1. Ground every medical fact directly in the provided evidence. DO NOT hallucinate textbook facts.\n"
            "2. Create a realistic clinical or diagnostic scenario in the stem matching the requested cognitive level and difficulty. For VERY_HARD difficulty, craft deep consultant-level diagnostic vignettes involving complex differential mimics, multi-parameter IHC panels, or molecular-morphologic integration where standard single-factor recall is insufficient.\n"
            "3. Formulate 4 mutually exclusive options (A, B, C, D). Avoid 'All of the above' or 'None of the above'.\n"
            "4. Provide a detailed educational explanation explaining why the correct option is right and why each distractor is wrong, citing the textbook edition and page number.\n"
            "5. Return ONLY a valid JSON object matching the exact schema."
        )

        prompt = f"""
BLUEPRINT:
- Speciality: {blueprint.speciality}
- Subject: {blueprint.subject}
- Topic: {blueprint.topic}
- Subtopic: {blueprint.subtopic or 'General'}
- Learning Objective: {blueprint.learning_objective}
- Target Exam: {blueprint.target_exam}
- Difficulty Level: {blueprint.difficulty}
- Cognitive Level: {blueprint.cognitive_level}
- Question Type: {blueprint.question_type}

AUTHORITATIVE ROBBINS EVIDENCE:
{combined_evidence}

Generate a JSON object with this exact structure:
{{
  "stem": "Clinical or conceptual question stem...",
  "options": [
    {{"key": "A", "text": "Option A text", "is_correct": false, "rationale": "Why A is incorrect"}},
    {{"key": "B", "text": "Option B text", "is_correct": true, "rationale": "Why B is correct"}},
    {{"key": "C", "text": "Option C text", "is_correct": false, "rationale": "Why C is incorrect"}},
    {{"key": "D", "text": "Option D text", "is_correct": false, "rationale": "Why D is incorrect"}}
  ],
  "correct_option": "B",
  "explanation": "Comprehensive breakdown citing the provided Robbins reference with chapter/page numbers...",
  "learning_objective": "{blueprint.learning_objective}"
}}
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "system_instruction": system_instruction,
                    "response_mime_type": "application/json",
                    "temperature": 0.2,
                },
            )
            raw_json = response.text.strip()
            data = json.loads(raw_json)

            options = [
                GeneratedOption(
                    key=opt.get("key", chr(65 + i)),
                    text=opt.get("text", ""),
                    is_correct=opt.get("is_correct", False),
                    rationale=opt.get("rationale", ""),
                )
                for i, opt in enumerate(data.get("options", []))
            ]

            return GeneratedMCQPayload(
                stem=data.get("stem", ""),
                options=options,
                correct_option=data.get("correct_option", "A"),
                explanation=data.get("explanation", ""),
                learning_objective=blueprint.learning_objective,
                difficulty=blueprint.difficulty,
                cognitive_level=blueprint.cognitive_level,
                question_type=blueprint.question_type,
                evidence_chunk_ids=chunk_ids,
                citations=citations,
                metadata={"generator": f"gemini:{self.model_name}"},
            )
        except Exception as e:
            logger.error(f"Gemini MCQ Generation failed: {e}")
            raise


class MockEvidenceGroundedGenerator(MCQGeneratorInterface):
    """
    Deterministic Mock Generator for offline environments and unit testing.
    Constructs high-fidelity questions directly from Robbins evidence chunks.
    """

    def generate_mcq(
        self,
        blueprint: QuestionBlueprint,
        evidence: List[EvidenceSearchResult],
    ) -> GeneratedMCQPayload:
        if not evidence:
            raise ValueError("Cannot generate MCQ without supporting reference evidence.")

        top_ev = evidence[0]
        chunk_ids = [e.chunk_id for e in evidence]
        citations = [e.citation_label for e in evidence]

        # Extract first 2 sentences for context
        sentences = [s.strip() for s in re.split(r"[.!?]", top_ev.content) if len(s.strip()) > 15]
        core_point = sentences[0] if sentences else top_ev.content[:100]

        stem = (
            f"A surgical pathology specimen is evaluated for {blueprint.topic.lower()}. "
            f"Regarding {blueprint.learning_objective.lower()}, which of the following statements represents "
            f"the standard diagnostic finding described in authoritative pathology guidelines?"
        )

        options = [
            GeneratedOption(
                key="A",
                text=f"{core_point}.",
                is_correct=True,
                rationale=f"Correct. As stated in {top_ev.citation_label}: {core_point}.",
            ),
            GeneratedOption(
                key="B",
                text=f"The diagnostic criteria do not depend on {blueprint.learning_objective.lower()} in routine practice.",
                is_correct=False,
                rationale="Incorrect. Standard guidelines mandate specific scoring criteria for this finding.",
            ),
            GeneratedOption(
                key="C",
                text="The finding is solely observed in benign lesions and excludes malignancy.",
                is_correct=False,
                rationale="Incorrect. This is a characteristic pathological hallmark in neoplastic and systemic diseases.",
            ),
            GeneratedOption(
                key="D",
                text="Immunohistochemistry cannot differentiate this entity from mimics.",
                is_correct=False,
                rationale="Incorrect. Specific immunohistochemical panels readily confirm the diagnosis.",
            ),
        ]

        explanation = (
            f"According to {top_ev.citation_label}, {core_point}. "
            f"Option A is correct. Options B, C, and D represent incorrect diagnostic interpretations."
        )

        return GeneratedMCQPayload(
            stem=stem,
            options=options,
            correct_option="A",
            explanation=explanation,
            learning_objective=blueprint.learning_objective,
            difficulty=blueprint.difficulty,
            cognitive_level=blueprint.cognitive_level,
            question_type=blueprint.question_type,
            evidence_chunk_ids=chunk_ids,
            citations=citations,
            metadata={"generator": "mock:deterministic_evidence_generator"},
        )


def get_mcq_generator(
    force_mock: bool = False,
    model_name: str = "gemini-2.5-flash",
) -> MCQGeneratorInterface:
    """Factory providing Gemini or Mock generator depending on configuration."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if force_mock or not api_key:
        logger.info("Using MockEvidenceGroundedGenerator (Deterministic)")
        return MockEvidenceGroundedGenerator()
    return GeminiMCQGenerator(api_key=api_key, model_name=model_name)
