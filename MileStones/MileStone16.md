# Milestone 16 — Evidence-Bound Learning Content

> **Status: PART 16A APPROVED / IN PROGRESS — paid embeddings and generation remain gated**

## Approved scope

**Milestone 16A only** is the approved implementation slice:

1. promote the three-book text corpus into local PostgreSQL;
2. build a versioned pgvector retrieval index;
3. measure retrieval on a human-authored evaluation set;
4. generate a small evidence-bound MCQ pilot;
5. send every candidate through automated checks and human review.

Short notes and rights-safe social cards are specified below as Parts B and C,
but they do not start until Part A passes.

## Why this sequence

The product goal is accuracy, not question volume. Generation must therefore be
downstream of measurable retrieval quality. A fluent question is not acceptable
unless its answer, explanation, and relevant distractor rationales can be traced
to the supplied book evidence.

Milestone 16 does not fine-tune a model. With the versioned evidence corpus, retrieval,
structured generation, evaluation, and human review are the first useful quality
controls. Fine-tuning is reconsidered only after reviewed failures produce a
meaningful training set.

## Question-bank sizing decision

The number of book pages or chunks does **not** determine the number of
questions. Robbins Review and Robbins Pathologic Basis overlap substantially;
they are complementary evidence/style sources, not two independent quotas.

The latest published NEET-SS scheme available while drafting this milestone is
the NEET-SS 2025 bulletin. It defines a 150-question paper in 150 minutes with
`+4/-1` marking. For the Pathology Group, questions are at the PG exit level of
the Pathology feeder specialty and may cover its general/basic and subspecialty
components. Revalidate this assumption when the NEET-SS 2026 bulletin is
published.

### Proposed size from these books

| Bank stage | Approved unique questions | Purpose |
|---|---:|---|
| Calibration pilot | 50 | Validate retrieval, prompts, evaluator, and human-review rubric |
| First usable bank | 300 | Topic tests plus two exam-equivalents |
| Expanded bank | 600 | Broad PG-exit Pathology coverage and repeated practice |
| Target mature bank | **900** | Six 150-question exam-equivalents; 600 practice + 300 initially reserved for mocks |
| Hard ceiling | **1,200** | Allowed only when a reviewed blueprint identifies genuine uncovered objectives |

The expected final target is therefore **about 900 human-approved questions**,
not 5,000–7,000. Generation may create at most 1,350 candidates while building
the 900-question bank. If more than one third of a batch is rejected, stop and
fix retrieval, prompts, or the blueprint instead of generating additional bulk.
Rejected candidates remain audit/evaluation data and do not count as bank size.

### Objective-based quota

Before scaling beyond 50, create a reviewed learning-objective matrix. Assign a
maximum quota per objective rather than per page:

- Tier A — high-yield/integrative objective: up to 4 distinct questions;
- Tier B — standard examinable objective: up to 2 questions;
- Tier C — narrow/low-yield but valid objective: 1 question;
- insufficient or duplicate evidence: 0 questions.

Four questions for one Tier A objective must test genuinely different skills,
for example recognition, mechanism, application, and interpretation. Wording
variants of the same fact count as duplicates, not additional questions.

### Proposed calibration mix for the 900-question target

The exact organ/topic allocation is approved only after the objective inventory;
NBEMS does not publish a dependable topic-weight table in the cited bulletin.
The initial cognitive and difficulty targets are:

| Dimension | Proposed mix |
|---|---|
| Cognitive level | 25% recall, 25% understanding, 40% application, 10% analysis |
| Difficulty | 15% easy, 50% medium, 35% hard |
| Format | 40% direct SBA, 35% clinicopathologic vignette, 25% integrated molecular/IHC/interpretation |

Image-dependent questions are excluded from the initial text-only pilot until
Milestone 18 produces private, reviewed, provenance-linked image assets. Its
30-question image pilot counts within the mature 900-question target. Robbins
Review may inform exam style and topic gaps,
but existing copyrighted questions must not be copied or lightly paraphrased.

## Current baseline

- The verified local promotion contains 2,845 unique text chunks across three
  books: `robbins_review` (496), `robbins_pathologic_basis_11th` (1,223), and
  `sternberg_review_2nd` (1,126). The sorted content-hash manifest SHA-256 is
  `88424b7e4561348083d43f1947b14f732bc225ff8e08b23071737f852975d787`.
- A verified local SQLite copy exists as a transfer/recovery artifact.
- Robbins Review contributes 496 chunks covering physical PDF pages 1–496.
- Robbins Pathologic Basis 11th contributes 1,223 chunks across physical PDF
  pages 1–1,227. Pages 4, 6, 16, and 1,226 have no stored text and require a
  visual blank-page confirmation or explicit page receipt.
- No real embeddings are stored.
- The configured local application database is PostgreSQL, so the SQLite corpus
  must be promoted before application work begins.
- Existing generation and retrieval code is a prototype. It uses JSON vectors,
  Python-side full-corpus scoring, silent mock fallbacks, shallow grounding
  checks, and uncalibrated confidence values. It is not an acceptance baseline.
- Processor version/run metadata is absent from the database chunks. Milestone
  15 provenance sign-off remains a release gate even if Milestone 16 code is
  developed behind a disabled feature flag.

### Implementation progress — 2026-09-01

- 16A.0 complete: the two selected sources, two source documents, and 1,719
  chunks were promoted into local PostgreSQL and independently hash-verified;
  unrelated seed data was preserved.
- 16A.1 complete: Alembic revision `20260901_0005` adds immutable embedding runs,
  `vector(768)` chunk vectors, and an HNSW cosine index. The configured provider
  fails closed and records document/query task types.
- 16A.2 framework complete: PostgreSQL dense + lexical retrieval, deterministic
  weighted fusion, page diversity, thresholds, and immutable evidence receipts
  pass a rollback-only PostgreSQL integration test.
- 16A.3 tooling complete, benchmark data pending: a strict JSONL loader and gate
  report calculate Recall@1/5/10, MRR, refusal rate, per-domain results, and
  citation integrity. The 50–75 cases still require human-authored prompts and
  human-verified gold chunk IDs.
- Real embeddings remain blocked until the four no-text page receipts are
  confirmed and both selected documents have matching, fully passed M15
  provenance manifests.
- No real/mock embedding run or MCQ candidate has been persisted.
- Machine-to-machine execution commands are documented in
  [`docs/M16A_RETRIEVAL_RUNBOOK.md`](../docs/M16A_RETRIEVAL_RUNBOOK.md).

## Non-negotiable invariants

1. Remote/production data is read-only during local promotion.
2. PostgreSQL plus pgvector is the local and deployed system of record.
3. Mock embeddings, mock model answers, and simulator scores are test fixtures
   only and can never be mixed with real evaluation results.
4. Provider failures fail closed. They never silently create mock medical data.
5. Every generated factual claim must name one or more evidence chunk IDs.
6. A citation is valid only when the referenced source, edition, chunk hash, and
   page resolve in the database.
7. Retrieval failure returns `INSUFFICIENT_EVIDENCE`; it does not broaden the
   prompt or invite unsupported completion.
8. PubMedBERT is an optional independent signal only when the real model is
   loaded. A deterministic simulator contributes no quality score.
9. Generated questions remain `GENERATED`/`AI_REVIEW`/`HUMAN_REVIEW` candidates.
   Only a human can approve them for personal exams.
10. Public notes/cards must be original paraphrases. Textbook prose and figures
    are not republished unless separate rights permit it.

## Part 16A — Retrieval and MCQ pilot

### A0. Database promotion and safety gate

1. Confirm local PostgreSQL is reachable at the configured `DATABASE_URL`.
2. Add a reusable SQLite-to-PostgreSQL promotion command for only:
   `Source -> SourceDocument -> DocumentChunk`.
3. Preserve IDs, source metadata, physical/printed page fields, content hashes,
   and chunk metadata; omit remote file-system paths.
4. Make the import idempotent and transactional. Refuse conflicting hashes.
5. Compare per-book source/document/chunk/word/hash counts between SQLite and
   PostgreSQL after import.
6. Record explicit receipts for the four no-text Robbins 11th pages before the
   corpus can be labelled complete.
7. Restore `.env` secret hygiene before any commit: `.env` must not be tracked.

**Original two-book A0 receipt:** PostgreSQL contained exactly 2 selected
sources, 2 source documents, and 1,719 unique chunks with zero empty content or
hash conflicts.

**Expanded three-book gate (2026-09-02):** the requested scope contains exactly
three source identities and one source document per book; remote, transfer, and
local PostgreSQL per-book chunk/word/content-hash manifests must match. The
verified runtime receipt—not a hard-coded count—is authoritative after adding
`sternberg_review_2nd`.

### A1. Versioned embedding schema

Add an Alembic migration for a replaceable embedding index rather than making a
single provider permanent in `document_chunks`.

Conceptual model:

```text
EmbeddingRun
  id, provider, model_id, model_version, dimension, document_task_type,
  query_task_type, chunking_version, status, started_at, completed_at,
  input_count, embedded_count, failed_count, configuration_hash

DocumentChunkEmbedding
  id, run_id, chunk_id, content_hash, embedding vector(768), created_at
  UNIQUE(run_id, chunk_id)
```

Use a pgvector cosine index. Keep the original text and hash in
`DocumentChunk`; an embedding run is disposable and reproducible.

Proposed first provider:

- Vertex AI `gemini-embedding-001`;
- output dimensionality: 768 for the initial pgvector index;
- corpus task type: `RETRIEVAL_DOCUMENT`;
- query task type: `RETRIEVAL_QUERY`;
- automatic truncation disabled so oversized chunks fail visibly;
- provider/model/dimension/task types recorded with every run.

The model ID remains configuration, not business logic. A local open embedding
model can be evaluated later through the same interface.

### A2. Retrieval service

Replace full-corpus Python scoring with database retrieval:

1. dense pgvector cosine search;
2. PostgreSQL lexical search for exact medical terms, gene names, stains, and
   acronyms;
3. deterministic hybrid fusion;
4. optional filters for source, edition, chapter, and physical page range;
5. diversity control so one repetitive page does not occupy every result;
6. evidence receipts containing chunk ID, content hash, source, edition,
   physical page, printed page, section, score, embedding run, and retrieval
   configuration.

Do not redesign chunking before measurement. Evaluate the current page-level
chunks first. Introduce smaller child passages only if the retrieval benchmark
shows a measurable need; child passages must retain their parent page receipt.

### A3. Retrieval evaluation set

Create 50–75 human-authored prompts across at least five domains:

- general pathology;
- neoplasia/molecular pathology;
- hematopathology;
- systemic/organ pathology;
- question-oriented review-book facts.

For every prompt, a reviewer records relevant chunk/page IDs or marks it
out-of-corpus. The evaluation command stores the dataset version, embedding run,
retrieval configuration, Recall@1/5/10, MRR, unsupported-query refusal rate, and
per-topic failures.

**A3 gate:**

- Recall@5 at least 90% overall;
- no topic below 80% Recall@5;
- 100% of out-of-corpus prompts return `INSUFFICIENT_EVIDENCE` in the generation
  entry gate;
- every returned citation resolves and its content hash matches.

If this gate fails, improve retrieval and repeat. Do not generate pilot MCQs.

### A4. Structured MCQ blueprint and generation

Pilot scope: 50 questions, initially 10 per evaluated domain. Generate one
candidate per request; do not bulk-generate hundreds.

Blueprint fields:

```json
{
  "topic": "...",
  "subtopic": "...",
  "learning_objective": "...",
  "target_exam": "NEET_SS",
  "difficulty": "hard",
  "cognitive_level": "application",
  "question_type": "single_best_answer",
  "allowed_source_ids": ["..."],
  "minimum_evidence_items": 2
}
```

The generator receives only the blueprint and retrieved evidence packet. Use a
provider-independent interface and Vertex AI structured JSON output. Record the
provider, requested model ID, returned model version, prompt version, response
ID, token usage, seed/configuration, evidence packet hash, and latency.

The response schema must include:

- stem and four options;
- one declared correct option;
- explanation and option rationales;
- learning objective/difficulty/cognitive level;
- evidence chunk IDs for the stem, correct answer, explanation, and each factual
  distractor rationale;
- an explicit `insufficient_evidence` result.

No model ID is approved permanently in this draft. At implementation time,
compare the currently supported GCP models on a 10-question calibration set and
select the best accuracy/cost trade-off. The chosen ID stays configurable.

### A5. Evaluator and failure policy

Mandatory deterministic checks:

- schema and option-key consistency;
- exactly one correct option;
- citation existence, source allowance, and content-hash match;
- claim-to-evidence coverage;
- no citations not present in the supplied evidence packet;
- exact and normalized duplicate detection against old and generated MCQs;
- near-duplicate detection with a separately versioned similarity threshold;
- answer leakage, giveaway wording, and malformed distractors;
- prohibited long verbatim overlap with source text;
- unsupported/out-of-scope claim detection.

Model-assisted checks run in a separate evaluator call using the same evidence,
but evaluator agreement is not ground truth. PubMedBERT disagreement is stored
as a review signal only when the real service reports a loaded model.

Any mandatory failure produces `AI_REVIEW` or `REJECTED`; it never produces
`APPROVED`. Scores must be derived from recorded signals—no hardcoded 0.95/0.98
confidence values.

### A6. Human review pilot

The reviewer sees:

- question, answer, explanation, and distractor rationales;
- evidence excerpts beside exact source/page receipts;
- automated findings and model identities;
- duplicate candidates;
- approve, edit, reject, or request-regeneration actions with notes.

Review every pilot question. Accepted content is educational exam preparation,
not clinical advice.

**Part 16A acceptance criteria:**

- retrieval A3 gate passes;
- 50 candidates generated with complete immutable run metadata;
- 100% of accepted questions have resolvable citations;
- 100% of accepted answers and explanations are judged supported by cited text;
- zero unsupported factual claims in the accepted set;
- zero invented citations;
- at least 90% of accepted distractors are judged plausible and unambiguous;
- no candidate is automatically approved;
- the accepted set is reproducibly exportable for a personal mock exam;
- failures and human edits are stored as future evaluation/training data.

The first pass is successful even if many candidates are rejected. Rejection
data is useful; hiding failure behind inflated scores is not.

## Part 16B — Evidence-bound short notes (planned, separately approved)

Entry condition: Part 16A passes.

Pilot 10 short-note packs. Each note has a learning objective, key points,
comparison table when supported, common pitfalls, self-test questions, and a
claim-to-evidence map. Every factual bullet must resolve to book evidence.

PDF generation renders original summaries, not copied textbook layouts. Verify
page layout visually and include an internal evidence appendix. Acceptance
requires human confirmation of every factual claim and zero invented citations.

## Part 16C — Rights-safe social study cards (planned, separately approved)

Entry condition: Part 16B passes.

Generate text-first Instagram/Facebook cards from approved notes using original
templates and paraphrased educational summaries. Do not use extracted textbook
figures, screenshots, or substantial prose unless separate publication rights
are documented. Each card receives human content and rights review before export.

## Explicitly out of scope

- automatic publishing to social networks;
- diagnostic interpretation of user pathology images;
- seeding nonexistent images or unverified textbook figure citations;
- fine-tuning before a reviewed failure dataset exists;
- autonomous medical/clinical recommendations;
- bulk generation before the 50-question pilot is accepted.

## Proposed implementation sequence

| Step | Deliverable | Approval boundary |
|---|---|---|
| 16A.0 | SQLite-to-local-PostgreSQL promotion and count/hash receipt | Engineering check |
| 16A.1 | Alembic pgvector embedding schema and fail-closed provider | Engineering check |
| 16A.2 | Hybrid retrieval and evidence receipts | Engineering check |
| 16A.3 | Human retrieval benchmark and report | Must pass before generation |
| 16A.4 | Structured generator and immutable generation run | 10-question calibration |
| 16A.5 | Evaluator corrections and editorial UI/API | Must pass before 50-question pilot |
| 16A.6 | 50-question reviewed pilot | Human sign-off |
| 16B | Short-note/PDF pilot | Separate approval |
| 16C | Rights-safe social-card pilot | Separate approval |

## Approval checklist

Please approve or revise these decisions before implementation:

- [x] Start only Part 16A now; defer notes and social cards.
- [x] Use local PostgreSQL as the working database and keep SQLite as a private
      transfer/recovery artifact.
- [x] Use a versioned `vector(768)` embedding table with Vertex AI
      `gemini-embedding-001` as the first measured provider.
- [x] Require the retrieval gate before the first real generated question.
- [x] Limit the first reviewed MCQ pilot to 50 candidates across five domains.
- [x] Keep all generated content non-production until human approval.
- [x] Treat M15 provenance/blank-page confirmation as a release gate rather
      than silently declaring the imported corpus fully verified.

## Current GCP references

- [NBEMS NEET-SS 2025 Information Bulletin](https://nbe.edu.in/IB/NEET-SS%202025%20information%20bulletin.pdf)
- [Vertex AI text embeddings](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-text-embeddings)
- [Vertex AI structured JSON output](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/samples/generativeaionvertexai-gemini-controlled-generation-response-schema-2)
- [Vertex AI model lifecycle](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions)
- [Vertex AI pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)
