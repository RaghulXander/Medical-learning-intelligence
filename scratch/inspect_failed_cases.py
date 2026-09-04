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
from backend.services.hybrid_retrieval_service import HybridRetrievalService, HybridRetrievalConfig
from database.models import DocumentChunk, RetrievalBenchmark, RetrievalBenchmarkCase, SourceDocument, Source

failing_ids = [
    "ctrl-001", "ctrl-002", "ctrl-003", "ctrl-004", "ctrl-005",
    "diag-002", "diag-003", "diag-006", "diag-008",
    "gen-path-001", "gen-path-005", "gen-path-006", "gen-path-009", "gen-path-010",
    "hem-001", "hem-008", "hem-010",
    "neop-006", "neop-008", "neop-010",
    "sys-001", "sys-004", "sys-005", "sys-008"
]

provider = GeminiEmbeddingProvider(
    model_name="gemini-embedding-001",
    dimension=768,
    task_type="RETRIEVAL_QUERY",
    vertex_ai=True,
    project="doc-egde-rag",
    location="us-central1"
)
retrieval_service = HybridRetrievalService(
    config=HybridRetrievalConfig(minimum_dense_score=0.60),
    embedding_provider=provider
)
run_id = "cba90495-1c99-416d-989d-fdd246212218"

with sessionmaker(bind=engine)() as session:
    benchmark = session.query(RetrievalBenchmark).filter_by(slug="m16a-retrieval-v1").first()
    cases = session.query(RetrievalBenchmarkCase).filter(
        RetrievalBenchmarkCase.benchmark_id == benchmark.id,
        RetrievalBenchmarkCase.case_key.in_(failing_ids)
    ).order_by(RetrievalBenchmarkCase.case_key).all()
    
    print(f"Loaded {len(cases)} cases to diagnose.\n")
    for c in cases:
        print("=" * 80)
        print(f"CASE: {c.case_key} ({c.domain}) | Out-of-corpus: {c.out_of_corpus}")
        print(f"QUERY: {c.query}")
        print(f"EXPECTED CHUNK IDS: {c.expected_chunk_ids}")
        
        # Check current expected chunks
        if c.expected_chunk_ids:
            exp_chunks = session.query(DocumentChunk, SourceDocument, Source).join(
                SourceDocument, DocumentChunk.document_id == SourceDocument.id
            ).join(Source, SourceDocument.source_id == Source.id).filter(
                DocumentChunk.id.in_(c.expected_chunk_ids)
            ).all()
            for ch, doc, src in exp_chunks:
                print(f"  [CURRENT EXPECTED] {ch.id} ({src.short_name} p.{ch.pdf_page}): {ch.content[:140]}...")
        
        # Run retrieval
        outcome = retrieval_service.search(session, c.query, top_k=5, embedding_run_id=run_id)
        print(f"RETRIEVAL OUTCOME: {len(outcome.results)} results")
        for res in outcome.results:
            hit = " [HIT!]" if res.chunk_id in (c.expected_chunk_ids or []) else ""
            dense_str = f"{res.dense_score:.3f}" if res.dense_score is not None else "None"
            lex_str = f"{res.lexical_score:.3f}" if res.lexical_score is not None else "None"
            print(f"  Rank {res.rank}: {res.chunk_id} ({res.source_short_name} p.{res.pdf_page}) dense={dense_str} lex={lex_str} fused={res.fused_score:.3f}{hit}")
            print(f"    Content: {res.content[:160]}...")

engine.dispose()
