"""
scripts/generate_multimodal_mcqs.py

CLI Utility for Generating Vision-Grounded Pathology MCQs
Anchored on Curated Reference Histology and IHC Images.

Usage:
  # Generate a sample multimodal question (dry run):
  python scripts/generate_multimodal_mcqs.py --topic Breast

  # Generate and persist to Neon PostgreSQL database:
  python scripts/generate_multimodal_mcqs.py --topic Hematolymphoid --persist

  # Generate 5 questions across available topics and save to JSONL:
  python scripts/generate_multimodal_mcqs.py --count 5 --output data/processed/multimodal_questions.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("multimodal_generator")

from backend.services.multimodal.generator import MultimodalMCQGenerator
from backend.services.multimodal.image_catalog import get_image_catalog
from backend.services.multimodal.models import MultimodalQuestionBlueprint


def main():
    parser = argparse.ArgumentParser(description="Generate vision-grounded pathology MCQs")
    parser.add_argument("--topic", default="Breast", help="Organ system or topic (Breast, Hematolymphoid, Kidney, etc.)")
    parser.add_argument("--image-id", help="Target image ID from catalog (e.g. img-breast-her2-3plus)")
    parser.add_argument("--objective", default="Histopathological diagnosis and immunohistochemical interpretation", help="Learning objective")
    parser.add_argument("--difficulty", default="MEDIUM", choices=["EASY", "MEDIUM", "HARD"])
    parser.add_argument("--cognitive-level", default="APPLICATION", choices=["RECALL", "UNDERSTANDING", "APPLICATION", "ANALYSIS"])
    parser.add_argument("--target-exam", default="NEET_PG", choices=["NEET_PG", "NEET_SS", "INICET", "MD_PATHOLOGY"])
    parser.add_argument("--count", type=int, default=1, help="Number of questions to generate")
    parser.add_argument("--output", type=Path, help="Save generated questions to JSON/JSONL file")
    parser.add_argument("--persist", action="store_true", help="Persist generated questions to PostgreSQL / Neon database")
    args = parser.parse_args()

    catalog = get_image_catalog()
    generator = MultimodalMCQGenerator()

    blueprint = MultimodalQuestionBlueprint(
        topic=args.topic,
        learning_objective=args.objective,
        difficulty=args.difficulty,
        cognitive_level=args.cognitive_level,
        target_exam=args.target_exam,
        target_image_id=args.image_id,
    )

    generated_questions = []

    for i in range(1, args.count + 1):
        mcq = generator.generate_image_mcq(blueprint=blueprint)
        logger.info(f"\n=======================================================")
        logger.info(f"Generated Question #{i} [{mcq.metadata.get('tags', [])}]:")
        logger.info(f"Stem: {mcq.stem}")
        logger.info(f"Image: {mcq.metadata['image_assets'][0]['title']} ({mcq.metadata['image_assets'][0]['stain_type']})")
        logger.info(f"Options:")
        for opt in mcq.options:
            marker = "[CORRECT]" if opt.is_correct else "         "
            logger.info(f"  {opt.key}. {opt.text} {marker}")
        logger.info(f"Explanation:\n{mcq.explanation}")

        q_dict = {
            "index": i,
            "stem": mcq.stem,
            "options": [{"key": o.key, "text": o.text, "is_correct": o.is_correct, "rationale": o.rationale} for o in mcq.options],
            "correct_option": mcq.correct_option,
            "explanation": mcq.explanation,
            "difficulty": mcq.difficulty,
            "cognitive_level": mcq.cognitive_level,
            "image_assets": mcq.metadata.get("image_assets", []),
            "citations": mcq.citations,
            "tags": mcq.metadata.get("tags", []),
        }
        generated_questions.append(q_dict)

        if args.persist:
            from database.db import get_engine, get_session_factory
            from database.models import (
                ClassificationSource,
                ClassificationStatus,
                CognitiveLevel,
                DifficultyLevel,
                Question,
                QuestionStatus,
                QuestionType,
                TopicMappingStatus,
            )

            engine = get_engine()
            session_factory = get_session_factory(engine)
            with session_factory() as db:
                opt_dicts = [
                    {"id": opt.key, "text": opt.text, "is_correct": opt.is_correct, "rationale": opt.rationale}
                    for opt in mcq.options
                ]
                content_hash = hashlib.sha256(f"{mcq.stem}|{mcq.correct_option}".encode("utf-8")).hexdigest()
                exact_stem_hash = hashlib.sha256(mcq.stem.encode("utf-8")).hexdigest()
                norm_stem_hash = hashlib.sha256(" ".join(mcq.stem.lower().split()).encode("utf-8")).hexdigest()

                question = Question(
                    id=str(uuid.uuid4()),
                    external_source="MULTIMODAL_AI",
                    external_source_id=f"mm-cli-{uuid.uuid4().hex[:12]}",
                    speciality="Pathology",
                    subject="Surgical Pathology",
                    topic_name_original=args.topic,
                    topic_name_normalized=args.topic.lower().strip(),
                    topic_mapping_status=TopicMappingStatus.MAPPED,
                    learning_objective=args.objective,
                    question_type=QuestionType.CASE_BASED,
                    stem=mcq.stem,
                    options=opt_dicts,
                    correct_option=mcq.correct_option,
                    correct_index=0,
                    is_labeled=True,
                    explanation=mcq.explanation,
                    difficulty=DifficultyLevel(args.difficulty.lower()),
                    cognitive_level=CognitiveLevel(args.cognitive_level.lower()),
                    target_exam_levels=[args.target_exam],
                    status=QuestionStatus.GENERATED,
                    quality_score=0.95,
                    classification_source=ClassificationSource.AI_CLASSIFIED,
                    classification_status=ClassificationStatus.PENDING_REVIEW,
                    classification_confidence=0.98,
                    knowledge_era="CURRENT",
                    origin_cohort="MULTIMODAL_IMAGE_MCQ",
                    tags=["MULTIMODAL_IMAGE_MCQ", "HISTOLOGY_VIGNETTE", args.topic.upper()],
                    has_images=True,
                    image_assets=mcq.metadata.get("image_assets", []),
                    content_hash=content_hash,
                    exact_stem_hash=exact_stem_hash,
                    norm_stem_hash=norm_stem_hash,
                    metadata_json={
                        "citations": mcq.citations,
                        "generator": "scripts/generate_multimodal_mcqs.py",
                    },
                    created_by="multimodal_cli",
                )
                db.add(question)
                db.commit()
                logger.info(f"💾 Persisted question to database: ID={question.id}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            if str(args.output).endswith(".jsonl"):
                for q in generated_questions:
                    f.write(json.dumps(q) + "\n")
            else:
                json.dump(generated_questions, f, indent=2)
        logger.info(f"📄 Saved {len(generated_questions)} questions to {args.output}")


if __name__ == "__main__":
    main()
