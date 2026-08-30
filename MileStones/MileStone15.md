# Milestone 15 — Rights-Verified Book Import and Evidence Foundation

## Decision

Milestone 15 is an **import and evidence-quality milestone**, split into Part A and Part B. It does not generate or publish questions, notes, or social-media images. Those consumers should start only after the imported evidence passes the gates below.

The first vertical slice is **Robbins and Cotran Review of Pathology**. Other books remain out of scope until the same pilot criteria pass.

## Non-negotiable invariants

- Process only documents for which the owner records a legitimate rights/access basis.
- Keep raw PDFs and extracted book content in private object storage or ignored local paths; never commit them to Git.
- Preserve the source document ID, edition, physical PDF page, printed page label when present, parser version, ingestion run, and content hash.
- A local/mock parser may support tests, but its output cannot become medical evidence, embeddings, notes, or questions.
- “Provenance passed” means traceability, not OCR or medical accuracy.
- Generated outputs remain candidates for human review; citations are never invented.

## Part A — Verified Robbins pilot

### Goal

Prove that one small, representative Robbins sample can be extracted accurately and reproducibly before paying to process the full book.

### Scope

1. **Rights-verified intake**
   - Register the exact file with SHA-256, edition metadata, total physical pages, private storage URI, `rights_status=AUTHORIZED`, and a private rights-basis note.
   - Pin a Document AI Layout Parser processor version. Environment-specific IDs stay outside Git.

2. **Stratified pilot set**
   - Select approximately 40–60 pages across front matter, ordinary prose, two-column pages, question/answer pages, tables, and image/figure-heavy pages.
   - Store an immutable pilot manifest with an `ingestion_run_id` and exact page list.

3. **Page calibration**
   - Preserve `pdf_page` for every page.
   - Build a human-verified page-label map for printed Arabic/Roman/unnumbered pages. A single global offset is allowed only if the entire mapping has been checked.
   - Record a page-processing receipt even when the page is blank or yields no text block.

4. **Live extraction**
   - Use the pinned live Layout Parser. Online requests remain at 15 pages/20 MB or less.
   - Persist the raw response privately, then normalize paragraphs, headings, lists, tables, figure captions, and available visual annotations without discarding provenance.
   - Fail closed on API/configuration errors. Never silently replace a live failure with mock output.

5. **Human quality set**
   - Manually transcribe/label a representative subset as gold data.
   - Measure text accuracy, reading order, table cell accuracy, heading classification, figure-caption association, and page-label accuracy separately.
   - Record errors by type and page; automated parser confidence is not a substitute for this review.

### Part A acceptance criteria

- 100% of selected pages have page receipts and valid physical-page provenance.
- 100% of evidence blocks are `LIVE_DOCAI` and reference the registered file hash and pinned processor version.
- Zero mock blocks, silent fallbacks, missing pilot pages, duplicate active pages, or invalid page mappings.
- At least 98% normalized-text character accuracy on the gold sample.
- At least 95% correct reading order and table-cell structure on applicable sampled pages.
- 100% figure captions and image references on the sampled figure-heavy pages are linked to the correct physical page; image crops may remain a Part B deliverable.
- A human reviewer signs off the pilot report and known limitations.

### Part A deliverables

- Rights-verified registry entry and immutable pilot/run manifest.
- Private raw parser output and normalized pilot artifacts.
- Page-label calibration file and page receipts.
- Gold sample, metric report, error log, and go/no-go decision for Part B.

## Part B — Canonical full-book import

### Entry condition

Part A passes. If it does not, improve the parser/configuration and rerun the pilot; do not scale a faulty extraction.

### Scope

1. Implement asynchronous GCS batch processing for the full authorized book. Layout Parser currently permits at most 500 PDF pages per file, so larger books require deterministic input partitions.
2. Introduce idempotent `ingestion_run_id` records with explicit states: `CREATED`, `UPLOADED`, `PROCESSING`, `NORMALIZED`, `QA_REVIEW`, `PASSED`, `FAILED`, `SUPERSEDED`.
3. Mark one run as canonical. Pilot, retry, and superseded artifacts cannot be mixed into the canonical coverage audit.
4. Normalize the complete layout response, including document-layout chunks, lists, tables, figures/visual elements, captions, page receipts, and image/object references supported by the pinned processor.
5. Store raw and derived copyrighted content in private buckets with least-privilege IAM, encryption, lifecycle rules, and audit logging. Git stores only code, schemas, synthetic fixtures, and non-content operational documentation.
6. Run the full-book gate: file integrity, rights status, live parser mode, pinned version, page receipts, unique canonical page coverage, calibrated labels, structural QA, and human-reviewed spot checks.
7. Only after the gate passes, create versioned evidence chunks and embeddings. Every retrieval result must return the source/edition, physical page, printed label, section, content hash, and ingestion run.
8. Build a small retrieval evaluation set of study questions with human-selected relevant pages. Measure retrieval recall before any MCQ or note generation is enabled.

### Part B acceptance criteria

- Every physical PDF page has exactly one successful receipt in the canonical run.
- No failed/missing/duplicate canonical pages and no mock or unknown parser modes.
- Rights, file-integrity, processor-version, page-mapping, and extraction-QA gates pass.
- Full-book spot-check metrics do not regress beyond the agreed Part A tolerance.
- Retrieval returns supporting evidence for at least 90% of the curated evaluation prompts at `Recall@5`; unsupported prompts return “insufficient evidence.”
- Evidence/embedding indexes can be deleted and rebuilt deterministically from the canonical private artifacts.

### Part B deliverables

- Batch/GCS processor and resumable run ledger.
- Canonical full-book evidence corpus with versioned embeddings.
- Full-book provenance/quality report and retrieval evaluation report.
- Approved handoff contract for Milestone 16 question and note generation.

## Explicitly deferred to Milestone 16+

- Evidence-bound MCQ generation and answer/explanation validation.
- Short-note/PDF generation.
- Instagram/Facebook image-note generation and rights-safe media policy.
- Image-based diagnostic questions or pathology image interpretation.
- Fine-tuning local or cloud models. RAG quality and evaluation come first; fine-tuning is not required for one-time digitization.

## Current implementation assessment

The repository already has useful foundations: SHA-256 registration, deterministic slices, dual page fields, normalized blocks, evidence blocks, reports, and an embedding gate. Part A is **not yet complete** because human gold-set accuracy testing, pinned-version validation, structured image/figure handling, and verified page-label calibration remain. Part B is **not started** until batch/GCS processing and canonical ingestion runs exist.

For extraction on one machine and review/application work on another, follow [the two-machine book-processing runbook](../docs/M15_TWO_MACHINE_BOOK_RUNBOOK.md) and its [run handoff template](../docs/templates/M15_RUN_HANDOFF_TEMPLATE.md).
