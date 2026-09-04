# M19B Completion Runbook

## Current live state (2026-09-04)

- Benchmark: `m16a-retrieval-v1`
- Total cases: 55
- `HUMAN_VERIFIED`: 25
- `HUMAN_REVIEW`: 30
- The five `ctrl-*` cases are already correctly verified as out-of-corpus controls.
- The final benchmark export remains blocked until all 55 cases are human verified.

## 1. Narrow or replace evidence for the remaining cases

Generate the private review packet from the live database:

```bash
python scripts/export_retrieval_narrowing_packet.py \
  --database-url-env REMOTE_DATABASE_URL
```

Output:

```text
data/processed/reference_documents/review_packets/m19b_remaining_prompt_narrowing.txt
```

The packet contains the current question, review notes, selected chunk IDs,
citations, hashes, and evidence text. It is Git-ignored because it contains
derived textbook content.

Give the whole packet, or one case block at a time, to the review model. Do not
send the private evidence to a third-party service unless the source rights and
provider terms permit it. The model must return one of:

- `KEEP`: the supplied evidence directly answers the current prompt;
- `NARROW`: rewrite the prompt so every requested claim is directly supported;
- `REPLACE_EVIDENCE`: retain the medically useful prompt and search the corpus
  for a better or complementary chunk;
- `OUT_OF_CORPUS`: only when the subject is genuinely absent from all three
  books.

Prompt narrowing must not introduce facts that are absent from the evidence,
put the answer into the question, or turn a useful question into a trivial
yes/no question. After applying each result in the review UI, save the draft,
re-read the revised prompt against the selected evidence, attest, and verify.

## 2. Out-of-corpus controls

No action is currently required. `ctrl-001` through `ctrl-005` are already:

- `out_of_corpus=true`;
- empty `expected_chunk_ids`;
- `HUMAN_VERIFIED` with reviewer notes and audit history.

Do not attach evidence to these controls.

## 3. Produce three PASSED provenance manifests

This must run on the extraction/artifact machine containing the canonical live
Document AI evidence receipts. A database chunk inventory cannot prove that
every physical source page was processed.

Before auditing, isolate one canonical full-book run. Move pilot/retry artifacts
out of `data/processed/reference_documents/`; overlapping page receipts cause a
correct hard-gate failure.

Confirm the registry records the actual authorized PDFs, file hashes, page
counts, rights basis, and one pinned live processor version. Then run:

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

Each generated JSON manifest must have:

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
sha256 matching the registered source document
```

The three JSON and Markdown manifests are generated under:

```text
data/processed/reference_documents/provenance_manifests/
```

That directory is intentionally Git-ignored. Transfer the manifests and their
canonical extraction receipts through the private versioned GCS run prefix
described in `docs/M15_TWO_MACHINE_BOOK_RUNBOOK.md`; do not commit textbook
artifacts to Git.

## 4. Export the verified benchmark

First make sure the review summary shows 55/55 `HUMAN_VERIFIED`. Then validate
the deterministic export without writing a file:

```bash
python scripts/export_retrieval_review_dataset.py \
  --database-url-env REMOTE_DATABASE_URL
```

If validation succeeds, write the export:

```bash
python scripts/export_retrieval_review_dataset.py \
  --database-url-env REMOTE_DATABASE_URL \
  --execute
```

If the destination already exists and this is an intentional replacement, add
`--overwrite`. Record the printed `dataset_hash`, case count, in-corpus domain
count, out-of-corpus count, and referenced chunk count in the milestone audit.
Do not use `--overwrite` merely to bypass an unexpected mismatch.

Expected output:

```text
data/evaluation/retrieval/verified/m16a_retrieval_eval_v1.jsonl
```

The exporter refuses to run if the benchmark is not fully human verified or if
any case lacks evidence/review provenance.
