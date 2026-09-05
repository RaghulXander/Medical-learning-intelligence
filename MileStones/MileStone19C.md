# Milestone 19C — Gold-Set Repair, Provenance Closure, and Real Retrieval Acceptance

> **Status: COMPLETE (2026-09-05).** The final human-reviewed dataset hash is
> `09b1c01e47a47837ebc989da834f426704ab2a79828d03e6e66769f7a18e2bd9`.
> Embedding run `cba90495-1c99-416d-989d-fdd246212218` achieved 98% Recall@5,
> 100% out-of-corpus refusal, and zero citation/hash mismatches. The sections
> below are retained as the execution history and reproducibility runbook.

## Purpose

Run this milestone on the machine that has:

- the complete canonical Document AI artifacts for all three authorized books;
- GCP Application Default Credentials;
- access to the PostgreSQL database containing the 2,845 promoted chunks;
- `REMOTE_DATABASE_URL` configured in the ignored `.env` file.

Do not start paid embeddings merely because the benchmark row says
`HUMAN_VERIFIED`. Phase 0 below repairs the invalid gold labels found during the
2026-09-04 audit and closes the three-book provenance gate first.

## Current audited state

The following mechanical checks pass:

- benchmark `m16a-retrieval-v1` contains 55/55 `HUMAN_VERIFIED` rows;
- `ctrl-001` through `ctrl-005` are valid out-of-corpus controls with empty
  evidence;
- the committed export contains 55 rows and matches the live deterministic
  payload;
- current dataset SHA-256 is
  `a3f8eff6b1f32f359146e40d3cf252e2c73eb7b78b3c86b7f94a7d92f5605c95`.

That export is not an accepted gold set. The ten automatically replaced cases
were assigned unrelated front matter or early Chapter 1 chunks because
`scripts/apply_review_decisions.py` selected the first keyword-search result and
immediately approved it.

The current checkout also has only an old incomplete Robbins Review manifest.
The other two passed manifests were not available for verification.

## Hard rules

1. Do not run `scripts/apply_review_decisions.py` against this benchmark again.
2. Do not approve the first search result automatically.
3. Do not mark a pathology prompt out of corpus merely because one search
   returned no rows.
4. Every selected chunk must be read and must directly support every material
   claim in the final prompt.
5. Preserve revision history through `RetrievalReviewService`; do not update
   benchmark tables with raw SQL.
6. A human reviewer must attest the final prompt/evidence pair. An automated
   script may save a draft but must not manufacture human approval.
7. Do not use mock embeddings for acceptance.
8. Do not run `--execute` for Vertex AI until Phase 0 passes and the user has
   separately approved current cost/quota.

## Phase 0A — Repair the ten invalid replacement labels

Reopen and adjudicate these cases:

```text
diag-002
diag-006
diag-008
gen-path-010
hem-001
hem-008
hem-010
sys-001
sys-004
sys-005
```

Known invalid current selections:

| Case | Current evidence problem |
|---|---|
| `diag-002` | Chromatin/gene-editing content; does not support CK7/CK20 profiling |
| `diag-006` | “Activate your eBook” page |
| `diag-008` | Chapter contents/noncoding DNA; does not support lung NGS testing |
| `gen-path-010` | Copyright page |
| `hem-001` | Promotional “Key Features” page |
| `hem-008` | Foreword/contributor material |
| `hem-010` | miRNA/cellular-housekeeping content |
| `sys-001` | Book cover |
| `sys-004` | Membrane transport/cytoskeleton content |
| `sys-005` | Promotional “Key Features” page |

For each case:

1. Search all three allowed sources with focused synonyms.
2. Open and read up to five candidate chunks, including neighboring physical
   pages when the answer spans a page boundary.
3. Select one or more chunks only when their text directly answers the prompt.
4. If the corpus supports only part of the prompt, narrow the prompt to that
   supported claim.
5. Save the corrected draft with a note naming what the evidence supports and
   what was removed.
6. Have the human reviewer re-read the final prompt and evidence, attest, and
   choose **Verify**.

Acceptance for Phase 0A:

- none of the ten cases points to a cover, copyright, advertisement, contents,
  contributor, or unrelated general-science chunk;
- every evidence ID resolves to an allowed source with physical page, content
  hash, and source-document provenance;
- every case has a `SAVE_DRAFT` followed by a genuine human `APPROVE` event.

## Phase 0B — Re-attest the twenty narrowed labels

The following cases were narrowed and immediately approved by automation. The
prompt revisions may be usable, but their approval must be confirmed against
the complete selected evidence:

```text
diag-003  diag-004  diag-005  diag-009  diag-010
gen-path-001  gen-path-002  gen-path-005  gen-path-006  gen-path-007  gen-path-009
hem-003  hem-005  hem-009
neop-006  neop-008  neop-010
sys-002  sys-003  sys-008
```

For each one, verify that the revised question is medically meaningful and
fully answerable from the selected chunk. Reopen and correct any case that only
mentions a term without defining or explaining what the prompt asks.

Acceptance for Phase 0B:

- all twenty prompt/evidence pairs have been explicitly reviewed by a human;
- no prompt embeds its answer or becomes a trivial yes/no question;
- all material claims are directly supported by the selected evidence.

## Phase 0C — Produce and verify all three provenance manifests

Use one clean canonical artifact run. Pilot and retry evidence files must be
moved outside `data/processed/reference_documents/`; overlapping page receipts
correctly fail the duplicate-page gate.

Run:

```bash
python scripts/manage_reference_documents.py audit \
  --doc robbins_review \
  --pages-per-chunk 15 \
  --enforce
```

```bash
python scripts/manage_reference_documents.py audit \
  --doc robbins_pathologic_basis_11th \
  --pages-per-chunk 15 \
  --enforce
```

```bash
python scripts/manage_reference_documents.py audit \
  --doc sternberg_review_2nd \
  --pages-per-chunk 15 \
  --enforce
```

For Robbins Pathologic Basis 11th, visually confirm or supply explicit page
receipts for physical PDF pages 4, 6, 16, and 1,226. OCR absence alone is not
proof that a page is blank.

Each JSON manifest under
`data/processed/reference_documents/provenance_manifests/` must contain:

```text
status = PASSED
is_ready_for_embedding = true
rights_verified = true
missing_pages = []
failed_chunks = []
duplicate_pages = []
page_mapping_valid = true
processing_modes = [LIVE_DOCAI]
exactly one processor_version_id
sha256 matching the corresponding PostgreSQL source_document.file_hash
```

Keep these manifests and extraction receipts private and transfer them through
the versioned private GCS run prefix. They are intentionally Git-ignored.

## Phase 0D — Regenerate and validate the corrected benchmark

The current committed export must be replaced after any repaired case changes.

Dry-run the deterministic export against the remote database:

```bash
python scripts/export_retrieval_review_dataset.py \
  --database-url-env REMOTE_DATABASE_URL
```

Write the corrected export only after all 55 cases are again verified:

```bash
python scripts/export_retrieval_review_dataset.py \
  --database-url-env REMOTE_DATABASE_URL \
  --execute \
  --overwrite
```

Validate that every referenced chunk exists without calling Vertex AI. Point
the application at the remote database for this shell session without printing
the URL:

```bash
export DATABASE_URL="$REMOTE_DATABASE_URL"
```

```bash
python scripts/evaluate_retrieval.py \
  --dataset data/evaluation/retrieval/verified/m16a_retrieval_eval_v1.jsonl \
  --validate-only
```

Record the new dataset hash. It must differ from the old hash if any prompt or
expected evidence ID changed.

Phase 0 is complete only when:

- the corrected 55-case dataset passes validation;
- all three book manifests pass;
- the ten invalid replacements are repaired;
- the twenty automated narrow decisions are genuinely re-attested.

## Phase 1 — Preflight the real embedding run

The embedding client reads `GCP_PROJECT_ID` (or `GOOGLE_CLOUD_PROJECT`) but
reads its region from `GOOGLE_CLOUD_LOCATION`. `GCP_LOCATION` is used by the
Document AI workflow and is not consumed by the embedding provider. Set the
Vertex AI region explicitly in the shell without printing credentials:

```bash
export GOOGLE_CLOUD_PROJECT="$GCP_PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="<VERTEX_AI_REGION>"
```

Run the relevant tests:

```bash
python -m pytest \
  tests/test_retrieval_review_service.py \
  tests/test_retrieval_review_export.py \
  tests/test_provenance_manifest.py \
  tests/test_hybrid_retrieval_postgres.py \
  -q
```

Review the plan without making a paid request or database write:

```bash
python scripts/generate_evidence_embeddings.py
```

The dry run must report:

- exactly the intended three sources;
- the independently reconciled corpus chunk count;
- `gemini-embedding-001`;
- dimension `768`;
- document task type `RETRIEVAL_DOCUMENT`;
- query task type `RETRIEVAL_QUERY`;
- automatic truncation disabled;
- `provenance_ready=True`;
- a recorded configuration hash and corpus manifest hash.

Stop if the count or provenance flag differs. Do not use a manual override.

## Cost approval checkpoint

Stop here and report the dry-run chunk count, configuration hash, active GCP
project/location, quota availability, and current estimated cost. Obtain the
user's explicit approval before invoking `--execute`.

## Phase 2 — Create one immutable Vertex AI embedding run

After explicit cost approval only:

```bash
python scripts/generate_evidence_embeddings.py \
  --execute \
  --batch-size 20 \
  --chunking-version promoted-page-chunks-v1
```

Record the printed embedding run ID. Preserve failed runs for diagnosis; never
delete or convert them into completed runs, and never substitute mock vectors.

Verify in PostgreSQL that:

- run status is `COMPLETED`;
- completed count equals expected count;
- failed count is zero;
- every vector has 768 dimensions;
- each embedding receipt retains the source chunk content hash.

## Phase 3 — Evaluate hybrid retrieval

Use the completed real run ID:

```bash
python scripts/evaluate_retrieval.py \
  --dataset data/evaluation/retrieval/verified/m16a_retrieval_eval_v1.jsonl \
  --embedding-run-id <RUN_ID> \
  --output data/evaluation/retrieval/reports/m19c_retrieval_eval_v1.json
```

Record:

- Recall@1, Recall@5, and Recall@10;
- MRR;
- per-domain Recall@5;
- out-of-corpus refusal rate;
- citation/hash mismatch count;
- dataset, embedding-run, and retrieval-configuration hashes;
- every failed case.

## M19C acceptance gate

Milestone 19C passes only when all are true:

- Recall@5 is at least 90% overall;
- every domain has Recall@5 of at least 80%;
- all five out-of-corpus controls return `INSUFFICIENT_EVIDENCE`;
- citation/hash mismatches equal zero;
- the evaluation uses a complete non-mock embedding run;
- the report is bound to the corrected human gold-set hash.

If the gate fails, preserve the report, diagnose the named failures, improve
retrieval, and run a new versioned evaluation. Do not begin Milestone 19D
question generation until this gate passes.

## Required handoff

Return these items to the main development machine:

1. corrected verified JSONL and dataset SHA-256;
2. the three private `PASSED` provenance JSON/Markdown manifests or their GCS
   run URI;
3. embedding run ID and configuration hash;
4. M19C evaluation JSON report;
5. exact Git commit used;
6. any failed/reopened case IDs and unresolved extraction anomalies.
