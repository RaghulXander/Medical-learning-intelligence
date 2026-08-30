"""
scripts/generate_evidence_embeddings.py

Batch Vector Embedding Generation CLI for Pathology Reference Evidence.
Embeds all DocumentChunk records in the database using Gemini text-embedding-004
or deterministic mock embeddings and persists the vector representations.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

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
from database.models import DocumentChunk
from backend.services.embedding_service import get_embedding_provider


def generate_embeddings_for_chunks(
    batch_size: int = 50,
    force_all: bool = False,
    force_mock: bool = False,
    doc_filter: Optional[str] = None,
) -> int:
    """Batch-generates embeddings for un-embedded document chunks."""
    init_db()
    provider = get_embedding_provider(force_mock=force_mock)
    logger.info(f"🧠 Using Embedding Provider: {provider.model_name} (Dimension: {provider.dimension})")

    embedded_count = 0

    with session_scope() as session:
        query = session.query(DocumentChunk)
        if not force_all:
            query = query.filter(DocumentChunk.embedding.is_(None))

        chunks = query.all()
        total_chunks = len(chunks)

        logger.info(f"⚡ Found {total_chunks} chunks to embed.")

        for i in range(0, total_chunks, batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c.content[:3000] for c in batch]
            embeddings = provider.embed_batch(texts)

            for chunk, emb in zip(batch, embeddings):
                chunk.embedding = emb
                chunk.embedding_model = provider.model_name
                embedded_count += 1

            session.commit()
            logger.info(f"   Embedded {min(i + batch_size, total_chunks)} / {total_chunks} chunks...")

    logger.info(f"✅ Successfully generated embeddings for {embedded_count} document chunks!")
    return embedded_count


def main():
    parser = argparse.ArgumentParser(
        description="Generate vector embeddings for pathology document chunks."
    )
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for embedding generation.")
    parser.add_argument("--force", action="store_true", help="Re-embed all chunks even if already embedded.")
    parser.add_argument("--mock", action="store_true", help="Force deterministic mock embedding provider.")

    args = parser.parse_args()
    generate_embeddings_for_chunks(
        batch_size=args.batch_size,
        force_all=args.force,
        force_mock=args.mock,
    )


if __name__ == "__main__":
    main()
