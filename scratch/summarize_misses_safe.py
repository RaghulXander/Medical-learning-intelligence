import json
from pathlib import Path

data = json.loads(Path("scratch/cases_analysis.json").read_text(encoding="utf-8"))

misses = [c for c in data if c["status"] == "MISS"]
refusals = [c for c in data if c["out_of_corpus"]]

print(f"Total cases: {len(data)}")
print(f"Total misses: {len(misses)}")
print(f"Out of corpus count: {len(refusals)}")
for r in refusals:
    print(f"  {r['case_key']}: {r['status']} ({len(r['retrieved'])} retrieved)")

print("\n" + "="*80)
print("ALL MISSES DETAIL:")
for m in misses:
    print("\n" + "-"*80)
    print(f"Case: {m['case_key']} ({m['domain']})")
    print(f"Query: {m['query']}")
    print(f"Expected: {m['expected_chunk_ids']}")
    print("Top Retrieved:")
    for ret in m["retrieved"][:5]:
        preview = ret['content_preview'].encode('ascii', 'replace').decode('ascii')
        print(f"  [Rank {ret['rank']}] Chunk ID: {ret['chunk_id']} ({ret['source']} p.{ret['pdf_page']}) dense={ret['dense_score']} fused={ret['fused_score']}")
        print(f"    Text: {preview[:150]}...")
