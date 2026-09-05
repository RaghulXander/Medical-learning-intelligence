"""Controlled, evidence-bound question generation for the M19D calibration pilot."""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
import uuid
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from backend.services.hybrid_retrieval_service import (
    HybridEvidenceReceipt,
    HybridRetrievalOutcome,
    HybridRetrievalService,
)
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


M19D_COHORT_ID = "M19D_TEXT_PILOT_V1"
M19D_PROMPT_VERSION = "m19d-text-sba-v1"
M19D_CORPUS_MANIFEST_HASH = "88424b7e4561348083d43f1947b14f732bc225ff8e08b23071737f852975d787"
M19D_DATASET_HASH = "09b1c01e47a47837ebc989da834f426704ab2a79828d03e6e66769f7a18e2bd9"
M19D_EMBEDDING_RUN_ID = "cba90495-1c99-416d-989d-fdd246212218"
M19D_EMBEDDING_CONFIG_HASH = "07cf615945e78cf9258d0c6788152ae9ad99e8dea93ecbde285261b1ca59bd6f"
M19D_RETRIEVAL_CONFIG_HASH = "7fdc2579c9a8bbe042d2585daeab764a6fd694c5a54f320ad78842a3f9ce64d6"
M19D_ALLOWED_DOMAINS = {
    "diagnostic_techniques",
    "general_pathology",
    "hematopathology",
    "neoplasia",
    "systemic_pathology",
}
M19D_ALLOWED_SOURCES = {
    "robbins_review",
    "robbins_pathologic_basis_11th",
    "sternberg_review_2nd",
}


class PilotBlueprintRow(BaseModel):
    id: str = Field(pattern=r"^m19d-[a-z]+-[0-9]{2}$")
    domain: str
    topic: str = Field(min_length=2)
    subtopic: str = Field(min_length=2)
    learning_objective: str = Field(min_length=10)
    retrieval_query: str = Field(min_length=10)
    target_exam: str = "NEET_SS"
    difficulty: str
    cognitive_level: str
    question_type: str = "SINGLE_BEST_ANSWER"
    source_requirements: List[str] = Field(min_length=1)
    minimum_evidence_count: int = Field(default=1, ge=1, le=5)

    @model_validator(mode="after")
    def validate_scope(self) -> "PilotBlueprintRow":
        if self.domain not in M19D_ALLOWED_DOMAINS:
            raise ValueError(f"Unsupported M19D domain: {self.domain}")
        if self.target_exam != "NEET_SS":
            raise ValueError("M19D rows must target NEET_SS")
        if self.question_type != "SINGLE_BEST_ANSWER":
            raise ValueError("M19D supports only SINGLE_BEST_ANSWER")
        if self.difficulty not in {"MEDIUM", "HARD"}:
            raise ValueError("M19D difficulty must be MEDIUM or HARD")
        if self.cognitive_level not in {"UNDERSTANDING", "APPLICATION", "ANALYSIS"}:
            raise ValueError("M19D excludes recall-only blueprint rows")
        unknown_sources = set(self.source_requirements) - M19D_ALLOWED_SOURCES
        if unknown_sources:
            raise ValueError(f"Unsupported M19D source requirements: {sorted(unknown_sources)}")
        return self


class PilotBlueprint(BaseModel):
    schema_version: int = 1
    blueprint_id: str
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    target_exam: str = "NEET_SS"
    accepted_corpus_manifest_hash: str
    accepted_dataset_hash: str
    accepted_embedding_run_id: str
    accepted_embedding_config_hash: str
    accepted_retrieval_config_hash: str
    rows: List[PilotBlueprintRow]

    @model_validator(mode="after")
    def validate_pilot(self) -> "PilotBlueprint":
        if self.blueprint_id != "m19d-text-pilot-v1":
            raise ValueError("Unexpected M19D blueprint ID")
        if self.target_exam != "NEET_SS":
            raise ValueError("M19D blueprint must target NEET_SS")
        if len(self.rows) != 50 or len({row.id for row in self.rows}) != 50:
            raise ValueError("M19D blueprint requires exactly 50 unique rows")
        counts = {domain: 0 for domain in M19D_ALLOWED_DOMAINS}
        for row in self.rows:
            counts[row.domain] += 1
        if any(count != 10 for count in counts.values()):
            raise ValueError(f"M19D requires 10 rows per domain; found {counts}")
        expected = {
            "accepted_corpus_manifest_hash": M19D_CORPUS_MANIFEST_HASH,
            "accepted_dataset_hash": M19D_DATASET_HASH,
            "accepted_embedding_run_id": M19D_EMBEDDING_RUN_ID,
            "accepted_embedding_config_hash": M19D_EMBEDDING_CONFIG_HASH,
            "accepted_retrieval_config_hash": M19D_RETRIEVAL_CONFIG_HASH,
        }
        for field_name, value in expected.items():
            if getattr(self, field_name) != value:
                raise ValueError(f"Blueprint {field_name} does not match accepted M19C artifact")
        if self.status == "APPROVED" and (not self.approved_by or not self.approved_at):
            raise ValueError("Approved blueprint requires approved_by and approved_at")
        if self.status not in {"DRAFT", "APPROVED"}:
            raise ValueError("Blueprint status must be DRAFT or APPROVED")
        return self

    @property
    def is_approved(self) -> bool:
        return self.status == "APPROVED" and bool(self.approved_by and self.approved_at)


class ProviderOption(BaseModel):
    text: str = Field(min_length=2)
    is_correct: bool
    rationale: str = Field(min_length=10)
    evidence_chunk_ids: List[str] = Field(min_length=1)


class ProviderCandidate(BaseModel):
    stem: str = Field(min_length=20)
    options: List[ProviderOption] = Field(min_length=4, max_length=4)
    explanation: str = Field(min_length=30)
    explanation_evidence_chunk_ids: List[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_answer(self) -> "ProviderCandidate":
        if sum(option.is_correct for option in self.options) != 1:
            raise ValueError("Provider candidate must contain exactly one correct option")
        normalized = [normalize_text(option.text) for option in self.options]
        if len(set(normalized)) != 4:
            raise ValueError("Provider candidate options must be unique")
        return self


@dataclass(frozen=True)
class ProviderReceipt:
    provider: str
    model: str
    model_version: Optional[str]
    project: str
    location: str
    prompt_version: str
    response_id: Optional[str]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    total_tokens: Optional[int]
    latency_ms: int


@dataclass(frozen=True)
class PilotSignal:
    name: str
    passed: bool
    score: float
    details: str


@dataclass(frozen=True)
class PilotEvaluation:
    passed: bool
    quality_score: float
    status: str
    signals: List[PilotSignal]
    duplicate_signals: Dict[str, Any]


def normalize_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_blueprint(path: Path) -> tuple[PilotBlueprint, str]:
    raw = path.read_bytes()
    blueprint = PilotBlueprint.model_validate_json(raw)
    return blueprint, hashlib.sha256(raw).hexdigest()


def evidence_packet_hash(receipts: Sequence[HybridEvidenceReceipt]) -> str:
    return canonical_hash(
        [
            {
                key: value
                for key, value in receipt.to_dict().items()
                if key != "content"
            }
            for receipt in receipts
        ]
    )


def evidence_metadata(receipts: Sequence[HybridEvidenceReceipt]) -> List[Dict[str, Any]]:
    return [
        {key: value for key, value in receipt.to_dict().items() if key != "content"}
        for receipt in receipts
    ]


def build_server_citations(receipts: Sequence[HybridEvidenceReceipt]) -> List[str]:
    citations: List[str] = []
    for receipt in receipts:
        page = receipt.textbook_page if receipt.textbook_page is not None else receipt.pdf_page
        page_label = f"p. {page}" if page is not None else "page unavailable"
        edition = f", {receipt.edition}" if receipt.edition else ""
        citations.append(f"{receipt.source_title}{edition}, {page_label}")
    return citations


def validate_evidence_mapping(
    candidate: ProviderCandidate,
    receipts: Sequence[HybridEvidenceReceipt],
) -> None:
    allowed = {receipt.chunk_id for receipt in receipts}
    mappings: Iterable[List[str]] = [
        candidate.explanation_evidence_chunk_ids,
        *(option.evidence_chunk_ids for option in candidate.options),
    ]
    for mapping in mappings:
        if not mapping or not set(mapping).issubset(allowed):
            raise ValueError("Candidate claim mapping references absent evidence")


def shuffle_candidate(
    candidate: ProviderCandidate,
    *,
    seed_material: str,
) -> tuple[List[Dict[str, Any]], str, int]:
    seed = int(hashlib.sha256(seed_material.encode("utf-8")).hexdigest()[:16], 16)
    indexes = list(range(4))
    random.Random(seed).shuffle(indexes)
    stored: List[Dict[str, Any]] = []
    correct_option = ""
    for new_index, old_index in enumerate(indexes):
        key = chr(65 + new_index)
        option = candidate.options[old_index]
        stored.append(
            {
                "id": key,
                "text": option.text.strip(),
                "is_correct": option.is_correct,
                "rationale": option.rationale.strip(),
                "evidence_chunk_ids": list(option.evidence_chunk_ids),
            }
        )
        if option.is_correct:
            correct_option = key
    if not correct_option:
        raise ValueError("Candidate has no correct option after shuffling")
    return stored, correct_option, seed


def _has_source_overlap(candidate_text: str, evidence: Sequence[str], words: int = 20) -> bool:
    candidate_tokens = normalize_text(candidate_text).split()
    if len(candidate_tokens) < words:
        return False
    candidate_ngrams = {
        tuple(candidate_tokens[index : index + words])
        for index in range(len(candidate_tokens) - words + 1)
    }
    for source in evidence:
        source_tokens = normalize_text(source).split()
        for index in range(len(source_tokens) - words + 1):
            if tuple(source_tokens[index : index + words]) in candidate_ngrams:
                return True
    return False


def evaluate_candidate(
    db: Session,
    *,
    row: PilotBlueprintRow,
    candidate: ProviderCandidate,
    options: List[Dict[str, Any]],
    evidence: Sequence[HybridEvidenceReceipt],
) -> PilotEvaluation:
    signals: List[PilotSignal] = []
    correct_count = sum(option["is_correct"] for option in options)
    structure_passed = len(options) == 4 and correct_count == 1
    signals.append(PilotSignal("single_best_answer_structure", structure_passed, float(structure_passed), f"correct_options={correct_count}"))

    mapped = {chunk_id for option in options for chunk_id in option["evidence_chunk_ids"]}
    mapped.update(candidate.explanation_evidence_chunk_ids)
    evidence_passed = bool(mapped) and mapped.issubset({item.chunk_id for item in evidence})
    signals.append(PilotSignal("claim_evidence_mapping", evidence_passed, float(evidence_passed), f"mapped_chunks={len(mapped)}"))

    combined = " ".join(
        [candidate.stem, candidate.explanation]
        + [option["text"] for option in options]
        + [option["rationale"] for option in options]
    )
    copied = _has_source_overlap(combined, [item.content for item in evidence])
    signals.append(PilotSignal("source_overlap", not copied, float(not copied), "20-word verbatim overlap detected" if copied else "No 20-word verbatim overlap detected"))

    normalized = normalize_text(candidate.stem)
    exact_hash = hashlib.sha256(candidate.stem.encode("utf-8")).hexdigest()
    norm_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    exact = db.query(Question.id).filter(Question.exact_stem_hash == exact_hash).first()
    normalized_match = db.query(Question.id).filter(Question.norm_stem_hash == norm_hash).first()
    semantic_id: Optional[str] = None
    semantic_ratio = 0.0
    if not exact and not normalized_match:
        for existing_id, stem in db.query(Question.id, Question.stem).all():
            ratio = SequenceMatcher(None, normalized, normalize_text(stem)).ratio()
            if ratio > semantic_ratio:
                semantic_ratio = ratio
                semantic_id = str(existing_id)
    duplicate = bool(exact or normalized_match or semantic_ratio >= 0.90)
    duplicate_details = {
        "exact_match_id": str(exact[0]) if exact else None,
        "normalized_match_id": str(normalized_match[0]) if normalized_match else None,
        "nearest_semantic_id": semantic_id,
        "nearest_semantic_ratio": round(semantic_ratio, 4),
    }
    signals.append(PilotSignal("duplicate_check", not duplicate, float(not duplicate), json.dumps(duplicate_details, sort_keys=True)))

    objective_terms = set(normalize_text(f"{row.topic} {row.subtopic} {row.learning_objective}").split())
    candidate_terms = set(normalize_text(f"{candidate.stem} {candidate.explanation}").split())
    meaningful = {term for term in objective_terms if len(term) > 3}
    objective_score = len(meaningful & candidate_terms) / len(meaningful) if meaningful else 0.0
    objective_passed = objective_score >= 0.15
    signals.append(PilotSignal("objective_fit", objective_passed, min(1.0, objective_score / 0.35), f"term_overlap={objective_score:.3f}"))

    mandatory = [signal for signal in signals if signal.name != "objective_fit"]
    passed = all(signal.passed for signal in mandatory) and objective_passed
    quality_score = round(sum(signal.score for signal in signals) / len(signals), 4)
    return PilotEvaluation(
        passed=passed,
        quality_score=quality_score,
        status="HUMAN_REVIEW" if passed else "AI_REVIEW",
        signals=signals,
        duplicate_signals=duplicate_details,
    )


class VertexPilotGenerator:
    """One-request Vertex AI structured-output generator for an M19D row."""

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        project: Optional[str] = None,
        location: Optional[str] = None,
    ) -> None:
        self.model = model or os.getenv("M19D_VERTEX_MODEL", "gemini-2.5-flash")
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
        self.location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        if not self.project:
            raise ValueError("GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID is required")
        from google import genai

        self.client = genai.Client(vertexai=True, project=self.project, location=self.location)

    def generate(
        self,
        *,
        row: PilotBlueprintRow,
        evidence: Sequence[HybridEvidenceReceipt],
    ) -> tuple[ProviderCandidate, ProviderReceipt]:
        if not evidence:
            raise ValueError("Vertex generation requires retrieved evidence")
        evidence_blocks = "\n\n".join(
            f"EVIDENCE chunk_id={item.chunk_id}\n{item.content[:12_000]}" for item in evidence
        )
        prompt = f"""Create one NEET-SS pathology single-best-answer MCQ.

Blueprint ID: {row.id}
Domain: {row.domain}
Topic: {row.topic}
Subtopic: {row.subtopic}
Learning objective: {row.learning_objective}
Difficulty: {row.difficulty}
Cognitive level: {row.cognitive_level}

Use only the evidence blocks below. If they cannot support the answer,
explanation, and every factual distractor rationale, do not add outside facts.
Return four mutually exclusive options with exactly one correct answer. Map
every option rationale and the explanation to one or more supplied chunk IDs.
Do not write citations, source titles, page numbers, quotations, or evidence
not present below. Paraphrase the source and avoid long verbatim sequences.

{evidence_blocks}
"""
        from google.genai import types

        started = time.monotonic()
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are a pathology examination item writer. Work only from supplied evidence, "
                    "return exactly one structured candidate, and never invent a citation."
                ),
                response_mime_type="application/json",
                response_schema=ProviderCandidate,
                temperature=0.15,
                max_output_tokens=2200,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        latency_ms = round((time.monotonic() - started) * 1000)
        parsed = getattr(response, "parsed", None)
        candidate = parsed if isinstance(parsed, ProviderCandidate) else ProviderCandidate.model_validate_json(response.text)
        usage = getattr(response, "usage_metadata", None)
        receipt = ProviderReceipt(
            provider="google_vertex_ai",
            model=self.model,
            model_version=getattr(response, "model_version", None),
            project=self.project,
            location=self.location,
            prompt_version=M19D_PROMPT_VERSION,
            response_id=getattr(response, "response_id", None),
            input_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
            total_tokens=getattr(usage, "total_token_count", None),
            latency_ms=latency_ms,
        )
        return candidate, receipt


class M19DPilotService:
    def __init__(
        self,
        *,
        retrieval: HybridRetrievalService,
        generator: VertexPilotGenerator,
        blueprint_id: str,
        blueprint_hash: str,
    ) -> None:
        self.retrieval = retrieval
        self.generator = generator
        self.blueprint_id = blueprint_id
        self.blueprint_hash = blueprint_hash

    @staticmethod
    def external_source_id(row_id: str) -> str:
        return f"m19d-v1-{row_id}"

    def generate_row(self, db: Session, row: PilotBlueprintRow) -> tuple[Question, bool]:
        existing = db.query(Question).filter_by(external_source_id=self.external_source_id(row.id)).first()
        if existing:
            return existing, False

        source_filter = row.source_requirements[0] if len(row.source_requirements) == 1 else None
        outcome: HybridRetrievalOutcome = self.retrieval.search(
            db,
            row.retrieval_query,
            top_k=5 if source_filter else 15,
            embedding_run_id=M19D_EMBEDDING_RUN_ID,
            source_short_name=source_filter,
        )
        scoped_results = [
            receipt
            for receipt in outcome.results
            if receipt.source_short_name in row.source_requirements
        ][:5]
        if outcome.status != "OK" or len(scoped_results) < row.minimum_evidence_count:
            raise ValueError("INSUFFICIENT_EVIDENCE")
        if outcome.embedding_run_id != M19D_EMBEDDING_RUN_ID:
            raise ValueError("Embedding run changed during M19D generation")
        if outcome.retrieval_configuration_hash != M19D_RETRIEVAL_CONFIG_HASH:
            raise ValueError("Retrieval configuration changed during M19D generation")
        outcome = HybridRetrievalOutcome(
            status="OK",
            query=outcome.query,
            embedding_run_id=outcome.embedding_run_id,
            retrieval_configuration_hash=outcome.retrieval_configuration_hash,
            results=scoped_results,
        )

        candidate, provider_receipt = self.generator.generate(row=row, evidence=outcome.results)
        validate_evidence_mapping(candidate, outcome.results)
        options, correct_option, shuffle_seed = shuffle_candidate(
            candidate,
            seed_material=f"{self.blueprint_hash}:{row.id}",
        )
        evaluation = evaluate_candidate(
            db,
            row=row,
            candidate=candidate,
            options=options,
            evidence=outcome.results,
        )
        normalized_stem = normalize_text(candidate.stem)
        exact_hash = hashlib.sha256(candidate.stem.encode("utf-8")).hexdigest()
        norm_hash = hashlib.sha256(normalized_stem.encode("utf-8")).hexdigest()
        content_hash = canonical_hash(
            {
                "stem": candidate.stem,
                "options": options,
                "correct_option": correct_option,
                "explanation": candidate.explanation,
            }
        )
        citations = build_server_citations(outcome.results)
        packet_hash = evidence_packet_hash(outcome.results)
        status = QuestionStatus.HUMAN_REVIEW if evaluation.passed else QuestionStatus.AI_REVIEW
        question = Question(
            id=str(uuid.uuid4()),
            external_source="AI_GENERATED_M19D",
            external_source_id=self.external_source_id(row.id),
            speciality="Pathology",
            subject="Pathology",
            topic_name_original=row.topic,
            topic_name_normalized=normalize_text(row.topic),
            topic_mapping_status=TopicMappingStatus.MAPPED,
            learning_objective=row.learning_objective,
            question_type=QuestionType.SINGLE_BEST_ANSWER,
            stem=candidate.stem.strip(),
            options=options,
            correct_option=correct_option,
            correct_index=ord(correct_option) - ord("A"),
            is_labeled=True,
            explanation=candidate.explanation.strip(),
            difficulty=DifficultyLevel(row.difficulty.lower()),
            cognitive_level=CognitiveLevel(row.cognitive_level.lower()),
            target_exam_levels=["NEET_SS"],
            status=status,
            quality_score=evaluation.quality_score,
            classification_source=ClassificationSource.AI_CLASSIFIED,
            classification_status=ClassificationStatus.PENDING_REVIEW,
            classification_confidence=evaluation.quality_score,
            knowledge_era="SOURCE_EDITION_BOUND",
            source_version=M19D_DATASET_HASH,
            origin_cohort=M19D_COHORT_ID,
            tags=["M19D", "TEXT_ONLY", "EVIDENCE_GROUNDED", row.domain.upper()],
            has_images=False,
            image_assets=[],
            content_hash=content_hash,
            exact_stem_hash=exact_hash,
            norm_stem_hash=norm_hash,
            duplicate_signals=evaluation.duplicate_signals,
            metadata_json={
                "pilot": {
                    "blueprint_id": self.blueprint_id,
                    "blueprint_hash": self.blueprint_hash,
                    "blueprint_row_id": row.id,
                    "cohort_id": M19D_COHORT_ID,
                    "shuffle_seed": shuffle_seed,
                },
                "accepted_artifacts": {
                    "corpus_manifest_hash": M19D_CORPUS_MANIFEST_HASH,
                    "dataset_hash": M19D_DATASET_HASH,
                    "embedding_run_id": M19D_EMBEDDING_RUN_ID,
                    "embedding_config_hash": M19D_EMBEDDING_CONFIG_HASH,
                    "retrieval_config_hash": M19D_RETRIEVAL_CONFIG_HASH,
                },
                "provider_receipt": asdict(provider_receipt),
                "evidence_packet_hash": packet_hash,
                "evidence_receipts": evidence_metadata(outcome.results),
                "explanation_evidence_chunk_ids": candidate.explanation_evidence_chunk_ids,
                "citations": citations,
                "evaluation_signals": [asdict(signal) for signal in evaluation.signals],
            },
            created_by="m19d_vertex_pilot",
        )
        for receipt in outcome.results:
            chunk = db.get(DocumentChunk, receipt.chunk_id)
            if not chunk or chunk.content_hash != receipt.content_hash or not chunk.document:
                raise ValueError(f"Evidence receipt mismatch for chunk {receipt.chunk_id}")
            question.evidence_links.append(
                QuestionEvidence(
                    id=str(uuid.uuid4()),
                    question_id=question.id,
                    source_id=receipt.source_id,
                    document_id=chunk.document_id,
                    chunk_id=chunk.id,
                    chapter=receipt.chapter_name,
                    section=receipt.section_heading,
                    page_range=str(receipt.textbook_page if receipt.textbook_page is not None else receipt.pdf_page),
                    excerpt=None,
                    verification_status=VerificationStatus.AI_SUGGESTED,
                    confidence=evaluation.quality_score,
                )
            )
        db.add(question)
        db.commit()
        db.refresh(question)
        return question, True
