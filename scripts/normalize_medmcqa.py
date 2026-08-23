"""
scripts/normalize_medmcqa.py

Normalizes raw MedMCQA questions into the application's domain Question model.
Preserves all source metadata, provides explicit topic decoupling (topic_name_original,
topic_name_normalized, topic_mapping_status), and computes reproducible content hashes.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Deterministic namespace for MedMCQA question UUIDs
MEDMCQA_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

OPTION_KEY_MAP = {
    0: "A",
    1: "B",
    2: "C",
    3: "D",
}


def sanitize_text(text: Optional[str]) -> Optional[str]:
    """Sanitizes text by stripping whitespace and normalizing unicode while preserving medical symbols."""
    if text is None:
        return None
    text = str(text)
    # NFKC normalizes compatibility characters while preserving greek letters, arrows, etc.
    text = unicodedata.normalize("NFKC", text)
    # Replace non-breaking spaces and other odd spaces with normal space
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    # Normalize multiple whitespace characters inside single lines while keeping paragraphs
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    # Join non-empty lines with single newline, or preserve double newlines
    cleaned = "\n".join(line for line in lines if line)
    return cleaned if cleaned else None


def normalize_topic(topic: Optional[str]) -> Optional[str]:
    """Normalizes raw topic string for consistent categorization."""
    if topic is None:
        return None
    topic = str(topic).strip()
    if not topic or topic.lower() in ("none", "null", "nan", ""):
        return None
    # Normalize unicode
    topic = unicodedata.normalize("NFKC", topic).strip()
    # Normalize common abbreviations and whitespace
    topic = re.sub(r"\s+", " ", topic)
    return topic


def compute_content_hashes(stem: str, options: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Computes cryptographic SHA-256 hashes for exact and normalized duplicate detection.
    """
    # Exact stem hash
    exact_stem_hash = hashlib.sha256(stem.encode("utf-8")).hexdigest()

    # Normalized stem (lowercased, punctuation removed, whitespace collapsed)
    stem_norm = re.sub(r"[^\w\s]", "", stem.lower())
    stem_norm = re.sub(r"\s+", " ", stem_norm).strip()
    norm_stem_hash = hashlib.sha256(stem_norm.encode("utf-8")).hexdigest()

    # Normalized options (order-invariant)
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


def normalize_question_record(raw: Dict[str, Any], split: Optional[str] = None) -> Dict[str, Any]:
    """
    Normalizes a single MedMCQA dictionary record into the target Question schema.
    """
    original_id = str(raw.get("id", "")).strip()
    if not original_id:
        raise ValueError("Missing required 'id' in raw record.")

    external_source = "medmcqa"
    external_source_id = f"medmcqa-{original_id}"
    internal_id = str(uuid.uuid5(MEDMCQA_NAMESPACE, external_source_id))

    raw_question = raw.get("question", "")
    stem = sanitize_text(raw_question) or ""

    raw_opa = raw.get("opa", "")
    raw_opb = raw.get("opb", "")
    raw_opc = raw.get("opc", "")
    raw_opd = raw.get("opd", "")

    options = [
        {"key": "A", "text": sanitize_text(raw_opa) or ""},
        {"key": "B", "text": sanitize_text(raw_opb) or ""},
        {"key": "C", "text": sanitize_text(raw_opc) or ""},
        {"key": "D", "text": sanitize_text(raw_opd) or ""},
    ]

    # Map Correct Option
    cop_val = raw.get("cop")
    if cop_val is not None:
        try:
            cop_int = int(cop_val)
        except (ValueError, TypeError):
            cop_int = -1
    else:
        cop_int = -1

    if cop_int in OPTION_KEY_MAP:
        correct_index = cop_int
        correct_option = OPTION_KEY_MAP[cop_int]
        is_labeled = True
    else:
        correct_index = -1
        correct_option = None
        is_labeled = False

    raw_exp = raw.get("exp")
    explanation = sanitize_text(raw_exp)

    # Topic Handling & Curriculum Decoupling
    raw_topic = raw.get("topic_name")
    topic_name_original = str(raw_topic).strip() if raw_topic is not None and str(raw_topic).strip() not in ("None", "nan", "") else None
    topic_name_normalized = normalize_topic(topic_name_original)

    if topic_name_original is None:
        topic_mapping_status = "UNMAPPED"
    else:
        topic_mapping_status = "RAW_ONLY"  # Present in source metadata, pending mapping to standard curriculum

    # Choice type
    raw_choice_type = str(raw.get("choice_type", "single")).strip().lower()
    question_type = "single_best_answer"

    # Compute hashes
    hashes = compute_content_hashes(stem, options)

    # Split info
    record_split = split or raw.get("split", "unknown")

    now_iso = datetime.now(timezone.utc).isoformat()

    normalized_record: Dict[str, Any] = {
        "id": internal_id,
        "external_source": external_source,
        "external_source_id": external_source_id,
        "speciality": "Pathology",
        "subject": "Pathology",
        # Decoupled Topic System
        "topic_name_original": topic_name_original,
        "topic_name_normalized": topic_name_normalized,
        "topic_mapping_status": topic_mapping_status,
        "curriculum_topic_id": None,
        "learning_objective": None,
        # Content
        "question_type": question_type,
        "stem": stem,
        "options": options,
        "correct_option": correct_option,
        "correct_index": correct_index,
        "is_labeled": is_labeled,
        "explanation": explanation,
        # Difficulty & Quality
        "difficulty": None,
        "cognitive_level": None,
        "status": "IMPORTED",
        "quality_score": None,
        # Hashes for similarity/duplicate tracking
        "content_hash": hashes["content_hash"],
        "exact_stem_hash": hashes["exact_stem_hash"],
        "norm_stem_hash": hashes["norm_stem_hash"],
        # Audit & Metadata
        "created_by": "system_import",
        "created_at": now_iso,
        "updated_at": now_iso,
        "metadata": {
            "original_id": original_id,
            "original_cop": cop_int,
            "original_choice_type": raw_choice_type,
            "split": record_split,
            "has_explanation": explanation is not None,
            "raw_subject": raw.get("subject_name", "Pathology"),
            "raw_topic": topic_name_original,
        },
    }

    return normalized_record
