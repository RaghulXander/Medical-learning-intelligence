"""
scripts/import_daily_quiz_form.py

Ingestion and normalization tool for Daily Pathology Quizzes & Google Forms (HTML, TXT, MD, JSON).
Extracts question stems, options, correct answers, explanations, and maps them to the
Surgical Pathology Ontology & Database Question Model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add repository root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_engine, session_scope
from database.models import (
    CognitiveLevel,
    DifficultyLevel,
    EducationalLevel,
    Question,
    QuestionStatus,
    QuestionType,
    TopicMappingStatus,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TOPIC_ONTOLOGY_MAPPINGS = {
    "urothelial": "TOPIC-RENAL-PATH",
    "urinary": "TOPIC-RENAL-PATH",
    "bladder": "TOPIC-RENAL-PATH",
    "kidney": "TOPIC-RENAL-PATH",
    "renal": "TOPIC-RENAL-PATH",
    "papilloma": "TOPIC-RENAL-PATH",
    "punlmp": "TOPIC-RENAL-PATH",
    "prostate": "TOPIC-MALE-GENITAL",
    "breast": "TOPIC-BREAST-PATH",
    "lung": "TOPIC-THORACIC-PATH",
    "gastric": "TOPIC-GI-PATH",
    "colon": "TOPIC-GI-PATH",
}


def compute_hashes(stem: str, options: List[Dict[str, Any]]) -> Tuple[str, str, str]:
    """Generates exact, normalized, and full content hashes for deduplication."""
    clean_stem = stem.strip()
    norm_stem = re.sub(r"[^a-zA-Z0-9]", "", clean_stem).lower()
    exact_stem_hash = hashlib.sha256(clean_stem.encode("utf-8")).hexdigest()
    norm_stem_hash = hashlib.sha256(norm_stem.encode("utf-8")).hexdigest()

    opts_str = "|".join([opt.get("text", "").strip() for opt in options])
    full_content = f"{clean_stem}::{opts_str}"
    content_hash = hashlib.sha256(full_content.encode("utf-8")).hexdigest()

    return content_hash, exact_stem_hash, norm_stem_hash


def extract_from_google_form_html(html_content: str, day_label: str = "", topic_title: str = "") -> List[Dict[str, Any]]:
    """
    Extracts questions and options from Google Forms HTML (via FB_PUBLIC_LOAD_DATA_).
    """
    questions: List[Dict[str, Any]] = []

    match = re.search(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.+?\]);\s*</script>', html_content, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            form_title = data[1][8] if len(data[1]) > 8 and data[1][8] else (topic_title or "Pathology Quiz")
            items = data[1][1] or []
            
            q_idx = 1
            for item in items:
                if not item or len(item) < 5 or not item[4]:
                    continue
                
                stem = (item[1] or "").strip()
                if not stem:
                    continue
                
                sub_items = item[4][0]
                if len(sub_items) > 1 and sub_items[1]:
                    raw_options = sub_items[1]
                    formatted_options = []
                    for opt_idx, opt in enumerate(raw_options):
                        opt_text = opt[0] if isinstance(opt, list) and len(opt) > 0 else str(opt)
                        formatted_options.append({
                            "key": chr(65 + opt_idx),
                            "text": str(opt_text).strip()
                        })
                    
                    if formatted_options:
                        questions.append({
                            "question_number": q_idx,
                            "stem": stem,
                            "options": formatted_options,
                            "correct_option": None,
                            "correct_index": -1,
                            "explanation": (item[2] or "").strip() if len(item) > 2 else None,
                            "form_title": form_title,
                        })
                        q_idx += 1
            return questions
        except Exception as e:
            logger.warning(f"Failed to parse FB_PUBLIC_LOAD_DATA_: {e}")

    return extract_from_raw_text(html_content, day_label=day_label, topic_title=topic_title)


def extract_from_raw_text(text: str, day_label: str = "", topic_title: str = "") -> List[Dict[str, Any]]:
    """
    Extracts MCQs from unstructured or structured text/markdown.
    Handles various formats:
    - 1. Question stem...
      A. Option A
      B. Option B
      C. Option C
      D. Option D
      Answer: A / Correct: Option A
      Explanation: ...
    """
    questions: List[Dict[str, Any]] = []
    
    norm_text = "\n" + text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r'\n\s*(?=(?:Q(?:uestion)?\s*\d+[\.:\)]|\d+[\.:\)]\s+))', norm_text, flags=re.IGNORECASE)
    
    q_num = 1
    for block in blocks:
        block = block.strip()
        if not block:
            continue
            
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue
            
        stem_lines = []
        options: List[Dict[str, Any]] = []
        correct_option = None
        exp_lines = []
        
        opt_pattern = re.compile(r'^[\[\(]?([A-Ea-e])[\.\)\:\-\]]\s*(.+)$')
        ans_pattern = re.compile(r'^(?:(?:Correct\s*)?Answer|Ans|Key)\s*[:\-]\s*([A-Ea-e]|\b.+\b)', re.IGNORECASE)
        exp_pattern = re.compile(r'^(?:Explanation|Exp|Rationale|Discussion|Notes?|Ref|Reference)\s*[:\-]\s*(.+)$', re.IGNORECASE | re.DOTALL)
        
        reading_explanation = False
        
        for line in lines:
            ans_match = ans_pattern.match(line)
            if ans_match:
                ans_val = ans_match.group(1).strip().upper()
                if len(ans_val) == 1 and ans_val in "ABCDE":
                    correct_option = ans_val
                else:
                    for opt in options:
                        if opt["text"].lower() == ans_val.lower():
                            correct_option = opt["key"]
                reading_explanation = False
                continue
                
            exp_match = exp_pattern.match(line)
            if exp_match:
                reading_explanation = True
                exp_lines.append(exp_match.group(1).strip())
                continue
                
            if reading_explanation:
                exp_lines.append(line)
                continue
                
            opt_match = opt_pattern.match(line)
            if opt_match:
                key = opt_match.group(1).upper()
                options.append({"key": key, "text": opt_match.group(2).strip()})
            else:
                if not options:
                    cleaned = re.sub(r'^(?:Q(?:uestion)?\s*\d+[\.:\)]|\d+[\.:\)]\s*)', '', line)
                    stem_lines.append(cleaned)
                
        stem = " ".join(stem_lines).strip()
        explanation = "\n".join(exp_lines).strip() if exp_lines else None
            
        if stem and len(options) >= 2:
            correct_idx = -1
            if correct_option:
                for idx, opt in enumerate(options):
                    if opt["key"] == correct_option:
                        correct_idx = idx
                        break
                        
            questions.append({
                "question_number": q_num,
                "stem": stem,
                "options": options,
                "correct_option": correct_option,
                "correct_index": correct_idx,
                "explanation": explanation,
                "form_title": topic_title or day_label,
            })
            q_num += 1
            
    return questions


def build_question_record(
    raw_q: Dict[str, Any],
    day_id: str,
    topic_title: str,
    origin_url: str = "",
) -> Question:
    """Converts extracted raw question dictionary into database Question model."""
    stem = raw_q["stem"]
    options = raw_q["options"]
    correct_opt = raw_q.get("correct_option")
    correct_idx = raw_q.get("correct_index", -1)
    explanation = raw_q.get("explanation")
    
    content_hash, exact_stem_hash, norm_stem_hash = compute_hashes(stem, options)
    
    q_num = raw_q.get("question_number", 1)
    ext_id = f"daily_quiz_{day_id.lower().replace(' ', '_')}_q{q_num}"
    
    primary_topic_id = None
    title_lower = (topic_title + " " + stem).lower()
    for key, topic_id in TOPIC_ONTOLOGY_MAPPINGS.items():
        if key in title_lower:
            primary_topic_id = topic_id
            break
            
    tags = [
        "DAILY_PATHOLOGY_QUIZ",
        day_id.upper().replace(" ", "_"),
        "ONCOPATHOLOGY",
        "UROPATHOLOGY" if "urothelial" in title_lower or "urinary" in title_lower else "GENERAL_PATHOLOGY",
    ]
    
    return Question(
        id=str(uuid.uuid4()),
        external_source="daily_pathology_quiz",
        external_source_id=ext_id,
        source_exam_id=day_id,
        speciality="Pathology",
        subject="Pathology",
        topic_name_original=topic_title,
        topic_name_normalized="Renal & Urinary Pathology" if "urothelial" in title_lower or "urinary" in title_lower else topic_title,
        topic_mapping_status=TopicMappingStatus.MAPPED if primary_topic_id else TopicMappingStatus.RAW_ONLY,
        primary_topic_id=primary_topic_id,
        learning_objective=topic_title,
        question_type=QuestionType.SINGLE_BEST_ANSWER,
        stem=stem,
        options=options,
        correct_option=correct_opt,
        correct_index=correct_idx,
        is_labeled=bool(correct_opt is not None),
        explanation=explanation,
        difficulty=DifficultyLevel.MEDIUM,
        cognitive_level=CognitiveLevel.APPLICATION,
        educational_level=EducationalLevel.SUPER_SPECIALTY,
        target_exam_levels=["NEET_SS", "DM_ONCOPATHOLOGY", "MD_PATHOLOGY"],
        status=QuestionStatus.APPROVED if correct_opt else QuestionStatus.IMPORTED,
        origin_cohort="DAILY_PATHOLOGY_QUIZ",
        tags=tags,
        has_images=False,
        image_assets=[],
        content_hash=content_hash,
        exact_stem_hash=exact_stem_hash,
        norm_stem_hash=norm_stem_hash,
        metadata_json={
            "day": day_id,
            "topic": topic_title,
            "origin_url": origin_url,
            "imported_at": datetime.now(timezone.utc).isoformat(),
        },
        created_by="daily_quiz_importer",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def import_form_file(
    file_path: Path,
    day_id: str,
    topic_title: str,
    origin_url: str = "",
    engine=None,
) -> int:
    """Imports questions from a local file (HTML, TXT, JSON, MD) into DB."""
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return 0
        
    content = file_path.read_text(encoding="utf-8")
    
    if file_path.suffix.lower() in [".html", ".htm"]:
        raw_questions = extract_from_google_form_html(content, day_label=day_id, topic_title=topic_title)
    elif file_path.suffix.lower() == ".json":
        data = json.loads(content)
        raw_questions = data if isinstance(data, list) else data.get("questions", [])
    else:
        raw_questions = extract_from_raw_text(content, day_label=day_id, topic_title=topic_title)
        
    logger.info(f"Extracted {len(raw_questions)} questions from {file_path.name}")
    if not raw_questions:
        return 0
        
    if engine is None:
        engine = get_engine()
        
    inserted = 0
    with session_scope(engine) as session:
        for raw_q in raw_questions:
            q_record = build_question_record(raw_q, day_id, topic_title, origin_url)
            
            existing = session.query(Question).filter(
                (Question.external_source_id == q_record.external_source_id) |
                (Question.content_hash == q_record.content_hash)
            ).first()
            
            if existing:
                logger.info(f"Skipping existing question: {q_record.external_source_id}")
                continue
                
            session.add(q_record)
            inserted += 1
            
    logger.info(f"Successfully inserted {inserted} new questions into database.")
    return inserted


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Daily Pathology Quiz / Google Form questions.")
    parser.add_argument("--file", type=Path, help="Path to raw file (HTML, TXT, JSON, MD)")
    parser.add_argument("--day", type=str, default="Day 077", help="Day label (e.g. Day 077)")
    parser.add_argument("--topic", type=str, default="", help="Topic title")
    parser.add_argument("--url", type=str, default="", help="Origin Google Form URL")
    
    args = parser.parse_args()
    if args.file:
        import_form_file(args.file, args.day, args.topic, args.url)
    else:
        logger.info("Ready to import. Provide --file argument.")
