"""
backend/services/embedding_service.py

Modular Vector Embedding Service for Pathology Evidence Retrieval.
Provides unified embedding generation with support for:
1. Google Gemini embeddings (768-dim dense semantic embeddings)
2. Deterministic unit-normalized mock embeddings for testing and offline environments.

Configured remote providers fail closed: an SDK or API failure is never replaced
with a mock vector that could be mistaken for production evidence.
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import time
from abc import ABC, abstractmethod
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"
DEFAULT_EMBEDDING_DIM = 768


class EmbeddingProviderError(RuntimeError):
    """Raised when a configured embedding provider cannot return valid vectors."""


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class EmbeddingProvider(ABC):
    """Abstract interface for vector embedding generation."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Returns the canonical model name."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Returns the embedding vector dimension."""
        pass

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generates embedding vector for a single text."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for a batch of texts."""
        pass


class DeterministicMockEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic hash-based embedding provider.
    Produces unit-normalized 768-dimensional vectors from text hashes for testing.
    Semantically similar or identical words produce higher overlap.
    """

    def __init__(self, dimension: int = DEFAULT_EMBEDDING_DIM):
        self._dim = dimension
        self._model_name = "mock-deterministic-embedding-768"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dim

    def _generate_vector(self, text: str) -> List[float]:
        """Generates a stable 768-dim pseudo-semantic vector from text tokens."""
        vec = np.zeros(self._dim, dtype=np.float32)
        words = text.lower().split()
        if not words:
            vec[0] = 1.0
            return vec.tolist()

        for idx, word in enumerate(words):
            # Seed each word into dimensions
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
            for d in range(8):
                dim_idx = (h + d * 97) % self._dim
                weight = 1.0 / math.sqrt(idx + 1)
                sign = 1.0 if ((h >> d) & 1) else -1.0
                vec[dim_idx] += sign * weight

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        else:
            vec[0] = 1.0
        return vec.tolist()

    def embed_text(self, text: str) -> List[float]:
        return self._generate_vector(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self._generate_vector(t) for t in texts]


class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Google Gemini Embedding Provider (`text-embedding-004`).
    Integrates with Google GenAI API with retry and batching.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        dimension: int = DEFAULT_EMBEDDING_DIM,
        task_type: str = "RETRIEVAL_DOCUMENT",
        vertex_ai: bool = False,
        project: Optional[str] = None,
        location: Optional[str] = None,
    ):
        self._api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self._model_name = model_name
        self._dim = dimension
        self._task_type = task_type
        self._vertex_ai = vertex_ai
        self._project = project or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
        self._location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        self._client = None
        self._init_client()

    def _init_client(self):
        try:
            from google import genai
            if self._vertex_ai:
                if not self._project:
                    raise ValueError("A GCP project is required for Vertex AI embeddings")
                self._client = genai.Client(
                    vertexai=True,
                    project=self._project,
                    location=self._location,
                )
            elif self._api_key:
                self._client = genai.Client(api_key=self._api_key)
            else:
                raise ValueError("An API key is required outside Vertex AI mode")
        except Exception as exc:
            raise EmbeddingProviderError("Google GenAI embedding client initialization failed") from exc

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def task_type(self) -> str:
        return self._task_type

    def embed_text(self, text: str) -> List[float]:
        res = self.embed_batch([text])
        if len(res) != 1:
            raise EmbeddingProviderError("Embedding provider returned no vector for the input text")
        return res[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if not self._client:
            raise EmbeddingProviderError("Google GenAI embedding client is not initialized")

        results: List[List[float]] = []
        batch_size = 50

        from google.genai import types

        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            for attempt in range(3):
                try:
                    response = self._client.models.embed_content(
                        model=self._model_name,
                        contents=chunk,
                        config=types.EmbedContentConfig(
                            task_type=self._task_type,
                            output_dimensionality=self._dim,
                            auto_truncate=False,
                        ),
                    )
                    # Extract embeddings
                    if hasattr(response, "embeddings"):
                        for emb in response.embeddings:
                            results.append(list(emb.values))
                    else:
                        raise ValueError(f"Unexpected embed_content response structure: {response}")
                    break
                except Exception as exc:
                    if attempt == 2:
                        raise EmbeddingProviderError(
                            "Google GenAI embedding request failed after 3 attempts"
                        ) from exc
                    else:
                        time.sleep(1.0 * (attempt + 1))

        if len(results) != len(texts):
            raise EmbeddingProviderError(
                f"Embedding provider returned {len(results)} vectors for {len(texts)} inputs"
            )
        if any(len(vector) != self._dim for vector in results):
            raise EmbeddingProviderError(
                f"Embedding provider returned a vector with dimension other than {self._dim}"
            )

        return results


def get_embedding_provider(
    force_mock: bool = False,
    api_key: Optional[str] = None,
    task_type: str = "RETRIEVAL_QUERY",
) -> EmbeddingProvider:
    """Factory creating the appropriate EmbeddingProvider."""
    if force_mock:
        return DeterministicMockEmbeddingProvider()

    configured_provider = os.getenv("EMBEDDING_PROVIDER", "").strip().lower()
    api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if configured_provider in {"vertex", "vertex_ai", "google_vertex_ai"}:
        return GeminiEmbeddingProvider(vertex_ai=True, task_type=task_type)
    if api_key:
        return GeminiEmbeddingProvider(api_key=api_key, task_type=task_type)
    else:
        # No provider was configured, so this is an explicit offline/test mode,
        # not a recovery path after a production provider failure.
        return DeterministicMockEmbeddingProvider()
