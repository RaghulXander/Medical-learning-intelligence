import os
import sys
import json
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

results_summary = []

with sessionmaker(bind=engine)() as session:
    benchmark = session.query(RetrievalBenchmark).filter_by(slug="m16a-retrieval-v1").first()
    cases = session.query(RetrievalBenchmarkCase).filter(
        RetrievalBenchmarkCase.benchmark_id == benchmark.id
    ).order_by(RetrievalBenchmarkCase.case_key).all()
    
    print(f"Loaded {len(cases)} cases.")
    for c in cases:
        case_info = {
            "case_id": c.id,
            "case_key": c.case_key,
            "domain": c.domain,
            "query": c.query,
            "out_of_corpus": c.out_of_corpus,
            "expected_chunk_ids": c.expected_chunk_ids,
            "revision": c.revision,
            "retrieved": []
        }
        
        outcome = retrieval_service.search(session, c.query, top_k=5, embedding_run_id=run_id)
        for res in outcome.results:
            is_hit = res.chunk_id in (c.expected_chunk_ids or [])
            case_info["retrieved"].append({
                "rank": res.rank,
                "chunk_id": res.chunk_id,
                "source": res.source_short_name,
                "pdf_page": res.pdf_page,
                "dense_score": res.dense_score,
                "lexical_score": res.lexical_score,
                "fused_score": res.fused_score,
                "is_hit": is_hit,
                "content_preview": res.content[:300]
            })
        
        hit_in_top5 = any(r["is_hit"] for r in case_info["retrieved"])
        if c.out_of_corpus:
            status = "REFUSED" if len(outcome.results) == 0 else "NOT_REFUSED"
        else:
            status = "HIT" if hit_in_top5 else "MISS"
            
        case_info["status"] = status
        results_summary.append(case_info)

engine.dispose()

out_path = PROJECT_ROOT / "scratch" / "cases_analysis.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(results_summary, indent=2), encoding="utf-8")
print(f"Analysis saved to {out_path}")
