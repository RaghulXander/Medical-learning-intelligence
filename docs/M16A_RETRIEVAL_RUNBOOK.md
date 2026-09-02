# Milestone 16A retrieval runbook

This runbook is for the machine that has the legitimately obtained PDFs, the
complete live Document AI artifacts, GCP Application Default Credentials, and
the local PostgreSQL database. Do not copy `.env` into Git or command output.

## 1. Start and migrate local PostgreSQL

```bash
docker compose -f infrastructure/docker-compose.yml up -d postgres
python -m alembic upgrade head
```

Revision `20260901_0005` must be current. It creates immutable embedding runs,
`vector(768)` storage, and the HNSW cosine index without changing book text.

## 2. Promote the private transfer database when needed

Skip this section when all three books are already present in PostgreSQL.

```bash
python scripts/promote_reference_content.py --dry-run
python scripts/promote_reference_content.py
```

The expected promoted scope is:

- `robbins_review`: 496 chunks;
- `robbins_pathologic_basis_11th`: 1,223 chunks;
- `sternberg_review_2nd`: 1,126 chunks;
- the first two-book total remains 1,719 chunks and the verified three-book
  transfer total is 2,845 chunks.

For the 2026-09-02 transfer, the sorted three-book content-hash manifest SHA-256
was `88424b7e4561348083d43f1947b14f732bc225ff8e08b23071737f852975d787` in
both the private SQLite transfer copy and local PostgreSQL. A later extraction
must establish and record its own matching manifest rather than assuming these
counts or this hash.

The command is transactional and refuses source, document, or content-hash
conflicts. Its private promotion receipt contains counts and hashes, not book
text.

## 3. Pass the M15 provenance gate on the PDF machine

Run the existing audit against the complete live extraction artifacts:

```bash
python scripts/manage_reference_documents.py audit --doc robbins_review --enforce
python scripts/manage_reference_documents.py audit --doc robbins_pathologic_basis_11th --enforce
python scripts/manage_reference_documents.py audit --doc sternberg_review_2nd --enforce
```

For Robbins Pathologic Basis 11th, visually confirm or supply explicit page
receipts for physical PDF pages 4, 6, 16, and 1,226. Do not mark these pages
blank from OCR absence alone.

Both generated JSON manifests under
`data/processed/reference_documents/provenance_manifests/` must report:

- `status: PASSED` and `is_ready_for_embedding: true`;
- authorized rights;
- zero missing, failed, or duplicate pages;
- `LIVE_DOCAI` only;
- one pinned processor version;
- a PDF SHA-256 matching the corresponding PostgreSQL source document.

The embedding command validates these values itself. There is no manual SQL
override.

## 4. Review the embedding plan without calling Vertex AI

```bash
python scripts/generate_evidence_embeddings.py
```

Proceed only when it reports the independently verified three-book chunk count,
`dimension=768`, `model=gemini-embedding-001`, and `provenance_ready=True`. The dry run creates no
run and makes no paid API call.

After checking the current Vertex AI price/quota and confirming approval, create
one real run:

```bash
EMBEDDING_PROVIDER=vertex_ai python scripts/generate_evidence_embeddings.py --execute
```

The run uses `RETRIEVAL_DOCUMENT`, output dimension 768, and automatic
truncation disabled. Any SDK/API/vector-count/vector-dimension error marks the
run failed; it never substitutes mock vectors.

## 5. Build the human retrieval gold set

Follow the benchmark instructions in `data/evaluation/retrieval/README.md`.
Create 50–75 human-authored cases across at least five domains, manually verify
the expected chunk IDs/pages, and include out-of-corpus controls.

Validate labels without calling Vertex AI:

```bash
python scripts/evaluate_retrieval.py \
  --dataset data/evaluation/retrieval/m16a_retrieval_eval_v1.jsonl \
  --validate-only
```

## 6. Measure the real run

Use the run ID printed by the embedding command:

```bash
python scripts/evaluate_retrieval.py \
  --dataset data/evaluation/retrieval/m16a_retrieval_eval_v1.jsonl \
  --embedding-run-id RUN_ID \
  --output data/evaluation/retrieval/reports/m16a_retrieval_eval_v1.json
```

MCQ generation remains blocked unless the report passes all M16A gates:
Recall@5 at least 90% overall, no domain below 80%, all unsupported controls
refused, and zero citation/hash mismatches. A failed gate means retrieval must be
corrected and measured again; it is not permission to generate more questions.
