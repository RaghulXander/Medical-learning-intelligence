import json

import pytest

from backend.services.retrieval_evaluation import load_evaluation_set


def test_evaluation_dataset_loader_hashes_and_validates_rows(tmp_path):
    dataset = tmp_path / "eval.jsonl"
    rows = [
        {
            "id": "case-1",
            "domain": "general_pathology",
            "query": "Mechanism question",
            "expected_chunk_ids": ["chunk-1"],
            "out_of_corpus": False,
            "reviewer": "reviewer-1",
            "verification_status": "HUMAN_VERIFIED",
        },
        {
            "id": "case-2",
            "domain": "control",
            "query": "Unsupported question",
            "expected_chunk_ids": [],
            "out_of_corpus": True,
            "reviewer": "reviewer-1",
            "verification_status": "HUMAN_VERIFIED",
        },
    ]
    dataset.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    cases, digest = load_evaluation_set(dataset)

    assert len(cases) == 2
    assert len(digest) == 64
    assert cases[1].out_of_corpus is True


def test_evaluation_dataset_rejects_unlabeled_in_corpus_case(tmp_path):
    dataset = tmp_path / "invalid.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "id": "case-1",
                "domain": "general_pathology",
                "query": "Question",
                "expected_chunk_ids": [],
                "out_of_corpus": False,
                "reviewer": "reviewer-1",
                "verification_status": "HUMAN_VERIFIED",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires at least one expected chunk"):
        load_evaluation_set(dataset)


def test_evaluation_dataset_rejects_automatically_selected_gold_label(tmp_path):
    dataset = tmp_path / "unverified.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "id": "case-1",
                "domain": "general_pathology",
                "query": "Question",
                "expected_chunk_ids": ["auto-selected-chunk"],
                "out_of_corpus": False,
                "reviewer": "automated-bootstrap",
                "verification_status": "AUTO_BOOTSTRAP_UNVERIFIED",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not HUMAN_VERIFIED"):
        load_evaluation_set(dataset)
