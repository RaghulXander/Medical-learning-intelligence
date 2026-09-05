# Milestone 19E — Image Curation and Multimodal Question Pilot

> **Status (2026-09-05): ACTIVE — curation UI implemented; paid generation remains blocked**

## Outcome

Curate the private pathology image catalog and run a controlled pilot of exactly
30 image-grounded NEET-SS question candidates. This milestone runs alongside
human review of the text-question pilot. It does not publish textbook images or
automatically approve generated questions.

## Starting database audit

The read-only remote audit on 2026-09-05 found:

- 2,165 image assets and occurrences;
- 3,053 image-to-text candidate links;
- 2,162 links with a source/page-compatible occurrence;
- 0 images approved for question generation;
- 0 human-verified image-text links.

Therefore the generation gate is closed. Existing `CURATED_VALID` and
`AI_SUGGESTED` values are import/automation states, not human approval.

## Part A — Human curation

### Local/remote shortlist ranking

Do not review all 2,165 assets before the pilot. On the machine containing the
local images, combine local pixel facts with remote source/page/chunk metadata:

```bash
python scripts/rank_m19e_images.py \
  --database-url-env REMOTE_DATABASE_URL \
  --image-dir /absolute/path/to/images
```

This defaults to a metadata-only, 72-image shortlist and verifies local hashes
only for shortlisted files. It writes a private ignored JSON report containing
no textbook passages or permanent R2 URLs. Review the shortlist first and select
the strongest 30. To sync only non-authoritative rank/tags into
`ImageAsset.metadata` after inspecting the dry run, repeat with `--apply-tags`.

Ranking uses deterministic quality, duplicate, exact provenance, figure-link,
and text-keyword signals. Suggested utility/tags remain `AI_SUGGESTED`; the
script cannot set human review status, verify evidence, supply a diagnosis, or
approve an image. A local CLIP-like utility classifier may later be added as an
additional signal, but never as medical ground truth.

Apply migration `20260905_0009`, deploy, then open **Admin → Image curation**.
For each useful image:

1. inspect the rendered private image;
2. correct the utility class;
3. enter only diagnosis, stain, magnification, and caption metadata supported by
   the displayed image and its book context;
4. select the exact source/page occurrence;
5. select and read a same-source, same-physical-page text chunk;
6. add concise review notes and attest;
7. choose **Approve for questions** only when every question gate is satisfied.

Use **Approve study** when an image is educational but not sufficiently grounded
for a question. Reject decoration/page fragments and unusable images with the
specific reason. Choose **Provenance unresolved** when the object is useful but
its exact source/page cannot be established.

Every save/decision creates an immutable `image_reviews` snapshot. Optimistic
revision checks prevent one reviewer from silently overwriting another. Browser
previews use the authenticated backend proxy; the persistent R2 URL is not sent
to the browser. Configure `R2_PUBLIC_URL` on the backend to the exact catalog
prefix until storage is moved to fully private presigned access.

Question eligibility additionally requires `storage_access_status =
PRIVATE_VERIFIED`. Existing public-CDN-style URLs remain `UNVERIFIED` even when
the medical curation is approved, so they cannot accidentally open the pilot
gate. A private R2 object audit/migration is the next storage slice.

## Part B — 30-slot pilot blueprint

The draft blueprint is
`data/generation/blueprints/m19e_multimodal_pilot_v1.json`:

- 10 morphology/recognition;
- 8 IHC or special-stain interpretation;
- 6 integrated clinicopathologic;
- 6 gross/cytology/hematology/diagram.

Run the no-cost, read-only gate check:

```bash
python scripts/run_m19e_multimodal_pilot.py \
  --database-url-env REMOTE_DATABASE_URL
```

Exit code 2 means the curation gate remains closed. This command never invokes
Vertex and never writes the database.

## Entry gate for generation implementation

Generation may be added only after:

- at least 30 assets satisfy the full relational eligibility query;
- the category distribution can fill all four blueprint cohorts;
- each selected asset has an exact `ImageOccurrence` and a `HUMAN_VERIFIED`
  `ImageTextEvidenceLink` bound to that occurrence;
- diagnosis/caption and any used stain/magnification are human verified;
- object resolution and SHA-256 checks pass;
- the 30 image/learning-objective allocations are frozen and reviewed;
- the owner approves the model, region, request cap, and current cost estimate.

The legacy hard-coded multimodal catalog and generic templated generator are
test fixtures and are forbidden for this pilot.

## Generation acceptance rules

- one image blueprint and one candidate per model request;
- the model cannot create citations, page numbers, diagnoses, stains, or
  magnification metadata;
- server-side persistence attaches `QuestionImageEvidence` with asset,
  occurrence, and verified link IDs;
- the caption/diagnosis must not leak into the stem;
- correct answer, explanation, and factual distractor rationales require
  verified text evidence;
- option order is deterministic and not fixed to A;
- generated candidates enter human review, never `APPROVED`;
- all 30 require medical-content and exam-resolution image-rendering review.

## Definition of done

The milestone completes when all 30 candidates have human decisions, every
accepted question has hash-resolving image provenance and verified text support,
and the pilot report records zero invented citations/visual findings and zero
unreadable or clipped images.
