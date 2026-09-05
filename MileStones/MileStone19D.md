# Milestone 19D — Vertex Text-Only Question Calibration Pilot

> **Implementation status (2026-09-05):** pilot-safe service, dedicated runner,
> tests, and the 50-row blueprint are implemented locally. The project owner
> approved the blueprint on 2026-09-05; no Vertex generation request or
> candidate database write has run.

## Purpose

Build and run a controlled pilot of **exactly 50 text-only, evidence-backed
pathology MCQ candidates** for NEET-SS-style personal study. This is a
calibration exercise, not bulk question-bank production.

Run this milestone on the machine that has:

- access to the PostgreSQL database containing the three-book corpus;
- GCP Application Default Credentials and Vertex AI access;
- `REMOTE_DATABASE_URL` configured in the ignored `.env` file;
- the accepted Milestone 19C embedding run and retrieval evaluation report.

The pilot must use only the legitimately ingested three-book corpus. It must
not use external medical facts to fill evidence gaps, and it must not include
textbook images. Image questions remain Milestone 19E.

## Entry gate — close Milestone 19C first

The retrieval evaluation against embedding run
`cba90495-1c99-416d-989d-fdd246212218` is complete and accepted. The user
confirmed review of the 19 corrected evidence sets on 2026-09-05. Do not start
a second paid evaluation unless an accepted input or configuration changes.

The final versioned report must prove all of the following:

- the embedding run is `COMPLETED`, non-mock, and contains 2,845/2,845 vectors;
- the report uses the intended retrieval configuration hash (currently
  `7fdc2579c9a8bbe042d2585daeab764a6fd694c5a54f320ad78842a3f9ce64d6`, unless a
  documented retrieval change produces a new hash);
- the report dataset hash matches a fresh deterministic export of the final
  human-adjudicated gold set;
- overall Recall@5 is at least 90%;
- Recall@5 is at least 80% in every evaluated domain;
- all five out-of-corpus controls return `INSUFFICIENT_EVIDENCE`;
- citation/hash mismatches equal zero;
- `gate_passed` is true.

If any gate fails, preserve the failed report and repair the gold label or
retrieval configuration responsible for the failure. Reuse the existing
embedding run when its corpus, model, dimensions, and hashes remain valid; do
not re-embed merely to tune retrieval.

Accepted M19C identifiers:

- dataset SHA-256:
  `09b1c01e47a47837ebc989da834f426704ab2a79828d03e6e66769f7a18e2bd9`;
- embedding run ID: `cba90495-1c99-416d-989d-fdd246212218`;
- embedding configuration hash:
  `07cf615945e78cf9258d0c6788152ae9ad99e8dea93ecbde285261b1ca59bd6f`;
- retrieval configuration hash:
  `7fdc2579c9a8bbe042d2585daeab764a6fd694c5a54f320ad78842a3f9ce64d6`.

M19C closeout requirements:

1. Keep the corrected deterministic gold-set export and its SHA-256 committed.
2. Keep `docs/M19C_RETRIEVAL_ACCEPTANCE_REPORT.md` aligned with the accepted report,
   dataset hash, embedding run ID, retrieval configuration hash, and failed-case
   count.
3. Keep `ACTIVE_CONTEXT.md` aligned with M19C passed and M19D active.
4. Do not commit private extraction receipts, textbook text previews, or
   credentials. Remove generated scratch analysis containing source previews
   from the tracked handoff and ignore equivalent future scratch output.

## Hard safety and quality rules

1. Generate exactly one candidate per Vertex request. Do not ask the provider
   for batches of questions.
2. Stop after 50 candidates in this pilot. A retry for a failed request does not
   create a second candidate for the same blueprint row.
3. Retrieve evidence before generation. If retrieval refuses or evidence is
   insufficient, record the blueprint row as blocked; do not let the model
   answer from general knowledge.
4. The model must not invent source titles, chapters, pages, chunk IDs, hashes,
   or citations. Build citations server-side from immutable retrieval receipts.
5. Require evidence support for the correct answer, explanation, and every
   factual distractor rationale.
6. Do not copy or closely paraphrase substantial textbook prose. Reject
   candidates that overlap source wording beyond short necessary medical terms.
7. Quality and confidence values must be computed from stored evaluator
   signals. Never assign fixed `0.95`, `0.98`, or similar values.
8. Randomize option order reproducibly and store the seed and final answer
   mapping.
9. Vertex agreement, automated evaluation, or persistence is not approval.
   Only a human reviewer may move a candidate to `APPROVED`.
10. Store only internal evidence references. Do not expose copyrighted source
    text or create public source URLs.

## Phase 1 — Make the generation path pilot-safe

The current `scripts/generate_pathology_mcqs.py` path is not approved for this
pilot yet. It uses the legacy retrieval service, supports multi-question calls,
allows provider-created citations, and persists fixed confidence values.
Do **not** run it with `--count 50`.

Implement these prerequisites:

### 1A. Accepted hybrid retrieval

- Replace the legacy retrieval path in `QuestionGenerationService` with
  `HybridRetrievalService`.
- Pin every generation run to the accepted embedding run ID, retrieval
  configuration hash, gold-set dataset hash, and corpus manifest hash.
- Fail closed on `INSUFFICIENT_EVIDENCE`, missing chunks, source mismatch, or
  content-hash mismatch.
- Preserve an evidence packet for each candidate containing chunk ID, chunk
  content hash, source/document ID, edition, physical PDF page, printed page
  when known, chapter/section metadata, embedding run ID, and retrieval
  configuration hash.

### 1B. Vertex provider and audit receipt

- Keep the provider behind the existing replaceable generation interface.
- Add/configure a Vertex AI structured-output provider; do not hard-code Vertex
  business logic into the question service.
- Record provider, exact model/version, GCP project and region identifiers,
  prompt-template version, provider response ID when available, token usage,
  latency, generation timestamp, blueprint row ID, and evidence-packet hash.
- Never include an instruction asking the model to create page references.
  Supply evidence text for reasoning, but attach authoritative citation fields
  from the stored evidence receipts after schema validation.

### 1C. Candidate schema and evaluation

Require one structured single-best-answer item containing:

- stem;
- four unique options;
- one correct option;
- explanation of the correct answer;
- concise rationale for why each distractor is incorrect;
- evidence IDs mapped to the answer, explanation, and each factual distractor
  rationale;
- topic, subtopic, learning objective, difficulty, cognitive level, and
  question type.

The evaluator must record independent signals for:

- one unambiguous correct answer;
- answer/explanation consistency;
- claim-level evidence support;
- plausible, homogeneous, non-overlapping distractors;
- topic and learning-objective fit;
- exact and normalized duplicate detection;
- semantic near-duplicate detection against existing and pilot questions;
- copied/source-overlap risk;
- optional model agreement as a non-authoritative signal.

Do not treat explanation length, option count, evidence presence, or
PubMedBERT/Vertex agreement alone as proof of correctness.

### 1D. Reproducible pilot runner

Add a dedicated resumable runner, for example:

```bash
python scripts/run_m19d_text_pilot.py \
  --blueprint data/generation/blueprints/m19d_text_pilot_v1.json \
  --database-url-env REMOTE_DATABASE_URL \
  --embedding-run-id cba90495-1c99-416d-989d-fdd246212218 \
  --limit 50
```

Dry-run must be the default. `--execute` must be required for Vertex requests
and database writes. The runner must:

- use a stable pilot/cohort ID and one stable ID per blueprint row;
- resume without duplicating completed candidates;
- make only one candidate request at a time;
- cap successful persisted candidates at 50;
- store blocked and failed rows separately from successful candidates;
- never auto-approve a question;
- produce a metadata-only run report without source excerpts.

The exact command above is a required implementation target, not confirmation
that the script already exists.

## Phase 2 — Create and approve the 50-row blueprint

Create a versioned JSON blueprint with 10 learning objectives from each of the
five retrieval-evaluated domains:

| Domain | Rows | Cognitive target |
|---|---:|---|
| Diagnostic pathology | 10 | application/analysis |
| General pathology | 10 | understanding/application |
| Hematopathology | 10 | application/analysis |
| Neoplasia | 10 | application/analysis |
| Systemic pathology | 10 | application/analysis |

Each row must include a stable ID, domain, topic, subtopic, one assessable
learning objective, NEET-SS target, difficulty, cognitive level,
single-best-answer type, source requirements, and minimum evidence
requirements. Favor clinically or diagnostically meaningful application over
isolated trivia.

Before any paid call, a human reviewer must approve the complete blueprint.
Approval confirms scope and educational value only; it does not pre-approve
the resulting questions.

## Phase 3 — Test and dry-run

Add focused tests for:

- accepted-run/config/hash pinning;
- refusal and missing/hash-mismatched evidence fail-closed behavior;
- exactly one provider request per blueprint row;
- idempotent resume and the hard 50-candidate cap;
- structured-output rejection;
- claim-to-evidence mapping;
- deterministic option shuffling and answer remapping;
- exact, normalized, and semantic duplicate rejection;
- removal of fixed quality/confidence values;
- prohibition on automatic `APPROVED` status;
- absence of model-invented citation fields in persistence.

At minimum, run:

```bash
python -m pytest \
  tests/test_question_generation.py \
  tests/test_question_review_service.py \
  tests/test_hybrid_retrieval_postgres.py \
  tests/test_m19d_text_pilot.py \
  -q
```

Then run the pilot command without `--execute`. The dry run must print the
blueprint count and distribution, accepted retrieval identifiers, selected
Vertex model/location, maximum request count, and a current cost estimate. It
must not call Vertex or write candidates.

Stop and obtain the user's explicit approval of the displayed Vertex model,
project, region, request cap, and estimated cost.

Current draft preflight:

- blueprint:
  `data/generation/blueprints/m19d_text_pilot_v1.json`;
- blueprint SHA-256:
  `acaee58ff32987cde6ef583f2d0ecfda2bbf6c06159a2d6203d4b3a2c1425048`;
- approval: `raghul_project_owner` at `2026-09-05T08:51:00Z`;
- distribution: 10 rows in each domain, 43 hard/7 medium, and 30
  application/19 analysis/1 understanding;
- provider: Vertex AI `gemini-2.5-flash` in `us-central1`;
- generation mode: thinking disabled (`thinking_budget=0`);
- maximum calls: 50 query embeddings and 50 single-candidate generations;
- conservative token ceiling: 900,000 input and 110,000 output tokens;
- estimated ceiling using the 2026-09-05 public rates supplied to the runner:
  USD 0.201.

Pricing must be checked again immediately before execution. The dry run used
the official [Vertex AI generative AI pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)
and [Vertex AI thinking configuration](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking)
documentation.

## Phase 4 — Execute the pilot

After cost approval only:

```bash
python scripts/run_m19d_text_pilot.py \
  --blueprint data/generation/blueprints/m19d_text_pilot_v1.json \
  --database-url-env REMOTE_DATABASE_URL \
  --embedding-run-id cba90495-1c99-416d-989d-fdd246212218 \
  --limit 50 \
  --input-cost-per-million <CURRENT_INPUT_RATE> \
  --output-cost-per-million <CURRENT_OUTPUT_RATE> \
  --embedding-cost-per-thousand <CURRENT_EMBEDDING_RATE> \
  --approved-cost-cap <USER_APPROVED_USD_CAP> \
  --execute
```

Use a conservative request rate suitable for the configured Vertex quota.
Retry only transient provider failures with bounded backoff. Do not regenerate
a candidate merely because it failed medical or evidence evaluation; retain
the failure for calibration.

Automatically evaluated candidates may remain `GENERATED`, `AI_REVIEW`, or
move to `HUMAN_REVIEW` according to recorded results. None may become
`APPROVED` automatically.

Stop the run when:

- an accepted M19C identifier or evidence hash no longer matches;
- retrieval returns insufficient evidence for repeated rows;
- the provider returns malformed data repeatedly;
- a citation cannot be built from the retrieved evidence packet;
- more than one third of attempted candidates fail the quality gate;
- the request/cost cap would be exceeded.

## Phase 5 — Human review and calibration report

Expose all pilot candidates in the existing admin review UI and require the
reviewer to check:

- stem clarity and NEET-SS relevance;
- exactly one correct option;
- option and distractor quality;
- answer and explanation correctness;
- each claim against the displayed source evidence and provenance;
- copied-text risk;
- topic, difficulty, and cognitive-level labels.

Approval must use the existing guarded human-review transition and record
reviewer identity, timestamp, notes, and evidence verification status. Rejected
and corrected candidates remain in the audit trail.

Write a versioned, metadata-only calibration report containing:

- blueprint and pilot cohort hashes;
- Git commit;
- embedding run, retrieval configuration, dataset, and corpus hashes;
- provider/model/prompt versions;
- request, token, latency, and cost totals;
- generated, blocked, evaluator-pass, human-approved, corrected, and rejected
  counts;
- outcomes by domain, difficulty, and cognitive level;
- correct-option A/B/C/D distribution;
- evidence-source/page coverage;
- duplicate and copied-text findings;
- every failure category and the recommended change before scaling.

Do not include source excerpts, secrets, signed URLs, or copyrighted images in
the committed report.

## M19D acceptance gate

Milestone 19D passes only when all are true:

- M19C passed on the exact pinned retrieval artifacts used by generation;
- the approved blueprint has exactly 50 rows, 10 per domain;
- the pilot made at most one successful candidate per row and persisted no
  more than 50 candidates;
- all persisted candidates have complete provider, blueprint, retrieval, and
  evidence receipts;
- every human-approved answer, explanation, and factual distractor rationale is
  supported by verified evidence;
- invented citations and evidence hash mismatches equal zero;
- exact/normalized duplicates equal zero and flagged semantic similarities
  have human decisions;
- no candidate was automatically approved;
- all 50 blueprint rows have a final pilot outcome and all generated candidates
  have a human decision;
- fewer than one third of attempted candidates failed review;
- the calibration report is complete and contains no private source content.

Do not scale question generation and do not begin the Milestone 19E image pilot
until this gate is reviewed and accepted.

## Required handoff

Return these items to the main development machine:

1. accepted M19C report identifiers and hashes;
2. approved 50-row blueprint and SHA-256;
3. pilot/cohort ID and metadata-only run report;
4. provider/model/prompt version and actual Vertex cost/usage totals;
5. question candidate IDs and their final review states;
6. failed/blocked blueprint row IDs with reasons;
7. exact Git commit and test output.
