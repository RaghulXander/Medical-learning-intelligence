# M19B Retrieval Review Audit — 2026-09-04

## Remote benchmark state

Read-only audit of `m16a-retrieval-v1`:

- 55 total cases;
- 48 `HUMAN_REVIEW` drafts;
- 2 `HUMAN_VERIFIED` cases;
- 5 `REJECTED` cases;
- 55/55 have non-empty review notes and reviewer identity;
- 58 draft-save events, 2 approval events, and 5 rejection events;
- 48 distinct selected evidence chunks resolve successfully;
- no selected chunk ID is missing.

The five rejected cases are the intended out-of-corpus controls. Their notes
correctly identify them as outside pathology, but a correct negative control
must be saved as `out_of_corpus=true` with no chunks and then **verified**.
`REJECTED` means the benchmark item itself is defective and prevents benchmark
completion.

The two currently verified cases (`diag-001` and `diag-007`) have notes stating
that their selected evidence does not support the prompt. They must be reopened
and corrected; their current verification must not be used as a gold label.

### Authorized follow-up correction

After the initial read-only audit, the reviewer authorized the following remote
changes through the normal revisioned review service:

- `ctrl-001` through `ctrl-005` were verified as valid out-of-corpus controls,
  each with explicit notes and empty evidence;
- `diag-001` and `diag-007` were reopened to `HUMAN_REVIEW`, preserving their
  existing prompts, evidence selections, and notes.

The post-change state is 5 `HUMAN_VERIFIED` out-of-corpus controls and 50
`HUMAN_REVIEW` in-corpus cases, with zero rejected cases and zero missing notes.
The benchmark remains `HUMAN_REVIEW` as intended.

## Evidence-quality findings

The review notes are substantive, but completing a note is not equivalent to
confirming the selected chunk. A conservative keyword grouping of the 50
in-corpus notes found:

| Preliminary group | Count |
|---|---:|
| Supported candidate | 15 |
| Partial or incomplete evidence | 16 |
| Unsupported, mismatched, or wrong-chapter evidence | 16 |
| Requires manual adjudication | 3 |

This grouping is a navigation aid, not a medical decision. The reviewer must
correct the selected evidence and explicitly verify every case.

Reported extraction issues overlap:

- table/table-layout concerns were mentioned in 19 notes;
- evidence mismatch was explicitly mentioned in at least 6 notes;
- source shorthand/reference-code noise was mentioned in 3 notes;
- running header/footer contamination was mentioned in 1 note;
- other unwanted text was mentioned in 1 note.

An automated scan of the 48 selected chunks found 16 table-like chunks and 3
chunks containing book reference shorthand. It found no cryptographic hashes
inside evidence text. The UUID and SHA displayed by the admin UI are application
integrity receipts and are not part of the evidence content supplied to a
generator.

Structured table metadata survived ingestion in 204 of the 2,845 corpus chunks;
5 currently selected evidence chunks contain such tables. The review API/UI now
exposes those five tables as grids. Missing or malformed tables still require a
new, versioned extraction/normalization run.

## Required remediation before M19C

1. Reopen `diag-001` and `diag-007`; replace or add directly supporting chunks,
   or revise the prompts to match available evidence.
2. Treat the five `ctrl-*` cases as verified out-of-corpus controls when their
   empty evidence labels are correct; do not reject them merely for being
   outside pathology.
3. For each partial/unsupported case, replace evidence, add complementary
   chunks, narrow the prompt, or mark it genuinely out of corpus.
4. Create a new immutable corpus version for header/footer suppression,
   reference-code separation, table reconstruction, reading-order repair, and
   figure/caption linkage. Do not silently edit existing chunk content/hashes.
5. Remap affected benchmark cases to the new chunk IDs and re-attest them.
6. Produce three complete `PASSED` M15 provenance manifests. The repository
   currently contains only an incomplete Robbins Review manifest, so M19B is
   still blocked independently of the 55-case review.
7. Export the verified benchmark and run validation. Only then request cost
   approval and begin the real embedding/retrieval evaluation in M19C.

## Image readiness

Remote catalog state:

- 2,165 private image assets;
- 2,165 assets have private storage references;
- 3,053 image-to-text links;
- all 3,053 links are `AI_SUGGESTED`;
- zero links are `HUMAN_VERIFIED`.

Images therefore cannot yet enter question generation. The next image slice is
an admin review workflow that approves/rejects utility, verifies source/page and
text linkage, and records eligibility as
`APPROVED_INTERNAL_QUESTION_CANDIDATE`. After M19C passes, the first pilot is 30
image-grounded questions. Each question uses the approved image as the visible
stimulus and verified text chunks as support for the correct answer and
explanation. Restricted textbook images remain private and cannot be posted to
Instagram, Facebook, or other public channels.
