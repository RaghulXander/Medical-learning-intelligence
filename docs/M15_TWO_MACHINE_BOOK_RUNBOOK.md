# Milestone 15 Two-Machine Book Processing Runbook

## Purpose

Use this runbook when the authorized source PDFs and Google Cloud credentials are on an extraction machine, while the application repository/database may run on another machine.

The two initial documents are:

| Short name | Document | Current registered size |
|---|---|---:|
| `robbins_review` | Robbins and Cotran Review of Pathology | 496 PDF pages / 34 online chunks |
| `robbins_pathologic_basis_11th` | Robbins & Cotran Pathologic Basis of Disease, 11th Edition | 1,227 PDF pages / 82 online chunks |

Treat the page and chunk counts as expectations, not constants. The registered PDF on the extraction machine is authoritative.

## Architecture decision

Do **not** copy or upload an application database from the extraction machine.

```text
Authorized PDFs + GCP credentials
        |
        v
Extraction machine
  raw Document AI JSON
  normalized JSON
  evidence JSON
  reports and provenance manifests
        |
        v
Private, versioned GCS run prefix
        |
        v
Application/review machine
  restore + verify artifacts
        |
        v
Future idempotent DB importer
  Source -> SourceDocument -> DocumentChunk -> embeddings
```

The extraction outputs are the portable system of record for this milestone. PostgreSQL/pgvector is a downstream, reproducible index.

## Important current limitation

The repository does not yet provide:

- asynchronous Document AI batch processing;
- canonical `ingestion_run_id` isolation in code;
- a JSON-to-`source_documents`/`document_chunks` database importer;
- an embedding column and embedding-generation command;
- a retrieval evaluation command.

Therefore this runbook ends at a validated artifact handoff. Do not manually insert the book JSON into PostgreSQL. Implement and test the idempotent importer before the database/RAG phase.

## 1. Rules that apply on both machines

1. Use only legitimately obtained documents for which processing rights/access have been recorded.
2. Keep PDFs, extracted text, and derived JSON in private storage. Never commit them to Git.
3. Never commit `.env`, service-account keys, credentials, access tokens, or `GCP.txt`.
4. Use the same Git commit on both machines. Record it with `git rev-parse HEAD`.
5. Use a pinned Document AI processor version and `DOCAI_MOCK_FALLBACK=false`.
6. Never use `--mock` for evidence intended for RAG, notes, or question generation.
7. Complete and audit one book before starting the second.

Before proceeding, this command must show that `.env` is ignored:

```bash
git check-ignore -v .env
```

If it prints nothing, stop and restore the `.env`/`.env.*` rules in `.gitignore` before any commit or push.

## 2. Extraction-machine preflight

Run from the repository root:

```bash
git status --short
git rev-parse HEAD
python -m pip install -r requirements.txt
python -m pytest tests/test_reference_document_ingestion.py \
  tests/test_medical_normalizer.py \
  tests/test_provenance_manifest.py -q
gcloud auth application-default login
```

Create an ignored `.env` using `.env.gcp.example` and set:

```env
GCP_PROJECT_ID=<project-id>
GCP_LOCATION=us
GCP_PROCESSOR_ID=<layout-parser-processor-id>
GCP_PROCESSOR_VERSION_ID=<tested-processor-version-id>
GCP_RAW_BUCKET=<private-raw-bucket>
GCP_PROCESSED_BUCKET=<private-processed-bucket>
DOCAI_MAX_ONLINE_PAGES=15
DOCAI_MOCK_FALLBACK=false
```

Application Default Credentials are preferred. If `GOOGLE_APPLICATION_CREDENTIALS` is used, it must reference a key outside the repository.

Place the authorized PDFs at the exact expected paths:

```text
data/raw/reference_documents/Robbins and Cotran Review of Pathology.pdf
data/raw/reference_documents/Robbins_and_Cotran_Pathologic_Basis_of_Disease_11th_Edition.pdf
```

Confirm that no credential or PDF is staged:

```bash
git status --short
```

## 3. Register and verify both sources

Run each command only when its rights statement is true:

```bash
python scripts/manage_reference_documents.py register \
  --doc robbins_review \
  --rights-status AUTHORIZED \
  --rights-basis "<private rights/access note>"

python scripts/manage_reference_documents.py register \
  --doc robbins_pathologic_basis_11th \
  --rights-status AUTHORIZED \
  --rights-basis "<private rights/access note>"

python scripts/manage_reference_documents.py verify
python scripts/manage_reference_documents.py list
```

Record each document ID, SHA-256, total page count, edition, and Git commit in a copy of [the handoff template](templates/M15_RUN_HANDOFF_TEMPLATE.md).

## 4. Run and approve a live pilot first

Do not immediately process every page. For each book, choose 40–60 representative pages covering ordinary text, two-column layouts, tables, questions/answers, and figure-heavy pages.

Example for one 15-page range:

```bash
python scripts/manage_reference_documents.py split \
  --doc robbins_review \
  --start <PDF_START_PAGE> \
  --end <PDF_END_PAGE> \
  --suffix m15a

python scripts/process_reference_documents.py process \
  --slice robbins_review_p<START_4_DIGITS>_p<END_4_DIGITS>_m15a
```

Review:

```text
data/processed/reference_documents/raw_docai/
data/processed/reference_documents/normalized/
data/processed/reference_documents/evidence_blocks/
data/processed/reference_documents/reports/
```

The pilot must meet the acceptance criteria in `MileStones/MileStone15.md`. Parser confidence alone is not approval; inspect source/page mapping, reading order, tables, figure captions, and a human-transcribed gold sample.

## 5. Prepare a clean canonical full-book run

The current auditor reads every matching evidence file. If pilot/retry and full-run files overlap, duplicate pages correctly block the embedding gate.

For the canonical run, use a fresh clone or move the pilot output tree into a private backup outside `data/processed/reference_documents/`, then re-register the two PDFs. Do not delete the pilot until it has been uploaded or otherwise backed up.

Record a unique run ID in the handoff file, for example:

```text
m15-robbins-live-YYYYMMDD-01
```

The run ID is currently an operational/GCS identifier; it is not yet represented in the generated JSON schema.

## 6. Process Robbins Review completely

```bash
python scripts/process_reference_documents.py book \
  --doc robbins_review \
  --pages-per-chunk 15
```

If interrupted, identify the last fully successful physical PDF page and resume from the next page:

```bash
python scripts/process_reference_documents.py book \
  --doc robbins_review \
  --pages-per-chunk 15 \
  --start-page <NEXT_PDF_PAGE>
```

Do not assume that command completion means quality approval. Run the hard audit:

```bash
python scripts/manage_reference_documents.py audit \
  --doc robbins_review \
  --pages-per-chunk 15 \
  --enforce
```

Proceed only if the manifest says `PASSED` and `is_ready_for_embedding=true`.

## 7. Process Robbins Pathologic Basis second

Only after Robbins Review passes:

```bash
python scripts/process_reference_documents.py book \
  --doc robbins_pathologic_basis_11th \
  --pages-per-chunk 15

python scripts/manage_reference_documents.py audit \
  --doc robbins_pathologic_basis_11th \
  --pages-per-chunk 15 \
  --enforce
```

The current command uses sequential online calls of at most 15 pages. Do not run both books concurrently. Google documents a 500-page-per-file Layout Parser batch limit, but the repository's asynchronous batch/GCS processor is still Milestone 15B work.

## 8. Artifact completeness check

Before upload, verify that the run contains:

```text
reference_documents/
├── registry.json
├── slices/*_manifest.json
├── raw_docai/*_docai.json
├── normalized/*_normalized.json
├── evidence_blocks/*_evidence.json
├── reports/*_quality_report.json
├── reports/*_quality_report.md
└── provenance_manifests/*_provenance_manifest.{json,md}
```

Slice PDFs do not need to be transferred for database/RAG handoff. Preserve the original authorized PDFs separately in the private raw bucket if cross-machine recovery is required.

Complete the handoff template with:

- run ID and Git commit;
- processor ID and pinned version;
- document IDs and file SHA-256 values;
- expected/completed pages and chunks;
- audit status;
- known failed pages or quality limitations;
- destination GCS prefix.

Place the completed handoff file inside `data/processed/reference_documents/` before upload.

## 9. Upload JSON artifacts to a private GCS run prefix

Use an immutable, unique destination. Replace all angle-bracket placeholders explicitly.

Preview the upload while excluding generated slice PDFs:

```bash
gcloud storage rsync \
  data/processed/reference_documents \
  gs://<PROCESSED_BUCKET>/reference-document-runs/<RUN_ID>/ \
  --recursive \
  --exclude='.*\.pdf$' \
  --dry-run
```

Review every destination, then upload:

```bash
gcloud storage rsync \
  data/processed/reference_documents \
  gs://<PROCESSED_BUCKET>/reference-document-runs/<RUN_ID>/ \
  --recursive \
  --exclude='.*\.pdf$'
```

List the uploaded objects and retain the run prefix in the handoff file:

```bash
gcloud storage ls --recursive \
  gs://<PROCESSED_BUCKET>/reference-document-runs/<RUN_ID>/
```

Do not use `--delete-unmatched-destination-objects`. Keep public access prevention and uniform bucket-level access enabled. Object Versioning plus lifecycle rules can protect replacements while controlling storage cost.

## 10. Restore on the application/review machine

Use the same Git commit as the extraction run. Keep the destination outside any directory containing a different active run.

Preview:

```bash
gcloud storage rsync \
  gs://<PROCESSED_BUCKET>/reference-document-runs/<RUN_ID>/ \
  data/processed/reference_documents \
  --recursive \
  --dry-run
```

Restore:

```bash
gcloud storage rsync \
  gs://<PROCESSED_BUCKET>/reference-document-runs/<RUN_ID>/ \
  data/processed/reference_documents \
  --recursive
```

Then inspect the completed handoff file and rerun the non-destructive audits:

```bash
python scripts/manage_reference_documents.py audit \
  --doc robbins_review \
  --pages-per-chunk 15 \
  --enforce

python scripts/manage_reference_documents.py audit \
  --doc robbins_pathologic_basis_11th \
  --pages-per-chunk 15 \
  --enforce
```

`manage_reference_documents.py verify` requires the original PDFs at the registered paths and can fail after a cross-machine JSON-only restore. The handoff's recorded hashes and successful extraction-machine integrity report remain required until registry paths become storage URIs.

## 11. Database and RAG handoff — do not execute yet

The intended database mapping is:

| Artifact | Database target | Rule |
|---|---|---|
| Registry book | `sources` | One canonical work/title |
| Registered edition/file | `source_documents` | Edition, file hash, rights/provenance metadata |
| Page evidence block | `document_chunks` | Exact physical page, printed page label, section, content hash, run metadata |
| Future embedding | future vector column/table | Provider/model/version recorded; rebuildable |

Before importing, implement a tested CLI such as:

```text
python scripts/import_reference_evidence.py \
  --run-dir <RESTORED_RUN_DIR> \
  --database-url <FROM_SECRET_STORE> \
  --dry-run
```

Required importer behavior:

1. Refuse manifests that are not `PASSED`/ready for embedding.
2. Refuse mock/unknown parser modes, missing processor versions, unverified rights, missing/duplicate pages, or mixed runs.
3. Validate document and content hashes before writes.
4. Use deterministic IDs and transactional upserts so reruns cannot duplicate chunks.
5. Preserve both physical PDF page and printed page label.
6. Store ingestion run, parser version, normalization version, source edition, and hashes in metadata.
7. Produce dry-run counts and a post-import reconciliation report.
8. Add an Alembic migration for the chosen pgvector schema before generating embeddings.
9. Keep embeddings replaceable and record embedding provider/model/version.
10. Run retrieval evaluation before enabling question or note generation.

Until that importer and migration exist, the correct output of Milestone 15 is a private, validated, restorable GCS artifact run—not a database dump.

## 12. Failure rules

- API failure: stop; do not enable mock fallback.
- Missing/duplicate page: keep the failed run for diagnosis and rerun only affected ranges in a new run.
- Page-label mismatch: correct calibration/version and rerun affected evidence.
- Audit not passed: upload under a clearly marked `failed-runs/` prefix if remote debugging is needed; never import it.
- Different Git commit or processor version: treat as a separate run.
- Credential or `.env` appears in `git status`: stop before commit/push.

## Official references

- [Google Cloud `gcloud storage rsync`](https://docs.cloud.google.com/sdk/gcloud/reference/storage/rsync)
- [Google Cloud Storage Object Versioning](https://docs.cloud.google.com/storage/docs/object-versioning)
- [Document AI quotas and limits](https://docs.cloud.google.com/document-ai/docs/limits)

