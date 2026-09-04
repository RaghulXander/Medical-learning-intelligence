import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
database_url = os.environ.get("DATABASE_URL")
engine = create_engine(database_url, hide_parameters=True, pool_pre_ping=True)

from backend.services.embedding_service import GeminiEmbeddingProvider
from database.models import DocumentChunk, DocumentChunkEmbedding, EmbeddingRun

run_id = "cba90495-1c99-416d-989d-fdd246212218"
provider = GeminiEmbeddingProvider(
    model_name="gemini-embedding-001",
    dimension=768,
    task_type="RETRIEVAL_QUERY",
    vertex_ai=True,
    project="doc-egde-rag",
    location="us-central1"
)

query_text = "What is the utility of cytokeratin 7 and cytokeratin 20 (CK7/CK20) expression profile in carcinomas of unknown primary?"
q_vec = provider.embed_text(query_text)

with sessionmaker(bind=engine)() as session:
    distance = DocumentChunkEmbedding.embedding.cosine_distance(q_vec)
    rows = session.query(
        DocumentChunk.id,
        DocumentChunk.pdf_page,
        (1.0 - distance).label("score"),
        DocumentChunk.content
    ).join(
        DocumentChunkEmbedding, DocumentChunkEmbedding.chunk_id == DocumentChunk.id
    ).filter(
        DocumentChunkEmbedding.run_id == run_id
    ).order_by(distance.asc()).limit(5).all()

    print(f"Top 5 dense matches for: '{query_text}'")
    for r in rows:
        print(f"  Chunk {r[0]} p.{r[1]} score={float(r[2]):.4f}")
        print(f"    Content: {r[3][:200]}...\n")

engine.dispose()
