import json
from pathlib import Path

data = json.loads(Path("scratch/cases_analysis.json").read_text(encoding="utf-8"))
misses = [c for c in data if c["status"] == "MISS"]

for idx, m in enumerate(misses, 1):
    print("=" * 80)
    print(f"{idx}. CASE: {m['case_key']} ({m['domain']}) [Case ID: {m['case_id']}]")
    print(f"QUERY: {m['query']}")
    print(f"EXPECTED: {m['expected_chunk_ids']}")
    print("TOP RETRIEVED CHUNKS:")
    for r in m["retrieved"][:3]:
        text = r['content_preview'].encode('ascii', 'replace').decode('ascii').replace('\n', ' ')
        print(f"  - Chunk ID: '{r['chunk_id']}' | {r['source']} p.{r['pdf_page']} (dense={r['dense_score']:.3f}, fused={r['fused_score']:.3f})")
        print(f"    Preview: {text[:220]}")
