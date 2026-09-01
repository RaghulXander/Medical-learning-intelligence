# Milestone 18 — AI agent handoff for the image-extraction machine

This document is the starting context for the AI coding agent running on the
machine that contains the approximately 3,000 already-extracted book images.

Read these files completely before changing code or data:

1. `AGENTS.md`
2. `MileStones/MileStone15.md`
3. `MileStones/MileStone16.md`
4. `MileStones/MileStone18.md`
5. `docs/M15_TWO_MACHINE_BOOK_RUNBOOK.md`
6. `docs/M16A_RETRIEVAL_RUNBOOK.md`
7. this handoff document

## Objective on that machine

Implement **Milestone 18A only** unless the user separately approves later
parts:

1. discover the extracted-image directory and extraction script;
2. inspect the real file and metadata formats;
3. create an immutable portable image inventory;
4. measure image dimensions and cleanup signals;
5. identify exact duplicates and propose near-duplicate groups;
6. assign non-destructive triage candidates;
7. generate private contact sheets;
8. select a stratified 300-image human-review calibration set.

Do not generate image MCQs during 18A.

## Important existing context

- The text corpus contains 1,719 selected chunks from two books:
  `robbins_review` (496) and `robbins_pathologic_basis_11th` (1,223).
- The image extraction reportedly produced about 3,000 files, with an estimated
  30–40% consisting of small blocks or unwanted fragments. Treat this percentage
  as an unverified observation, not a cleanup quota.
- Images were extracted by a Python script. Its path, output naming convention,
  page mapping, and manifest format must be inspected rather than assumed.
- The source PDFs are not required for 18A. The extracted files and available
  extraction metadata are the input.
- If physical page/source metadata is missing, cleanup may continue, but the
  affected images must remain `PROVENANCE_UNRESOLVED` and cannot be used for
  question generation.
- Existing text chunks in PostgreSQL can later provide page-adjacent evidence in
  18C without reopening the PDFs.

## Existing code that must not be trusted as real evidence

The repository contains a prototype under:

```text
backend/services/multimodal/
backend/api/routes/multimodal.py
tests/test_multimodal_engine.py
```

`image_catalog.py` currently seeds hard-coded example image paths, diagnoses,
captions, and textbook citations. These are demo/test fixtures. Do not import
them into the real catalog, do not copy their citations, and do not use them as
medical ground truth.

The prototype generator also creates generic hard-coded distractors. It is not
the Milestone 18 generation design and must not be scaled to the extracted
images.

## Mandatory discovery report before implementation

Inspect first and produce a short report containing:

- absolute image root path;
- extraction script path and relevant commit/version;
- number of files by extension;
- total bytes;
- readable versus corrupt files;
- dimension, area, aspect-ratio, and file-size distributions;
- count below several observed size bands—do not choose a rejection threshold
  yet;
- whether alpha/transparency is present;
- exact SHA-256 duplicate count and groups;
- available filename metadata;
- available JSON/JSONL/CSV/database manifests and their fields;
- whether source short name, PDF page, printed page, figure label, caption, and
  bounding box are preserved;
- a private contact sheet of a small representative sample;
- any dirty Git changes or private data paths that must be preserved.

Do not move, rename, delete, resize, or rewrite images while producing this
report.

## Raw-data and Git boundaries

1. Treat the extracted-image directory as immutable raw input.
2. Never recursively delete or overwrite the input directory.
3. Derived thumbnails, contact sheets, manifests, and reports go into a separate
   ignored/private processed directory.
4. Do not commit textbook images, thumbnails, contact sheets, OCR captions,
   private bucket URLs, or source PDFs.
5. It is acceptable to commit schemas, scripts, tests, aggregate metrics, and
   synthetic fixtures containing no copyrighted book content.
6. Use stable relative paths in portable manifests; do not persist Windows drive
   letters or machine-specific absolute paths as canonical identifiers.
7. Store SHA-256 and extraction IDs so a moved bundle remains verifiable.
8. Before any Git commit, verify `.env`, images, manifests containing captions,
   and private receipts are ignored and untracked.

## Portable bundle expectations

If the existing extraction output is not portable, create a manifest around it
without copying or modifying the binaries initially:

```text
image_handoff/
  bundle_manifest.json
  extraction_manifest.jsonl
  checksums.sha256
  assets/  # may be a private copied bundle or an external immutable root
```

Each image record should preserve every available source field and add:

- stable `extraction_id`;
- relative path;
- SHA-256;
- decoded-pixel hash;
- width/height/format/color mode;
- extractor name/version;
- inventory run ID;
- provenance status;
- validation errors.

Never infer a page, figure number, stain, diagnosis, or caption when it was not
provided by the extractor or verified by a reviewer.

## Cleanup strategy

Cleanup is a classification and review workflow, not file deletion.

### Safe automatic facts

Collect deterministic signals such as:

- decoder success;
- width, height, area, aspect ratio, format, and bytes;
- alpha/transparent fraction;
- blank/near-blank statistics;
- entropy and edge density;
- connected components;
- OCR/text-area estimate;
- exact SHA-256 duplicate;
- decoded-pixel duplicate;
- perceptual-hash distance.

### Candidate decisions only

Automated logic may emit:

- `AUTO_KEEP_CANDIDATE`
- `AUTO_REJECT_CANDIDATE`
- `HUMAN_REVIEW_REQUIRED`
- `QUARANTINED_CORRUPT`

It must not emit final human approval or permanently delete a file.

Tiny publisher marks, rules, blank crops, navigation icons, and repeated
decorations may become reject candidates. Small IHC panels, cytology cells,
insets, legends, scale bars, and components of compound figures require review.
Image dimensions alone are not an adequate rejection rule.

## Duplicate and crop rules

Keep these relationships distinct:

- byte-identical file;
- pixel-identical image with different encoding;
- perceptual near-duplicate;
- crop of another image;
- child panel of a compound figure;
- the same image reused on different pages.

Canonicalizing a binary must not remove its page/source occurrences. Do not
collapse possible crops or panels based only on perceptual-hash similarity.

## Human calibration set

Select at least 300 images stratified by:

- both books;
- page ranges;
- dimensions and aspect ratios;
- file-size bands;
- entropy/blank scores;
- proposed utility class;
- exact/near duplicates;
- likely useful pathology images;
- likely unwanted fragments;
- ambiguous crops and multi-panel figures.

Do not select only random files; rare useful small images must be represented.
Keep the human labels separate from the rule-development subset so cleanup
metrics can be measured on held-out examples.

Required acceptance targets are defined in `MileStones/MileStone18.md`, including
at least 99% recall for useful images and at least 98% precision for automatic
reject candidates. If the gate fails, widen human review rather than increasing
automatic deletion.

## Contact-sheet requirements

Contact sheets are private review artifacts. Each tile should show:

- image thumbnail without distortion;
- stable image ID;
- width × height;
- source short name and physical page when known;
- proposed utility class;
- candidate status and confidence band;
- duplicate/parent group indicator.

Do not render long textbook captions. Ensure a reviewer can open the original
asset from its ID without exposing it through a public URL.

## No-PDF provenance linkage for later 18C

After 18B approval, link images using the extraction manifest and PostgreSQL:

```text
source_short_name + source_document_hash + pdf_page
    -> SourceDocument
    -> same-page/adjacent DocumentChunk records
    -> candidate ImageTextEvidenceLink
    -> human verification
```

Filename or visual similarity alone cannot verify provenance. Candidate links
remain `AI_SUGGESTED` until a human confirms the image, page, and associated
text/caption relationship.

## Question-generation boundary

Do not begin image question generation merely because cleanup finishes. An
eligible asset must satisfy all Milestone 18D gates, including:

- human approval for internal question use;
- verified binary hash and private storage object;
- verified source/page relationship;
- verified medical metadata used in the question;
- verified links to supporting text chunks;
- passed Milestone 16 retrieval gate.

The first image-question pilot is 30 questions and counts inside the 900-question
mature-bank target. It is not 30 questions per image or an additional bank.

## Suggested implementation order

1. Add ignored/private input and output path configuration.
2. Define versioned JSON schemas for bundle, inventory record, triage result,
   duplicate relationship, and human review.
3. Build a read-only inventory CLI with dry-run behavior by default.
4. Add deterministic unit tests using synthetic images only.
5. Run inventory against the real private directory.
6. Produce aggregate discovery report and sample contact sheets.
7. Ask for approval of the proposed triage thresholds.
8. Generate candidate decisions without moving/deleting files.
9. Build the 300-image review set and measure the held-out cleanup gate.
10. Stop after 18A and request approval before database catalog work.

## Required handoff at the end of 18A

Report:

- input bundle hash and inventory run ID;
- total, readable, corrupt, unique, exact-duplicate, and near-duplicate counts;
- proposed keep/reject/review counts, clearly labelled as candidates;
- size/statistics distributions and chosen threshold rationale;
- human sample composition;
- held-out metrics when labels are complete;
- paths to private manifests/contact sheets;
- tests executed;
- unresolved provenance count;
- explicit confirmation that no raw image was modified or deleted;
- explicit confirmation that no image MCQ was generated.

## Stop conditions

Stop and ask the user rather than guessing when:

- the image root or extraction manifest is ambiguous;
- multiple directories appear to contain different extraction runs;
- filenames conflict with manifest page/source fields;
- source rights are not confirmed for private processing;
- a proposed operation would move, delete, overwrite, publicly upload, or commit
  book images;
- the agent would need to infer diagnoses, captions, pages, or citations;
- the requested work expands beyond Milestone 18A.
