"""
scripts/generate_pathology_mcqs.py

CLI Utility for Generating Authoritative Pathology MCQs Grounded in Robbins Evidence.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

from database.db import init_db, session_scope
from backend.services.generation.models import QuestionBlueprint
from backend.services.generation.service import QuestionGenerationService
from backend.services.generation.generator import get_mcq_generator


def main():
    parser = argparse.ArgumentParser(
        description="Generate evidence-grounded pathology MCQs from Robbins corpus."
    )
    parser.add_argument("--topic", type=str, required=True, help="Topic name (e.g. 'Breast Carcinoma')")
    parser.add_argument("--objective", type=str, default="Diagnostic criteria and molecular hallmarks", help="Learning objective")
    parser.add_argument("--subtopic", type=str, default=None, help="Optional subtopic or chapter keyword")
    parser.add_argument("--difficulty", type=str, default="MEDIUM", choices=["EASY", "MEDIUM", "HARD"])
    parser.add_argument("--cognitive-level", type=str, default="APPLICATION", choices=["RECALL", "UNDERSTANDING", "APPLICATION", "ANALYSIS"])
    parser.add_argument("--target-exam", type=str, default="NEET_PG", choices=["NEET_PG", "NEET_SS", "INICET", "MD_PATHOLOGY"])
    parser.add_argument("--count", type=int, default=1, help="Number of questions to generate")
    parser.add_argument("--mock", action="store_true", help="Force mock generator (no Gemini API required)")
    parser.add_argument("--no-persist", action="store_true", help="Dry run without saving to database")

    args = parser.parse_args()

    init_db()
    generator = get_mcq_generator(force_mock=args.mock)
    service = QuestionGenerationService()

    blueprint = QuestionBlueprint(
        topic=args.topic,
        learning_objective=args.objective,
        subtopic=args.subtopic,
        difficulty=args.difficulty,
        cognitive_level=args.cognitive_level,
        target_exam=args.target_exam,
    )

    logger.info(f"🎯 Generating {args.count} MCQ(s) for Topic: '{args.topic}' (Objective: '{args.objective}')")

    with session_scope() as session:
        for i in range(args.count):
            logger.info(f"\n--- Generating Question #{i+1} ---")
            question, eval_result, mcq = service.generate_question_from_blueprint(
                db=session,
                blueprint=blueprint,
                generator=generator,
                persist=not args.no_persist,
            )

            print("\n" + "=" * 70)
            print(f"STEM: {question.stem}")
            print("-" * 70)
            for opt in question.options:
                marker = "[CORRECT]" if opt["id"] == question.correct_option else "         "
                print(f"  {marker} ({opt['id']}) {opt['text']}")
            print("-" * 70)
            print(f"CORRECT ANSWER: Option {question.correct_option}")
            print(f"EXPLANATION: {question.explanation}")
            print("-" * 70)
            print(f"EVALUATION: Passed={eval_result.passed} | Status={question.status.value} | Quality Score={eval_result.overall_score}")
            print(f"EVIDENCE LINKS: {len(question.evidence_links)} Robbins block(s) attached")
            for ev in question.evidence_links:
                print(f"  - Chapter: {ev.chapter} | Page: {ev.page_range} | Status: {ev.verification_status.value}")
            print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
