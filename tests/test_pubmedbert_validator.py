"""
tests/test_pubmedbert_validator.py

Unit & Integration Tests for PubMedBERT MCQA Validation Service and Client.
"""

import pytest
from fastapi.testclient import TestClient

from ml.pubmedbert_validator.service import app as pubmedbert_app
from backend.services.evaluation.pubmedbert_client import PubMedBERTClient
from backend.services.generation.models import GeneratedMCQPayload, GeneratedOption
from backend.services.generation.evaluator import QuestionEvaluator


def test_pubmedbert_service_endpoints():
    client = TestClient(pubmedbert_app)

    # Health check
    h_resp = client.get("/health")
    assert h_resp.status_code == 200
    assert h_resp.json()["status"] == "healthy"

    # Prediction endpoint
    payload = {
        "question": "Which marker is characteristically positive in classical Hodgkin lymphoma Reed-Sternberg cells?",
        "options": ["CD20", "CD30 and CD15", "CD3", "CD68"],
    }
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["prediction"] in ["A", "B", "C", "D"]
    assert "probabilities" in data
    assert len(data["probabilities"]) == 4
    assert pytest.approx(sum(data["probabilities"].values()), 0.01) == 1.0
    assert data["confidence"] > 0.0
    assert data["entropy"] >= 0.0


def test_pubmedbert_client_prediction():
    client = PubMedBERTClient(force_local=True)
    pred = client.predict(
        stem="What is the diagnostic scoring threshold for HER2 3+ positivity?",
        options=["0%", "1-10% incomplete", ">10% strong circumferential", "Negative"],
        ground_truth="C",
    )
    assert pred.predicted_option == "C"
    assert pred.agrees_with_ground_truth is True
    assert pred.confidence > 0.0
    assert pred.margin >= 0.0


def test_pubmedbert_evaluator_integration():
    evaluator = QuestionEvaluator()
    mcq = GeneratedMCQPayload(
        stem="A 35-year-old female presents with painless cervical lymphadenopathy. RS cells are found.",
        options=[
            GeneratedOption(key="A", text="CD20 only", is_correct=False, rationale="Negative"),
            GeneratedOption(key="B", text="CD30 and CD15 positive", is_correct=True, rationale="Positive"),
            GeneratedOption(key="C", text="CD3 positive", is_correct=False, rationale="T cell marker"),
            GeneratedOption(key="D", text="CD138 positive", is_correct=False, rationale="Plasma cell marker"),
        ],
        correct_option="B",
        explanation="Option B is correct. Reed-Sternberg cells express CD30 and CD15.",
        learning_objective="Hodgkin lymphoma immunophenotype",
        difficulty="MEDIUM",
        cognitive_level="APPLICATION",
        question_type="SINGLE_BEST_ANSWER",
        evidence_chunk_ids=["chunk-1"],
        citations=["Robbins 11th Ed., p. 582"],
    )

    res = evaluator.evaluate_mcq(mcq)
    assert res.passed is True
    # Verify PubMedBERT validation check is present
    pmb_checks = [c for c in res.checks if c.name == "PubMedBERT Validation"]
    assert len(pmb_checks) == 1
    assert pmb_checks[0].passed is True
    assert "PubMedBERT Model" in pmb_checks[0].details
