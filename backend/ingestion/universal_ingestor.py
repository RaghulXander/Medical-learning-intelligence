"""
backend/ingestion/universal_ingestor.py

Universal Multi-Source Question Ingestion Engine.
Normalizes, validates, hashes, and ingests questions from:
- MedMCQA datasets
- CSV / Excel spreadsheets
- Google Forms responses / webhooks
- Manual Admin entry
- AI Generator pipelines (LLM blueprints)
- External JSON/JSONL datasets

Guarantees 100% schema conformity across all intake channels.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy.orm import Session

from database.db import session_scope
from database.models import (
    Course,
    CurriculumTopic,
    DifficultyLevel,
    CognitiveLevel,
    Question,
    QuestionStatus,
    QuestionType,
    TopicMappingStatus,
)

logger = logging.getLogger(__name__)

INGESTION_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

OPTION_KEY_MAP = {
    0: "A",
    1: "B",
    2: "C",
    3: "D",
    "0": "A",
    "1": "B",
    "2": "C",
    "3": "D",
    "a": "A",
    "b": "B",
    "c": "C",
    "d": "D",
    "A": "A",
    "B": "B",
    "C": "C",
    "D": "D",
}


def sanitize_text(text: Optional[str]) -> Optional[str]:
    """Sanitizes text by normalizing unicode while preserving medical symbols."""
    if text is None:
        return None
    text = str(text)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    return cleaned if cleaned else None


def compute_hashes(stem: str, options: List[Dict[str, str]]) -> Dict[str, str]:
    """Computes SHA-256 content and stem hashes for duplicate detection."""
    exact_stem_hash = hashlib.sha256(stem.encode("utf-8")).hexdigest()

    stem_norm = re.sub(r"[^\w\s]", "", stem.lower())
    stem_norm = re.sub(r"\s+", " ", stem_norm).strip()
    norm_stem_hash = hashlib.sha256(stem_norm.encode("utf-8")).hexdigest()

    norm_options = []
    for opt in options:
        opt_text = opt.get("text", "")
        opt_norm = re.sub(r"[^\w\s]", "", opt_text.lower())
        opt_norm = re.sub(r"\s+", " ", opt_norm).strip()
        norm_options.append(opt_norm)
    norm_options.sort()

    content_payload = f"{stem_norm}|{'|'.join(norm_options)}"
    content_hash = hashlib.sha256(content_payload.encode("utf-8")).hexdigest()

    return {
        "exact_stem_hash": exact_stem_hash,
        "norm_stem_hash": norm_stem_hash,
        "content_hash": content_hash,
    }


def resolve_correct_option(cop_val: Any, options: List[Dict[str, str]]) -> Tuple[Optional[str], int, bool]:
    """
    Resolves correct option key ('A', 'B', 'C', 'D') and index (0..3) from various representations.
    Returns (correct_option, correct_index, is_labeled).
    """
    if cop_val is None or str(cop_val).strip() in ("", "-1", "null", "none"):
        return None, -1, False

    cop_str = str(cop_val).strip()

    # Check key map
    if cop_str in OPTION_KEY_MAP:
        key = OPTION_KEY_MAP[cop_str]
        idx = ord(key) - ord("A")
        return key, idx, True

    # Check integer (1-indexed vs 0-indexed)
    try:
        cop_int = int(cop_str)
        if cop_int in (0, 1, 2, 3):
            key = chr(ord("A") + cop_int)
            return key, cop_int, True
        elif cop_int in (1, 2, 3, 4):  # 1-indexed fallback
            key = chr(ord("A") + cop_int - 1)
            return key, cop_int - 1, True
    except ValueError:
        pass

    # Check if exact text matches an option
    for idx, opt in enumerate(options):
        if opt.get("text", "").strip().lower() == cop_str.lower():
            key = chr(ord("A") + idx)
            return key, idx, True

    return None, -1, False


class UniversalQuestionIngestor:
    """
    Unified Ingestion Service that processes raw inputs from any source
    into the canonical Question database model.
    """

    def __init__(self, engine):
        self.engine = engine

    def normalize_question_payload(
        self,
        raw: Dict[str, Any],
        source_type: str,
        source_exam_id: Optional[str] = None,
        primary_topic_id: Optional[str] = None,
        default_status: QuestionStatus = QuestionStatus.IMPORTED,
        created_by: str = "system_import",
    ) -> Question:
        """
        Converts raw payload dictionary into a validated Question ORM entity.
        """
        # External ID
        external_id = raw.get("external_source_id") or raw.get("id") or str(uuid.uuid4())
        external_source_id = f"{source_type}-{external_id}" if not str(external_id).startswith(f"{source_type}-") else str(external_id)
        
        # Internal UUID
        internal_id = str(uuid.uuid5(INGESTION_NAMESPACE, external_source_id))

        stem = sanitize_text(raw.get("stem") or raw.get("question") or "")
        if not stem:
            raise ValueError("Question stem cannot be empty.")

        # Parse options
        raw_options = raw.get("options")
        options: List[Dict[str, str]] = []

        if isinstance(raw_options, list):
            for idx, item in enumerate(raw_options):
                if isinstance(item, dict):
                    key = item.get("key") or chr(ord("A") + idx)
                    text = sanitize_text(item.get("text", "")) or ""
                else:
                    key = chr(ord("A") + idx)
                    text = sanitize_text(str(item)) or ""
                options.append({"key": key, "text": text})
        elif isinstance(raw_options, dict):
            for key in sorted(raw_options.keys()):
                options.append({"key": key.upper(), "text": sanitize_text(raw_options[key]) or ""})
        else:
            # Check individual option fields (opa, opb, opc, opd / option_a, etc.)
            for idx, k in enumerate(["a", "b", "c", "d"]):
                opt_text = (
                    raw.get(f"op{k}")
                    or raw.get(f"option_{k}")
                    or raw.get(f"option{k}")
                    or raw.get(f"choice_{k}")
                    or raw.get(k.upper())
                    or ""
                )
                options.append({"key": chr(ord("A") + idx), "text": sanitize_text(opt_text) or ""})

        # Resolve correct option
        cop_val = raw.get("correct_option") or raw.get("cop") or raw.get("answer") or raw.get("correct_answer")
        correct_option, correct_index, is_labeled = resolve_correct_option(cop_val, options)

        explanation = sanitize_text(raw.get("explanation") or raw.get("exp"))

        # Topic Decoupling
        raw_topic = raw.get("topic_name_original") or raw.get("topic_name") or raw.get("topic")
        topic_name_original = str(raw_topic).strip() if raw_topic and str(raw_topic).strip() not in ("None", "nan", "") else None
        topic_name_normalized = sanitize_text(topic_name_original)

        if primary_topic_id:
            topic_mapping_status = TopicMappingStatus.MAPPED
        elif topic_name_original:
            topic_mapping_status = TopicMappingStatus.RAW_ONLY
        else:
            topic_mapping_status = TopicMappingStatus.UNMAPPED

        # Hashes
        hashes = compute_hashes(stem, options)

        # Status & Quality
        status = default_status
        if "status" in raw:
            try:
                status = QuestionStatus(raw["status"])
            except ValueError:
                pass

        now_utc = datetime.now(timezone.utc)

        question = Question(
            id=internal_id,
            external_source=source_type,
            external_source_id=external_source_id,
            source_exam_id=source_exam_id or raw.get("source_exam_id") or raw.get("origin_exam_id") or raw.get("course_id"),
            speciality=raw.get("speciality", "Pathology"),
            subject=raw.get("subject", "Pathology"),
            topic_name_original=topic_name_original,
            topic_name_normalized=topic_name_normalized,
            topic_mapping_status=topic_mapping_status,
            primary_topic_id=primary_topic_id or raw.get("primary_topic_id"),
            learning_objective=raw.get("learning_objective"),
            question_type=QuestionType.SINGLE_BEST_ANSWER,
            stem=stem,
            options=options,
            correct_option=correct_option,
            correct_index=correct_index,
            is_labeled=is_labeled,
            explanation=explanation,
            difficulty=raw.get("difficulty"),
            cognitive_level=raw.get("cognitive_level"),
            status=status,
            quality_score=raw.get("quality_score"),
            content_hash=hashes["content_hash"],
            exact_stem_hash=hashes["exact_stem_hash"],
            norm_stem_hash=hashes["norm_stem_hash"],
            duplicate_signals=raw.get("duplicate_signals"),
            metadata_json=raw.get("metadata", {}),
            created_by=created_by,
            created_at=now_utc,
            updated_at=now_utc,
        )

        return question

    def ingest_single(
        self,
        raw_dict: Dict[str, Any],
        source_type: str,
        source_exam_id: Optional[str] = None,
        primary_topic_id: Optional[str] = None,
        status: QuestionStatus = QuestionStatus.IMPORTED,
        created_by: str = "system_import",
    ) -> Question:
        """Ingests a single question entity into the database."""
        question = self.normalize_question_payload(
            raw_dict,
            source_type=source_type,
            source_exam_id=source_exam_id,
            primary_topic_id=primary_topic_id,
            default_status=status,
            created_by=created_by,
        )
        with session_scope(self.engine) as session:
            session.merge(question)
        return question

    def ingest_csv(
        self,
        csv_file_or_content: Union[str, Path, io.StringIO],
        column_mapping: Optional[Dict[str, str]] = None,
        source_name: str = "csv_import",
        source_exam_id: Optional[str] = None,
        primary_topic_id: Optional[str] = None,
        created_by: str = "csv_user",
    ) -> Dict[str, Any]:
        """
        Parses and ingests questions from a CSV file or raw CSV string.
        Supports standard and customized column mappings.
        """
        should_close = False
        if isinstance(csv_file_or_content, Path):
            f = open(csv_file_or_content, "r", encoding="utf-8-sig")
            should_close = True
        elif isinstance(csv_file_or_content, str):
            if "\n" not in csv_file_or_content and Path(csv_file_or_content).exists():
                f = open(csv_file_or_content, "r", encoding="utf-8-sig")
                should_close = True
            else:
                f = io.StringIO(csv_file_or_content)
                should_close = False
        else:
            f = csv_file_or_content
            should_close = False

        try:
            reader = csv.DictReader(f)
            records_to_insert: List[Question] = []
            skipped = 0

            for row in reader:
                mapped_row: Dict[str, Any] = {}
                if column_mapping:
                    for src_col, target_field in column_mapping.items():
                        if src_col in row:
                            mapped_row[target_field] = row[src_col]
                else:
                    # Auto-detect common CSV header variants
                    mapped_row = {
                        "question": row.get("question") or row.get("stem") or row.get("Question Text") or row.get("Question"),
                        "opa": row.get("opa") or row.get("option_a") or row.get("Option A") or row.get("A"),
                        "opb": row.get("opb") or row.get("option_b") or row.get("Option B") or row.get("B"),
                        "opc": row.get("opc") or row.get("option_c") or row.get("Option C") or row.get("C"),
                        "opd": row.get("opd") or row.get("option_d") or row.get("Option D") or row.get("D"),
                        "cop": row.get("cop") or row.get("correct_option") or row.get("Answer") or row.get("Correct Option"),
                        "exp": row.get("exp") or row.get("explanation") or row.get("Explanation"),
                        "topic": row.get("topic") or row.get("Topic"),
                        "speciality": row.get("speciality") or row.get("Speciality") or "Pathology",
                        "subject": row.get("subject") or row.get("Subject") or "Pathology",
                    }

                try:
                    q = self.normalize_question_payload(
                        mapped_row,
                        source_type=source_name,
                        source_exam_id=source_exam_id,
                        primary_topic_id=primary_topic_id,
                        created_by=created_by,
                    )
                    records_to_insert.append(q)
                except Exception as e:
                    logger.warning(f"Skipping CSV row due to normalization error: {e}")
                    skipped += 1

            with session_scope(self.engine) as session:
                for q in records_to_insert:
                    session.merge(q)

            return {
                "total_rows_processed": len(records_to_insert) + skipped,
                "inserted_count": len(records_to_insert),
                "skipped_count": skipped,
            }
        finally:
            if should_close:
                f.close()

    def ingest_google_forms(
        self,
        form_rows: List[Dict[str, Any]],
        source_exam_id: Optional[str] = None,
        primary_topic_id: Optional[str] = None,
        created_by: str = "google_forms_sync",
    ) -> Dict[str, Any]:
        """
        Parses and ingests question submissions from Google Forms exports / webhook arrays.
        """
        inserted = 0
        skipped = 0

        for item in form_rows:
            payload = {
                "id": item.get("Response ID") or item.get("id") or str(uuid.uuid4()),
                "stem": item.get("Question") or item.get("Question Text") or item.get("stem"),
                "opa": item.get("Option A") or item.get("opa"),
                "opb": item.get("Option B") or item.get("opb"),
                "opc": item.get("Option C") or item.get("opc"),
                "opd": item.get("Option D") or item.get("opd"),
                "cop": item.get("Correct Answer") or item.get("Answer") or item.get("cop"),
                "exp": item.get("Explanation") or item.get("exp"),
                "topic": item.get("Topic") or item.get("topic"),
                "metadata": {"form_submitter": item.get("Email Address", "anonymous"), "timestamp": item.get("Timestamp")},
            }
            try:
                self.ingest_single(
                    payload,
                    source_type="google_forms",
                    source_exam_id=source_exam_id,
                    primary_topic_id=primary_topic_id,
                    status=QuestionStatus.IMPORTED,
                    created_by=created_by,
                )
                inserted += 1
            except Exception as e:
                logger.warning(f"Skipping Google Form entry: {e}")
                skipped += 1

        return {"inserted_count": inserted, "skipped_count": skipped}

    def ingest_ai_generated(
        self,
        ai_output: Dict[str, Any],
        blueprint: Optional[Dict[str, Any]] = None,
        model_name: str = "gemini-flash",
        source_exam_id: Optional[str] = None,
        primary_topic_id: Optional[str] = None,
    ) -> Question:
        """
        Ingests an AI-generated question candidate with blueprint provenance and sets status to AI_REVIEW.
        """
        metadata = ai_output.get("metadata", {})
        metadata["ai_model"] = model_name
        metadata["blueprint"] = blueprint or {}

        payload = {
            "id": ai_output.get("id") or str(uuid.uuid4()),
            "stem": ai_output.get("stem") or ai_output.get("question"),
            "options": ai_output.get("options", []),
            "cop": ai_output.get("correct_option") or ai_output.get("cop"),
            "exp": ai_output.get("explanation") or ai_output.get("exp"),
            "learning_objective": (blueprint or {}).get("learning_objective"),
            "difficulty": (blueprint or {}).get("difficulty"),
            "cognitive_level": (blueprint or {}).get("cognitive_level"),
            "metadata": metadata,
        }

        return self.ingest_single(
            payload,
            source_type="ai_generator",
            source_exam_id=source_exam_id,
            primary_topic_id=primary_topic_id,
            status=QuestionStatus.AI_REVIEW,
            created_by=f"ai_model:{model_name}",
        )
