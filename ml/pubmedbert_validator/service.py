"""
ml/pubmedbert_validator/service.py

PubMedBERT Multiple Choice Question Answering (MCQA) Validation Microservice.
Wraps 'jamezoon/medmcqa-pubmedbert-mcqa' using PyTorch / Transformers.
Provides option probability distribution and prediction signals for question evaluation.
"""

from __future__ import annotations

import logging
import math
import os
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pubmedbert-service")

app = FastAPI(
    title="PubMedBERT MCQA Validation Service",
    description="Medical MCQ answer-validation and probability distribution calibration service.",
    version="1.0.0",
)

MODEL_NAME = os.getenv("PUBMEDBERT_MODEL_NAME", "jamezoon/medmcqa-pubmedbert-mcqa")
FORCE_MOCK = os.getenv("PUBMEDBERT_FORCE_MOCK", "false").lower() == "true"

_tokenizer = None
_model = None
_is_loaded = False


def load_model():
    """Lazily loads Hugging Face model and tokenizer."""
    global _tokenizer, _model, _is_loaded
    if _is_loaded or FORCE_MOCK:
        return

    try:
        import torch
        from transformers import AutoModelForMultipleChoice, AutoTokenizer

        logger.info(f"Loading PubMedBERT MCQA model: '{MODEL_NAME}'...")
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModelForMultipleChoice.from_pretrained(MODEL_NAME)
        _model.eval()
        _is_loaded = True
        logger.info("✅ PubMedBERT model loaded successfully.")
    except Exception as e:
        logger.warning(f"Could not load Hugging Face model weights ({e}). Falling back to deterministic heuristic mode.")
        _is_loaded = False


class PredictRequest(BaseModel):
    question: str = Field(..., min_length=5, description="Question stem text")
    options: List[str] = Field(..., min_items=2, max_items=6, description="List of option texts")


class PredictResponse(BaseModel):
    prediction: str  # "A", "B", "C", "D"
    probabilities: Dict[str, float]
    confidence: float
    entropy: float
    model_name: str


@app.on_event("startup")
def startup_event():
    load_model()


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "model_name": MODEL_NAME,
        "model_loaded": _is_loaded,
        "force_mock": FORCE_MOCK,
    }


@app.post("/predict", response_model=PredictResponse)
def predict_mcq(req: PredictRequest):
    """
    Computes probability distribution across options for a given question stem.
    """
    if len(req.options) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 options are required for MCQA prediction.",
        )

    option_keys = [chr(65 + i) for i in range(len(req.options))]

    if _is_loaded and _tokenizer and _model:
        try:
            import torch
            num_options = len(req.options)
            first_sentences = [req.question] * num_options
            second_sentences = req.options

            inputs = _tokenizer(
                first_sentences,
                second_sentences,
                truncation=True,
                padding=True,
                max_length=512,
                return_tensors="pt",
            )
            # Reshape for MultipleChoice
            inputs = {k: v.unsqueeze(0) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = _model(**inputs)
                logits = outputs.logits[0]
                probs = torch.softmax(logits, dim=-1).tolist()

            pred_idx = int(torch.argmax(logits).item())
            pred_key = option_keys[pred_idx]
            prob_dict = {k: round(p, 4) for k, p in zip(option_keys, probs)}
            confidence = prob_dict[pred_key]

            # Calculate Shannon entropy: - sum(p * log2(p))
            entropy = -sum(p * math.log2(p + 1e-9) for p in probs if p > 0)

            return PredictResponse(
                prediction=pred_key,
                probabilities=prob_dict,
                confidence=round(confidence, 4),
                entropy=round(entropy, 4),
                model_name=MODEL_NAME,
            )
        except Exception as e:
            logger.error(f"Inference error with PubMedBERT weights: {e}. Using deterministic heuristic.")

    # Deterministic Heuristic Fallback (for offline testing & lightweight environments)
    import hashlib
    scores = []
    for opt in req.options:
        h = int(hashlib.sha256(f"{req.question}:{opt}".encode("utf-8")).hexdigest()[:8], 16)
        scores.append(float(h % 1000 + 100))

    total = sum(scores)
    probs = [s / total for s in scores]
    max_idx = probs.index(max(probs))
    pred_key = option_keys[max_idx]
    prob_dict = {k: round(p, 4) for k, p in zip(option_keys, probs)}
    entropy = -sum(p * math.log2(p + 1e-9) for p in probs if p > 0)

    return PredictResponse(
        prediction=pred_key,
        probabilities=prob_dict,
        confidence=round(prob_dict[pred_key], 4),
        entropy=round(entropy, 4),
        model_name="mock-pubmedbert-heuristic",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
