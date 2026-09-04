# M19B Retrieval Human Review

This workflow converts the 55 automatically bootstrapped retrieval cases into
a human-reviewed benchmark. Importing a case does **not** verify it, and this
queue does not unblock embeddings until all M19B acceptance conditions pass.

## One-time setup

Use the local PostgreSQL database containing the synchronized three-book text
corpus.

```bash
.venv/bin/python -m alembic upgrade head
.venv/bin/python scripts/import_retrieval_review_dataset.py
.venv/bin/python scripts/import_retrieval_review_dataset.py --execute
```

The first importer invocation is a validation-only dry run. The execution is
idempotent for the same source hash and refuses to replace a changed dataset.
It also refuses any candidate chunk ID absent from the target database. All
inserted cases start as `AUTO_BOOTSTRAP_UNVERIFIED`.

If the corpus was re-imported with new chunk IDs, regenerate the bootstrap
against that exact corpus before human review begins. A changed bootstrap can
then be checked and replaced safely:

```bash
.venv/bin/python scripts/import_retrieval_review_dataset.py --replace-unreviewed
.venv/bin/python scripts/import_retrieval_review_dataset.py \
  --replace-unreviewed --execute
```

Replacement is refused as soon as any human review status, reviewer metadata,
revision, or audit event exists.

Start the existing backend and web applications, sign in as `REVIEWER`,
`ADMIN`, or `SUPER_ADMIN`, and open:

```text
http://localhost:3000/admin/retrieval-review
```

## Review each case

1. Read the retrieval prompt and every selected chunk in full.
2. Confirm that the domain matches the actual knowledge tested.
3. Retain only chunks that directly support the prompt. Page proximity or
   lexical overlap is not sufficient evidence.
4. Search the approved three-book corpus and add a better chunk when needed.
5. Use **Out-of-corpus control** only when none of the three books contains the
   answer. Out-of-corpus cases must have no selected chunks.
6. Add concise notes describing what was checked, then save the draft.
7. Read the saved evidence again, select the human-review attestation, and
   choose **Verify** or **Reject**.

Every save, approval, and rejection records the authenticated reviewer, time,
revision, notes, and before/after snapshots. A stale browser tab receives a
conflict instead of overwriting another review.

## Completion gate

The benchmark is promoted to `HUMAN_VERIFIED` only when:

- at least 50 cases exist;
- every case is `HUMAN_VERIFIED`;
- at least five domains are represented; and
- at least one verified out-of-corpus control exists.

Rejected and draft cases keep the benchmark in `HUMAN_REVIEW`. Separately, all
three M15 book provenance manifests must pass before M19B as a whole is
complete. Do not run paid embeddings while either gate is pending.

## Export the verified gold set

After the UI reports that every case is human verified, validate the database
export without writing a file:

```bash
.venv/bin/python scripts/export_retrieval_review_dataset.py
```

The exporter refuses to proceed unless every review and dataset-shape gate
passes. It also resolves every selected chunk against the approved three-book
corpus and emits source/page/content-hash receipts without exporting textbook
text. Then create the evaluator input:

```bash
.venv/bin/python scripts/export_retrieval_review_dataset.py --execute
.venv/bin/python scripts/evaluate_retrieval.py \
  --dataset data/evaluation/retrieval/verified/m16a_retrieval_eval_v1.jsonl \
  --validate-only
```

Use `--overwrite` only when you intentionally re-export after additional
audited human review. The output is deterministic while the reviewed database
state is unchanged.
