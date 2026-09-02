"""Deterministic, reversible question-to-ontology mapping suggestions."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence

from sqlalchemy.orm import Session, joinedload

from backend.domain.surgical_pathology_ontology import (
    OntologyMappingMethod,
    OntologyMappingRole,
    OntologyMappingReviewDecision,
    OntologyMappingRunStatus,
    OntologyNodeType,
)
from database.models import (
    OntologyAlias,
    OntologyMappingRun,
    OntologyNode,
    OntologyScheme,
    Question,
    QuestionOntologyMapping,
    VerificationStatus,
)


RULE_VERSION = "exact-topic-label-v1"
ELIGIBLE_NODE_TYPES = {
    OntologyNodeType.DISCIPLINE,
    OntologyNodeType.METHOD_GROUP,
    OntologyNodeType.METHOD,
    OntologyNodeType.ANATOMIC_SYSTEM,
    OntologyNodeType.ORGAN,
    OntologyNodeType.ANATOMIC_SITE,
    OntologyNodeType.DISEASE_FAMILY,
    OntologyNodeType.DIAGNOSTIC_ENTITY,
}


def normalize_mapping_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").casefold()
    normalized = re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())


@dataclass(frozen=True)
class MappingCandidate:
    question_id: str
    external_source_id: str
    input_field: str
    input_label: str
    normalized_label: str
    node_id: str
    node_code: str
    node_name: str
    match_basis: str
    lexical_confidence: float


@dataclass(frozen=True)
class AmbiguousMapping:
    question_id: str
    external_source_id: str
    input_label: str
    normalized_label: str
    candidate_node_codes: List[str]


@dataclass
class MappingPreview:
    scheme_id: str
    scheme_code: str
    ontology_version: str
    rule_version: str
    configuration_hash: str
    question_filter: Dict[str, object]
    input_count: int
    candidates: List[MappingCandidate]
    ambiguous: List[AmbiguousMapping]
    unmapped_question_ids: List[str]
    skipped_existing_count: int

    def summary(self) -> Dict[str, object]:
        return {
            "scheme": self.scheme_code,
            "ontology_version": self.ontology_version,
            "rule_version": self.rule_version,
            "configuration_hash": self.configuration_hash,
            "question_filter": self.question_filter,
            "input_count": self.input_count,
            "matched_count": len(self.candidates),
            "ambiguous_count": len(self.ambiguous),
            "unmapped_count": len(self.unmapped_question_ids),
            "skipped_existing_count": self.skipped_existing_count,
        }


@dataclass(frozen=True)
class _TermTarget:
    node: OntologyNode
    match_basis: str
    lexical_confidence: float


class QuestionOntologyMappingService:
    def __init__(self, rule_version: str = RULE_VERSION) -> None:
        self.rule_version = rule_version

    @staticmethod
    def _scheme(session: Session, scheme_code: str, ontology_version: str) -> OntologyScheme:
        scheme = (
            session.query(OntologyScheme)
            .filter_by(code=scheme_code, version=ontology_version)
            .one_or_none()
        )
        if scheme is None:
            raise ValueError(f"Ontology scheme {scheme_code} {ontology_version} is not seeded")
        return scheme

    @staticmethod
    def _term_index(session: Session, scheme: OntologyScheme) -> Dict[str, List[_TermTarget]]:
        nodes = (
            session.query(OntologyNode)
            .filter(OntologyNode.scheme_id == scheme.id, OntologyNode.node_type.in_(ELIGIBLE_NODE_TYPES))
            .options(joinedload(OntologyNode.aliases))
            .all()
        )
        index: Dict[str, List[_TermTarget]] = {}
        for node in nodes:
            preferred = normalize_mapping_text(node.preferred_name)
            if preferred:
                index.setdefault(preferred, []).append(
                    _TermTarget(node=node, match_basis="PREFERRED_NAME", lexical_confidence=1.0)
                )
            for alias in node.aliases:
                term = normalize_mapping_text(alias.alias)
                if not term:
                    continue
                confidence = (
                    1.0
                    if alias.verification_status == VerificationStatus.HUMAN_VERIFIED
                    else 0.95
                )
                index.setdefault(term, []).append(
                    _TermTarget(node=node, match_basis="ALIAS", lexical_confidence=confidence)
                )
        return index

    @staticmethod
    def _question_labels(question: Question) -> List[tuple[str, str]]:
        labels: List[tuple[str, str]] = []
        for field_name, value in (
            ("topic_name_normalized", question.topic_name_normalized),
            ("topic_name_original", question.topic_name_original),
            (
                "primary_topic.name",
                question.primary_topic.name if question.primary_topic is not None else None,
            ),
        ):
            if value and normalize_mapping_text(value):
                labels.append((field_name, value))
        return labels

    def preview(
        self,
        session: Session,
        *,
        scheme_code: str,
        ontology_version: str,
        subject: Optional[str] = "Pathology",
        speciality: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> MappingPreview:
        scheme = self._scheme(session, scheme_code, ontology_version)
        term_index = self._term_index(session, scheme)
        question_filter: Dict[str, object] = {
            "subject": subject,
            "speciality": speciality,
            "limit": limit,
        }
        config_payload = {
            "scheme_code": scheme_code,
            "ontology_version": ontology_version,
            "rule_version": self.rule_version,
            "question_filter": question_filter,
        }
        configuration_hash = hashlib.sha256(
            json.dumps(config_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        query = session.query(Question).options(joinedload(Question.primary_topic)).order_by(Question.id)
        if subject:
            query = query.filter(Question.subject == subject)
        if speciality:
            query = query.filter(Question.speciality == speciality)
        if limit:
            query = query.limit(limit)
        questions = query.all()

        active_question_ids = {
            row[0]
            for row in session.query(QuestionOntologyMapping.question_id)
            .filter(
                QuestionOntologyMapping.ontology_version == ontology_version,
                QuestionOntologyMapping.is_active.is_(True),
            )
            .all()
        }
        candidates: List[MappingCandidate] = []
        ambiguous: List[AmbiguousMapping] = []
        unmapped: List[str] = []
        skipped_existing = 0

        for question in questions:
            if question.id in active_question_ids:
                skipped_existing += 1
                continue
            matches: Dict[str, tuple[_TermTarget, str, str, str]] = {}
            for input_field, input_label in self._question_labels(question):
                normalized_label = normalize_mapping_text(input_label)
                for target in term_index.get(normalized_label, []):
                    existing = matches.get(target.node.id)
                    if existing is None or target.lexical_confidence > existing[0].lexical_confidence:
                        matches[target.node.id] = (
                            target,
                            input_field,
                            input_label,
                            normalized_label,
                        )
                if matches:
                    # Respect label precedence; do not let a lower-priority legacy
                    # field introduce a competing node after an exact match.
                    break

            if len(matches) == 1:
                target, input_field, input_label, normalized_label = next(iter(matches.values()))
                candidates.append(
                    MappingCandidate(
                        question_id=question.id,
                        external_source_id=question.external_source_id,
                        input_field=input_field,
                        input_label=input_label,
                        normalized_label=normalized_label,
                        node_id=target.node.id,
                        node_code=target.node.code,
                        node_name=target.node.preferred_name,
                        match_basis=target.match_basis,
                        lexical_confidence=target.lexical_confidence,
                    )
                )
            elif len(matches) > 1:
                first = next(iter(matches.values()))
                ambiguous.append(
                    AmbiguousMapping(
                        question_id=question.id,
                        external_source_id=question.external_source_id,
                        input_label=first[2],
                        normalized_label=first[3],
                        candidate_node_codes=sorted(item[0].node.code for item in matches.values()),
                    )
                )
            else:
                unmapped.append(question.id)

        return MappingPreview(
            scheme_id=scheme.id,
            scheme_code=scheme.code,
            ontology_version=scheme.version,
            rule_version=self.rule_version,
            configuration_hash=configuration_hash,
            question_filter=question_filter,
            input_count=len(questions),
            candidates=candidates,
            ambiguous=ambiguous,
            unmapped_question_ids=unmapped,
            skipped_existing_count=skipped_existing,
        )

    def apply(self, session: Session, preview: MappingPreview, *, actor: str) -> OntologyMappingRun:
        run = OntologyMappingRun(
            id=str(uuid.uuid4()),
            scheme_id=preview.scheme_id,
            ontology_version=preview.ontology_version,
            rule_version=preview.rule_version,
            status=OntologyMappingRunStatus.APPLIED,
            configuration_hash=preview.configuration_hash,
            question_filter=preview.question_filter,
            input_count=preview.input_count,
            matched_count=len(preview.candidates),
            ambiguous_count=len(preview.ambiguous),
            unmapped_count=len(preview.unmapped_question_ids),
            created_mapping_count=len(preview.candidates),
            created_by=actor,
            completed_at=datetime.now(timezone.utc),
        )
        session.add(run)
        session.flush()
        for candidate in preview.candidates:
            session.add(
                QuestionOntologyMapping(
                    id=str(uuid.uuid4()),
                    question_id=candidate.question_id,
                    node_id=candidate.node_id,
                    mapping_role=OntologyMappingRole.PRIMARY,
                    mapping_method=OntologyMappingMethod.RULE,
                    confidence=candidate.lexical_confidence,
                    verification_status=VerificationStatus.AI_SUGGESTED,
                    ontology_version=preview.ontology_version,
                    is_active=True,
                    mapping_run_id=run.id,
                    match_metadata={
                        "input_field": candidate.input_field,
                        "input_label": candidate.input_label,
                        "normalized_label": candidate.normalized_label,
                        "match_basis": candidate.match_basis,
                        "rule_version": preview.rule_version,
                        "confidence_semantics": "exact_lexical_match_not_medical_verification",
                    },
                    mapped_by=actor,
                )
            )
        session.flush()
        return run

    def rollback(self, session: Session, run_id: str, *, actor: str) -> int:
        run = session.get(OntologyMappingRun, run_id)
        if run is None:
            raise ValueError("Ontology mapping run not found")
        if run.status != OntologyMappingRunStatus.APPLIED:
            raise ValueError(f"Only APPLIED runs can be rolled back; found {run.status.value}")
        mappings = (
            session.query(QuestionOntologyMapping)
            .filter_by(mapping_run_id=run.id, is_active=True)
            .all()
        )
        for mapping in mappings:
            mapping.is_active = False
            metadata = dict(mapping.match_metadata or {})
            metadata["rolled_back_by"] = actor
            metadata["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
            mapping.match_metadata = metadata
        run.status = OntologyMappingRunStatus.ROLLED_BACK
        run.rolled_back_at = datetime.now(timezone.utc)
        session.flush()
        return len(mappings)

    def review(
        self,
        session: Session,
        mapping_id: str,
        *,
        decision: OntologyMappingReviewDecision,
        reviewer: str,
        corrected_node_code: Optional[str] = None,
    ) -> Optional[QuestionOntologyMapping]:
        mapping = session.get(QuestionOntologyMapping, mapping_id)
        if mapping is None:
            raise ValueError("Question ontology mapping not found")
        if not mapping.is_active or mapping.verification_status != VerificationStatus.AI_SUGGESTED:
            raise ValueError("Only active AI_SUGGESTED mappings can be reviewed")
        if decision == OntologyMappingReviewDecision.CORRECT and not corrected_node_code:
            raise ValueError("CORRECT requires corrected_node_code")
        if decision != OntologyMappingReviewDecision.CORRECT and corrected_node_code:
            raise ValueError("corrected_node_code is valid only for CORRECT")

        mapping.is_active = False
        mapping.reviewed_by = reviewer
        metadata = dict(mapping.match_metadata or {})
        metadata["review_decision"] = decision.value
        metadata["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        mapping.match_metadata = metadata

        if decision == OntologyMappingReviewDecision.REJECT:
            mapping.verification_status = VerificationStatus.REJECTED
            session.flush()
            return None

        target_node_id = mapping.node_id
        if decision == OntologyMappingReviewDecision.CORRECT:
            original_node = session.get(OntologyNode, mapping.node_id)
            corrected_node = (
                session.query(OntologyNode)
                .filter_by(scheme_id=original_node.scheme_id, code=corrected_node_code)
                .one_or_none()
            )
            if corrected_node is None:
                raise ValueError("Corrected ontology node was not found in the same scheme")
            target_node_id = corrected_node.id

        reviewed_mapping = QuestionOntologyMapping(
            id=str(uuid.uuid4()),
            question_id=mapping.question_id,
            node_id=target_node_id,
            mapping_role=mapping.mapping_role,
            mapping_method=OntologyMappingMethod.HUMAN,
            confidence=1.0,
            verification_status=VerificationStatus.HUMAN_VERIFIED,
            ontology_version=mapping.ontology_version,
            is_active=True,
            supersedes_mapping_id=mapping.id,
            mapping_run_id=None,
            match_metadata={
                "review_decision": decision.value,
                "source_mapping_id": mapping.id,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "confidence_semantics": "human_reviewed_mapping",
            },
            mapped_by=reviewer,
            reviewed_by=reviewer,
        )
        session.add(reviewed_mapping)
        session.flush()
        return reviewed_mapping
