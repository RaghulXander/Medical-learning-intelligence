import json
from pathlib import Path

data = json.loads(Path("scratch/cases_analysis.json").read_text(encoding="utf-8"))
cases = {c["case_key"]: c for c in data}

for key in ["diag-002", "diag-003", "neop-010"]:
    c = cases[key]
    print("=" * 80)
    print(f"CASE: {c['case_key']} ({c['domain']})")
    print(f"QUERY: {c['query']}")
    print(f"EXPECTED: {c['expected_chunk_ids']}")
    for r in c["retrieved"]:
        text = r['content_preview'].encode('ascii', 'replace').decode('ascii').replace('\n', ' ')
        print(f"  - Chunk ID: '{r['chunk_id']}' | {r['source']} p.{r['pdf_page']} (dense={r['dense_score']:.3f}, fused={r['fused_score']:.3f})")
        print(f"    Preview: {text[:220]}")
