# Milestone 18 — Portable Pathology Image Curation and Image-Grounded Questions

> **Status: DRAFT FOR APPROVAL — image inventory/cleanup can start independently of the PDF machine**

> **Other-machine agent handoff:** Read
> [`docs/M18_IMAGE_CURRATION_HANDOFF.md`](../docs/M18_IMAGE_CURRATION_HANDOFF.md)
> before inspecting or processing the extracted image directory.

## Purpose

Curate approximately 3,000 images already extracted from the two legitimately
obtained books, remove or quarantine unusable fragments, and produce a private,
reviewed image catalog that can later support evidence-bound NEET-SS pathology
questions.

This milestone starts from an **extracted-image handoff bundle**, not from the
source PDFs. The machine doing curation does not need the PDFs, Document AI, or
the original extraction program.

The cleanup goal is not to maximize the number of retained images. It is to
retain a smaller set of useful, traceable pathology visuals without deleting a
valid microscopic panel merely because it is small.

## Scope decision

Milestone 18 is divided into independently gated parts:

| Part | Deliverable | Dependency |
|---|---|---|
| 18A | Portable image inventory, duplicate detection, and automated triage | Extracted image bundle only |
| 18B | Human cleanup review and private approved image catalog | 18A |
| 18C | Link approved images to existing PostgreSQL source/page/text evidence | 18B and the already-promoted text database; no PDF required |
| 18D | Small image-grounded MCQ pilot | 18C plus the Milestone 16 retrieval gate |

Parts 18A–18C can run in parallel with the remaining text retrieval work. Part
18D cannot bypass Milestone 16 accuracy requirements.

## Portable handoff contract

Copy the following private bundle from the extraction machine:

```text
image_handoff/
  bundle_manifest.json
  assets/
    <image files>
  extraction_manifest.jsonl
  checksums.sha256
```

The bundle must remain outside Git. It may be transferred through encrypted
local storage or a private GCS bucket owned by the project account.

### Minimum per-image extraction record

```json
{
  "extraction_id": "stable-id",
  "relative_path": "assets/...png",
  "source_short_name": "robbins_pathologic_basis_11th",
  "source_document_hash": "sha256-if-known",
  "pdf_page": 412,
  "textbook_page": 396,
  "figure_label": "Fig. 10.4",
  "caption_text": null,
  "bounding_box": null,
  "extractor_name": "python-script-name",
  "extractor_version": "version-or-commit",
  "extracted_at": "ISO-8601 timestamp"
}
```

`pdf_page`, printed page, figure label, caption, and bounding box may be null when
the current extractor did not preserve them. Missing provenance must be recorded
as `UNRESOLVED`; it must never be guessed from image content.

If no extraction manifest currently exists, 18A first creates one using stable
file hashes and the available directory/file naming convention. This permits
cleanup, but provenance-unresolved images cannot enter question generation.

## Non-negotiable rules

1. Raw extracted images are immutable. Cleanup changes status; it does not
   delete or overwrite the source files.
2. Every asset receives SHA-256, dimensions, format, byte size, and an inventory
   receipt before classification.
3. Small dimensions alone never cause automatic permanent rejection.
4. Exact duplicates may share one canonical asset, but all original extraction
   records remain traceable.
5. Near-duplicates and multi-panel fragments require review; they are not
   silently collapsed.
6. A model-proposed diagnosis, stain, magnification, caption, or source mapping
   is `AI_SUGGESTED`, never verified medical metadata.
7. Only human-reviewed assets with resolvable source/page provenance may be used
   for image-based questions.
8. Extracted textbook images are private study assets. They are not eligible for
   Instagram, Facebook, public notes, public APIs, or redistribution unless
   separate publication rights are documented.
9. Image questions remain candidates until human approval. No vision model is
   medical ground truth.
10. Existing hard-coded multimodal catalog seeds and their citations are test
    fixtures only. They must not be treated as real assets or production
    evidence.

## Part 18A — Inventory and automated triage

### A1. Immutable inventory

For every input file record:

- SHA-256 and perceptual hash;
- MIME type and decoder result;
- width, height, aspect ratio, pixel area, file size, and color mode;
- alpha/transparent fraction;
- grayscale/color statistics;
- blank/near-blank score and entropy;
- edge density and connected-component summary;
- OCR/text-area estimate;
- source/page metadata supplied by the extraction manifest;
- extraction run and original relative path.

Corrupt or undecodable files receive `QUARANTINED_CORRUPT`; they are retained for
audit.

### A2. Triage classes

The first classifier is a utility classifier, not a diagnostic model:

- `PATHOLOGY_MICROSCOPY`
- `GROSS_PATHOLOGY`
- `IHC_OR_SPECIAL_STAIN`
- `CYTOLOGY_OR_HEMATOLOGY`
- `MEDICAL_DIAGRAM`
- `CHART_OR_GRAPH`
- `TABLE_OR_TEXT_FIGURE`
- `MULTI_PANEL_FIGURE`
- `LOGO_ICON_OR_DECORATION`
- `PAGE_FRAGMENT_OR_RULE`
- `BLANK_OR_NEAR_BLANK`
- `DUPLICATE`
- `UNKNOWN_REVIEW_REQUIRED`

The system should initially use reproducible image statistics and a replaceable
offline image-classification provider. Do not train a diagnostic pathology
model from these files during this milestone.

### A3. Decision statuses

Automated processing produces only:

- `AUTO_KEEP_CANDIDATE`
- `AUTO_REJECT_CANDIDATE`
- `HUMAN_REVIEW_REQUIRED`
- `QUARANTINED_CORRUPT`

No automated status is equivalent to human approval.

Examples of strong rejection candidates include tiny decorative bullets,
single-color rules, publisher logos, repeated navigation icons, and nearly blank
crops. Small but information-dense IHC panels, blood cells, labels, insets, and
compound-figure components go to review.

Thresholds such as minimum dimensions, entropy, text fraction, and perceptual
distance must be learned from the reviewed calibration sample. Do not hard-code
an assumption that 30–40% of files are unwanted.

### A4. Duplicate handling

Use separate signals:

1. exact SHA-256 duplicate;
2. decoded-pixel duplicate despite different encoding;
3. perceptual near-duplicate;
4. crop/parent relationship;
5. possible panels from the same figure.

Choose a canonical asset only after the relationship is recorded. Preserve all
source/page occurrences because a reused image may have different educational
context.

### A5. Contact sheets

Generate private review contact sheets with image ID, dimensions, proposed
class, confidence band, source short name, and physical page when known. Do not
include long textbook captions. Contact sheets are review artifacts and must
also remain outside public Git.

## Part 18B — Human cleanup and catalog approval

### B1. Calibration sample

Before processing all 3,000 files, a reviewer labels at least 300 stratified
images covering:

- every size/aspect-ratio band;
- low/high entropy;
- every proposed utility class;
- exact and near duplicates;
- likely pathology images;
- ambiguous fragments and multi-panel figures;
- samples from both books and multiple page ranges.

Store the reviewer, timestamp, decision, utility class, reason, and optional
correction. This becomes the versioned cleanup evaluation set.

### B2. Cleanup acceptance gate

On a held-out human-labeled set:

- useful-image recall at least 99%;
- `AUTO_REJECT_CANDIDATE` precision at least 98%;
- exact-duplicate precision 100%;
- near-duplicate precision at least 98%;
- corrupt-file detection 100% for the reviewed corrupt examples;
- every low-confidence prediction routed to human review;
- no approved asset lacks a resolvable file and matching SHA-256.

If useful-image recall misses the target, broaden the review bucket. It is safer
to review extra fragments than to discard a rare diagnostic visual.

### B3. Final human states

- `APPROVED_INTERNAL_STUDY`
- `APPROVED_INTERNAL_QUESTION_CANDIDATE`
- `REJECTED_NON_EDUCATIONAL`
- `REJECTED_UNUSABLE_QUALITY`
- `DUPLICATE_CANONICALIZED`
- `PROVENANCE_UNRESOLVED`
- `RIGHTS_RESTRICTED`

Approval for internal study does not automatically approve question generation.

## Part 18C — Database catalog and evidence linkage

### C1. Proposed data model

```text
ImageIngestionRun
  id, bundle_hash, extractor_name/version, classifier_provider/model/version,
  ruleset_version, status, counts, timestamps, configuration_hash

ImageAsset
  id, sha256, pixel_hash, perceptual_hash, storage_uri, width, height, format,
  utility_class, curation_status, rights_status, created_at

ImageOccurrence
  id, image_asset_id, source_document_id, pdf_page, textbook_page,
  figure_label, bounding_box, extraction_id, extraction_metadata

ImageReview
  id, image_asset_id, reviewer_id, decision, corrected_class, notes, created_at

ImageTextEvidenceLink
  id, image_asset_id, document_chunk_id, link_type, confidence,
  verification_status, verified_by, verified_at

QuestionImageEvidence
  question_id, image_asset_id, role, crop_variant_id, display_order
```

`ImageOccurrence` separates the binary image from its occurrences and prevents
loss of provenance when the same figure appears more than once.

### C2. Linking without PDFs

Link using the extraction manifest plus the already-promoted PostgreSQL corpus:

1. resolve source short name and source document hash;
2. resolve physical and printed page when supplied;
3. retrieve text chunks from the same page and adjacent pages;
4. compare supplied figure label/caption tokens when available;
5. store candidate links as `AI_SUGGESTED`;
6. human verifies the image-page-caption relationship;
7. store the verified image-to-text evidence link.

This requires no PDF access. When the handoff lacks reliable page metadata, the
asset remains useful for cleanup but cannot pass the question-generation gate.

### C3. Private storage

Store binaries in a private GCS or S3-compatible bucket using content-addressed
object keys. PostgreSQL stores metadata and private object references, not image
blobs. Signed URLs must be short-lived and authorized. Local development may use
an ignored private asset directory with the same storage interface.

## Part 18D — Image-grounded MCQ pilot

### D1. Entry gate

An image is eligible only when:

- status is `APPROVED_INTERNAL_QUESTION_CANDIDATE`;
- SHA-256 resolves to the cataloged private object;
- rights allow internal educational use;
- source document and physical page resolve;
- at least one human-verified image-to-text evidence link exists;
- stain/magnification/diagnosis metadata used by the question is human verified;
- the Milestone 16 text retrieval gate has passed.

### D2. Pilot size

Start with **30 image-grounded questions**, not one question per retained image:

- 10 morphology/recognition questions;
- 8 IHC or special-stain interpretation questions;
- 6 integrated clinicopathologic questions;
- 6 gross/cytology/hematology or diagram-based questions, based on the retained
  catalog distribution.

The 30 are part of the future 900-question mature bank, not an additional volume
quota. Multiple images from one figure or one learning objective must not inflate
the question count.

### D3. Generation packet

The generator receives only:

- approved private image or reviewed crop;
- verified human metadata;
- question blueprint;
- retrieved text evidence packet;
- allowed source IDs and evidence chunk IDs.

The response must cite both `image_asset_id` and supporting text chunks. A vision
model description is not sufficient evidence for the correct answer.

### D4. Mandatory evaluation

- image file/hash and authorization resolve;
- question is answerable from the displayed image plus supplied vignette;
- claimed visible features are actually visible at rendered exam resolution;
- stem does not reveal caption/diagnosis or rely on hidden metadata;
- correct answer and explanation are supported by verified text evidence;
- distractors are plausible and unambiguous;
- no invented stain, magnification, source, page, figure number, or diagnosis;
- no near-duplicate question or reused image/objective combination beyond quota;
- human reviewer approves both medical content and image rendering.

### D5. Image-question acceptance gate

- all 30 candidates receive human review;
- 100% of accepted images resolve and hash-match;
- 100% of accepted image/source/page mappings are human verified;
- 100% of accepted correct answers and explanations have text evidence;
- zero invented citations or visual findings;
- zero unreadable, clipped, distorted, or accidentally revealing images;
- rejected candidates remain stored as evaluation data;
- no automatic production approval.

## Explicitly out of scope

- re-extracting the PDFs during image cleanup;
- publishing extracted textbook images or contact sheets;
- training a diagnostic image model from copyrighted book figures;
- autonomous diagnosis of uploaded patient images;
- using hard-coded demo catalog citations as verified evidence;
- deleting raw files after automated rejection;
- generating hundreds of image questions before the 30-question pilot passes.

## Deliverables

1. Bundle validator and immutable image inventory.
2. Versioned cleanup rules/classifier interface.
3. Duplicate/crop/parent relationship detector.
4. Private contact-sheet review workflow.
5. Human-labeled cleanup benchmark and metrics report.
6. PostgreSQL image catalog and review/evidence-link schema.
7. Private object-storage adapter.
8. Image-to-existing-text linking workflow.
9. Thirty-question image-grounded pilot behind the M16 retrieval gate.
10. Reproducible private export and audit report.

## Approval checklist

- [ ] Start 18A image inventory/cleanup in parallel without requiring the PDF machine.
- [ ] Treat all extracted images and contact sheets as private copyrighted study assets.
- [ ] Never permanently delete an image based only on size or automated classification.
- [ ] Require human approval and verified source/page/text linkage for question use.
- [ ] Count the 30-question image pilot within the 900-question mature-bank target.
- [ ] Quarantine the current hard-coded multimodal catalog as demo/test data.
- [ ] Keep image MCQ generation blocked until the M16 retrieval gate passes.

## First implementation slice after approval

Implement only 18A:

1. inspect a sample of the extracted image directory and any existing manifest;
2. define the portable bundle schema;
3. build read-only inventory and hash/statistics collection;
4. produce exact-duplicate groups and triage candidates;
5. render private contact sheets;
6. create the 300-image stratified human-review sample;
7. do not delete files, train a diagnostic model, upload public assets, or
   generate image questions yet.

The implementation agent should stop after 18A and provide the handoff report
specified in `docs/M18_IMAGE_CURRATION_HANDOFF.md` before requesting approval for
18B.
