# Milestone 16A retrieval benchmark

Create `m16a_retrieval_eval_v1.jsonl` here only after a human reviewer has
written each query and verified its relevant chunk IDs/pages in PostgreSQL.
Generated queries or automatically inferred gold labels are not acceptable.

Each JSONL row has this shape:

```json
{"id":"general-001","domain":"general_pathology","query":"...","expected_chunk_ids":["verified-chunk-id"],"out_of_corpus":false,"reviewer":"reviewer-id","verification_status":"HUMAN_VERIFIED"}
```

An unsupported control prompt uses an empty `expected_chunk_ids` list and
`"out_of_corpus": true`.

Requirements:

- 50–75 total cases;
- at least five medical domains;
- at least one deliberately out-of-corpus control;
- one or more manually verified chunk IDs for every in-corpus query;
- no copied review-book question stems.

`scripts/build_retrieval_eval_set.py` produces bootstrap candidates using term
matching. Its output is deliberately marked `AUTO_BOOTSTRAP_UNVERIFIED` and is
rejected by the evaluator until a human checks each expected chunk and changes
the reviewer and status truthfully.

Validate labels without calling Vertex AI:

```bash
python scripts/evaluate_retrieval.py \
  --dataset data/evaluation/retrieval/m16a_retrieval_eval_v1.jsonl \
  --validate-only
```

The scored command is run only after a real completed embedding run exists. Its
JSON report records the dataset hash, model/run, retrieval configuration,
Recall@1/5/10, MRR, refusal rate, per-domain failures, and the gate decision.
