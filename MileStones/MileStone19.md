# Milestone 19 — Evidence Acceptance and Multimodal Safety Stabilization

> **Status: PART 19A COMPLETE / PART 19B REVIEW TOOLING READY, HUMAN REVIEW PENDING / PARTS 19C–19E DRAFT — no paid
> embeddings or generation may run before the M15/M16 quality gates pass**

## Purpose

Convert the three-book corpus and the newly uploaded private image catalog into
a reproducible, measurable RAG foundation before generating study questions or
notes. This milestone closes execution gaps in Milestones 15, 16, and 18; it
does not add another bulk content generator.

Accuracy is the primary objective. A database row, page co-occurrence, or fluent
model response is not medical verification.

## Current verified baseline

- Local and remote text scope: 2,845 unique chunks across three books.
- Text manifest SHA-256:
  `88424b7e4561348083d43f1947b14f732bc225ff8e08b23071737f852975d787`.
- Remote private image catalog: 2,165 assets, 2,165 source occurrences, and
  3,053 image-to-text links.
- All 3,053 current image-to-text links are `AI_SUGGESTED` page
  co-occurrences; none is human verified.
- Current image rows are rights-restricted internal assets. They are not public
  social-media material.
- No real embedding run exists.
- The 55 bootstrapped retrieval cases are not human gold labels.
- No generated question is approved merely because it was persisted.

## Part 19A — Image catalog schema and local metadata mirror

This is the only part that can run immediately.

1. Add an Alembic migration for the image asset, occurrence, and text-link
   tables already present remotely.
2. Copy only metadata and private object references using an explicitly
   read-only remote transaction.
3. Require matching local source-document and chunk hashes before accepting a
   link.
4. Dry-run by default; write only with an explicit execution flag.
5. Make repeated syncs idempotent and verify a deterministic aggregate manifest
   after commit.
6. Do not download binaries, create public URLs, or generate questions.

**19A acceptance:** remote/local counts and manifests match; Alembic owns the
local schema; text/questions/ontology data remain unchanged.

## Part 19B — M15 provenance closure and human retrieval gold set

Entry condition: access to the complete live extraction receipts or manifests
from the PDF/GCP processing machine.

1. Produce one `PASSED` provenance manifest per book with authorized rights,
   matching PDF hash, pinned live processor version, and adjudicated no-text
   pages.
2. Resolve missing/blank pages using receipts or visual confirmation; OCR
   absence alone is not a blank-page decision.
3. Manually review the 55 bootstrapped retrieval cases. Correct the prompt,
   domain, expected chunk IDs/pages, and out-of-corpus label.
4. Mark a case `HUMAN_VERIFIED` only with reviewer identity, timestamp, and
   notes. Automatically selected chunks remain unverified.
5. Expand to 50–75 cases only to close domain coverage gaps, not to inflate the
   benchmark.

Implementation available for the retrieval-label portion:

- role-gated admin queue at `/admin/retrieval-review`;
- complete selected chunk text and source/page/hash provenance shown to the
  reviewer;
- editable prompt, domain, evidence set, and out-of-corpus flag;
- explicit human attestation before approve/reject;
- optimistic revision checks and immutable save/decision history;
- bootstrap import remains `AUTO_BOOTSTRAP_UNVERIFIED` by design.
- deterministic verified-JSONL export with reviewer metadata and evidence
  receipts; export remains blocked until every human and dataset-shape gate
  passes.

See `docs/M19B_RETRIEVAL_HUMAN_REVIEW.md` for setup and reviewer instructions.

**19B acceptance:** all three provenance manifests pass and every benchmark
label is human verified. Until then, embedding execution remains blocked.

## Part 19C — Real embeddings and retrieval acceptance

Entry condition: Part 19B passes and the user approves current Vertex AI cost
and quota.

1. Run one immutable `gemini-embedding-001` document embedding cohort at 768
   dimensions with automatic truncation disabled.
2. Record provider/model version, task types, chunking version, configuration
   hash, input count, failures, and corpus manifest.
3. Evaluate hybrid dense/lexical retrieval on the human gold set.
4. Preserve failed runs and reports; never substitute mock embeddings.

**19C acceptance:** Recall@5 at least 90% overall, every domain at least 80%,
100% out-of-corpus refusal, and zero citation/hash mismatches.

## Part 19D — Fifty-question text-only calibration pilot

Entry condition: Part 19C passes.

1. Approve a learning-objective blueprint covering five evaluated domains.
2. Generate exactly one structured candidate per request, up to 50 total.
3. Require evidence IDs for the answer, explanation, and factual distractor
   rationales.
4. Derive quality scores from recorded evaluator signals. Never assign a fixed
   `0.95` or `0.98` score.
5. Randomize option order reproducibly; the correct answer must not always be
   option A.
6. Reject copied or substantially overlapping textbook prose.
7. Keep candidates in `GENERATED`, `AI_REVIEW`, or `HUMAN_REVIEW`; only a human
   can approve them for personal exams.

**19D acceptance:** every accepted answer/explanation is human-confirmed and
evidence-supported; zero invented citations or unsupported factual claims.

## Part 19E — Image-question eligibility repair and 30-question pilot

Entry condition: Parts 19C and 18B/18C human review pass.

Before using the current multimodal generator path:

1. Replace `CURATED_VALID` as an eligibility shortcut with the explicit human
   state `APPROVED_INTERNAL_QUESTION_CANDIDATE`.
2. Require at least one `HUMAN_VERIFIED` image-to-text link.
3. Resolve the exact image occurrence tied to the selected evidence link; do
   not join arbitrary occurrences and links merely because they share an asset.
4. Use printed textbook pages for citations when available and preserve the
   physical PDF page separately.
5. Replace generic templated diagnoses/distractors and unsupported
   “pathognomonic” assertions with provider-generated structured candidates plus
   deterministic and human evaluation.
6. Store private object keys. Deliver images through short-lived authorized
   signed URLs; never depend on publicly accessible R2 URLs for restricted book
   images.
7. Ensure mobile rendering handles loading, failure, authorization expiry,
   accessibility, and screenshot/public-sharing policy.

Pilot size remains 30 human-reviewed image questions and counts inside the
900-question mature-bank target.

## Stop conditions

Stop without generation when any of the following is true:

- a book provenance manifest is missing or incomplete;
- a retrieval label or image evidence link is not human verified;
- a referenced chunk or image hash does not resolve;
- the retrieval acceptance gate fails;
- a restricted image would require a public URL;
- generation would copy source prose or infer an unverified diagnosis, stain,
  figure number, page, or caption;
- more than one third of a candidate batch fails review.

## Approval checklist

- [x] Complete Part 19A as schema/sync stabilization only.
- [ ] Complete Part 19B human work before paid embeddings.
- [ ] Approve Vertex AI cost immediately before Part 19C execution.
- [ ] Run the 50-question text pilot before any image-question pilot.
- [ ] Keep current image MCQ persistence disabled until Part 19E entry gates
      pass.
- [ ] Keep extracted textbook images private and internal-use only.
