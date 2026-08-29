"""Preview or apply deterministic grouping of legacy Pathology question topics."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.domain.pathology_ontology import map_legacy_topic
from database.db import get_engine, session_scope
from database.models import CurriculumLevel, CurriculumTopic, Question, TopicMappingStatus
from backend.domain.pathology_ontology import PATHOLOGY_TOPICS


def seed_pathology_ontology(engine) -> None:
    """Upsert only ontology nodes; do not create users, sources, or sample content."""
    roots = (
        ("SPEC-PATH", "Pathology", CurriculumLevel.SPECIALITY, None),
        ("SUBJ-GEN-PATH", "General Pathology", CurriculumLevel.SUBJECT, "SPEC-PATH"),
        ("SUBJ-HEM-PATH", "Hematopathology", CurriculumLevel.SUBJECT, "SPEC-PATH"),
        ("SUBJ-SYS-PATH", "Systemic & Surgical Pathology", CurriculumLevel.SUBJECT, "SPEC-PATH"),
        ("SUBJ-MOL-PATH", "Molecular & Diagnostic IHC", CurriculumLevel.SUBJECT, "SPEC-PATH"),
    )
    with session_scope(engine) as session:
        nodes = {node.code: node for node in session.query(CurriculumTopic).all()}
        for code, name, level, parent_code in roots:
            if code not in nodes:
                node = CurriculumTopic(
                    code=code,
                    name=name,
                    level=level,
                    parent_id=nodes[parent_code].id if parent_code else None,
                    metadata_json={"ontology_version": "pathology-v1"},
                )
                session.add(node)
                session.flush()
                nodes[code] = node
        for definition in PATHOLOGY_TOPICS:
            if definition.code not in nodes:
                node = CurriculumTopic(
                    code=definition.code,
                    name=definition.name,
                    level=CurriculumLevel.TOPIC,
                    parent_id=nodes[definition.parent_code].id,
                    metadata_json={"ontology_version": "pathology-v1", "aliases": list(definition.aliases)},
                )
                session.add(node)
                session.flush()
                nodes[definition.code] = node


def group_questions(*, database_url: str | None = None, apply: bool = False) -> dict:
    engine = get_engine(database_url)
    if apply:
        seed_pathology_ontology(engine)
    summary = Counter()
    unmatched_topics = Counter()
    examples: dict[str, list[dict]] = {"unmapped": [], "mapped": []}

    with session_scope(engine) as session:
        topics = {topic.code: topic for topic in session.query(CurriculumTopic).all()}
        questions = session.query(Question).filter(Question.speciality.ilike("%pathology%")).all()
        summary["total"] = len(questions)
        for question in questions:
            match = map_legacy_topic((question.topic_name_original, question.topic_name_normalized))
            if not match or (apply and match.code not in topics):
                summary["unmapped"] += 1
                if question.topic_name_original or question.topic_name_normalized:
                    summary["unmatched_topic"] += 1
                    unmatched_topics[question.topic_name_original or question.topic_name_normalized] += 1
                else:
                    summary["missing_topic"] += 1
                if len(examples["unmapped"]) < 20:
                    examples["unmapped"].append({"question_id": question.id, "topic": question.topic_name_original})
                continue

            summary[f"group:{match.code}"] += 1
            summary["mapped"] += 1
            if len(examples["mapped"]) < 20:
                examples["mapped"].append({
                    "question_id": question.id,
                    "from": question.topic_name_original,
                    "to": match.code,
                    "confidence": match.confidence,
                })
            if apply:
                question.primary_topic_id = topics[match.code].id
                question.topic_mapping_status = TopicMappingStatus.MAPPED
                metadata = dict(question.metadata_json or {})
                metadata["ontology_mapping"] = {
                    "method": "deterministic_alias_v1",
                    "topic_code": match.code,
                    "confidence": match.confidence,
                    "matched_aliases": list(match.matched_aliases),
                }
                question.metadata_json = metadata

        if not apply:
            session.rollback()

    return {
        "mode": "apply" if apply else "dry-run",
        "counts": dict(summary),
        "top_unmatched_topics": [
            {"topic": topic, "count": count} for topic, count in unmatched_topics.most_common(50)
        ],
        "examples": examples,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url")
    parser.add_argument("--apply", action="store_true", help="Persist mappings; default is a safe dry run")
    parser.add_argument("--report", type=Path, help="Optional JSON report path")
    args = parser.parse_args()
    report = group_questions(database_url=args.database_url, apply=args.apply)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
