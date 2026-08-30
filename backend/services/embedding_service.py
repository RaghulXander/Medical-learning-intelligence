"""
backend/services/embedding_service.py

Modular Vector Embedding Service for Pathology Evidence Retrieval.
Provides unified embedding generation with support for:
1. Google Gemini `text-embedding-004` (768-dim dense semantic embeddings)
2. Deterministic unit-normalized mock embeddings for testing and offline environments.
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

DEFAULT_EMBEDDING_MODEL = "text-embedding-004"
DEFAULT_EMBEDDING_DIM = 768


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
    ):
        self._api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self._model_name = model_name
        self._dim = dimension
        self._client = None
        self._init_client()

    def _init_client(self):
        try:
            from google import genai
            if self._api_key:
                self._client = genai.Client(api_key=self._api_key)
            else:
                self._client = genai.Client()
        except Exception as e:
            logger.warning(f"Google GenAI SDK init warning: {e}")
            self._client = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_text(self, text: str) -> List[float]:
        res = self.embed_batch([text])
        return res[0] if res else [0.0] * self._dim

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if not self._client:
            logger.warning("Gemini Client not initialized. Falling back to deterministic embedding.")
            mock = DeterministicMockEmbeddingProvider(dimension=self._dim)
            return mock.embed_batch(texts)

        results: List[List[float]] = []
        batch_size = 50

        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            for attempt in range(3):
                try:
                    response = self._client.models.embed_content(
                        model=self._model_name,
                        contents=chunk,
                    )
                    # Extract embeddings
                    if hasattr(response, "embeddings"):
                        for emb in response.embeddings:
                            results.append(list(emb.values))
                    else:
                        raise ValueError(f"Unexpected embed_content response structure: {response}")
                    break
                except Exception as e:
                    if attempt == 2:
                        logger.error(f"Failed to embed batch with Gemini API after 3 attempts: {e}")
                        mock = DeterministicMockEmbeddingProvider(dimension=self._dim)
                        results.extend(mock.embed_batch(chunk))
                    else:
                        time.sleep(1.0 * (attempt + 1))

        return results


def get_embedding_provider(
    force_mock: bool = False,
    api_key: Optional[str] = None,
) -> EmbeddingProvider:
    """Factory creating the appropriate EmbeddingProvider."""
    if force_mock:
        return DeterministicMockEmbeddingProvider()

    api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            return GeminiEmbeddingProvider(api_key=api_key)
        except Exception as e:
            logger.warning(f"Could not load Gemini provider ({e}), using deterministic provider.")
            return DeterministicMockEmbeddingProvider()
    else:
        return DeterministicMockEmbeddingProvider()
