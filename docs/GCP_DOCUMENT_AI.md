# GCP Document AI & Reference Document Ingestion Architecture

**Project:** Medical Examination Intelligence Platform (DocEdge AI)  
**Component:** Reference Document Intake, PDF Slicing, Layout Parsing & Provenance Engine  
**Processor:** Google Cloud Document AI Layout Parser (version pinned in the private environment)
**Location:** selected in the private GCP environment

---

## 1. Overview & Purpose

The Medical Examination Intelligence Platform relies on authoritative reference textbooks (such as *Robbins & Cotran Pathologic Basis of Disease*, *Sternberg's Diagnostic Surgical Pathology*, and *Robbins Review of Pathology*) to supply verified medical knowledge, ground-truth evidence, and grounding for automated MCQ validation and curriculum blueprints.

This subsystem provides:
1. **Immutable Document Registry**: Cryptographically verified cataloging of raw reference PDFs with SHA-256 hash tracking and deterministic document IDs.
2. **Pilot PDF Preparation & Slicing**: Accurate extraction of PDF chunks (e.g. 10–15 pages or targeted chapters) while preserving exact **1-based original page offsets**.
3. **GCP Document AI Integration**: Version-pinned live layout parsing for authorized content.
4. **Structured JSON Normalization**: Transformation of supported parser elements into provenance-bound blocks. Complete `documentLayout`, list, visual-element, and image handling remains a Milestone 15B deliverable.
5. **Quality & Provenance Auditing**: Automated traceability checks plus a separate human-reviewed extraction-accuracy evaluation.

---

## 2. GCP Infrastructure Specification

Concrete project numbers, processor IDs, service-account addresses, bucket names, and endpoints are environment configuration and must not be committed. Use `.env.gcp.example` as the key template and keep real values in the deployment secret store.

| Resource | Configuration / Value |
|---|---|
| **GCP Project ID** | private environment value |
| **GCP Project Number** | private environment value |
| **Location** | private environment value |
| **Processor Name/ID** | private environment value |
| **Processor Type** | `Layout Parser` |
| **Processor Version** | pinned after M15A bakeoff |
| **Raw/Output Buckets** | private, least-privilege buckets |
| **Service Account** | dedicated ingestion identity |
| **Assigned IAM Roles** | `roles/documentai.apiUser`, `roles/storage.objectViewer`, `roles/storage.objectUser` |

---

## 3. GCP Document AI Operational Limits & Slicing Strategy

Understanding Google Cloud Document AI's operational constraints is essential for processing multi-hundred page medical textbooks:

### Online Parsing (`process_document` / synchronous)
* **Maximum page count:** 15 pages per request for Layout Parser / OCR.
* **Maximum payload size:** 20 MB per file.
* **Timeout:** 120 seconds per HTTP call.
* **Best used for:** Rapid developer testing, pilot chapters, interactive inspections, and sliced chunks.

### Batch Processing (`batch_process_documents` / asynchronous)
* **Maximum page count:** 500 PDF pages per file for Layout Parser.
* **Input/Output:** Requires Cloud Storage buckets (`gs://...`).
* **Execution:** Returns a Long Running Operation (LRO) metadata token; structured JSON shards are written to the output bucket.
* **Best used for:** Complete volume/textbook ingestion runs.
* **Repository status:** Not implemented yet; this is Milestone 15B work.

### Slicing Strategy for Textbooks
Because full books exceed the online limits:
1. The **PDF Splitter** cuts the parent PDF into manageable pilot slices ($\le 15$ pages each, e.g. pages 1–15, 16–30, or specific disease chapters).
2. Each slice retains a manifest recording:
   $$\text{original\_page\_number} = \text{start\_page\_1based} + \text{slice\_page\_index} - 1$$
3. When Document AI parses slice page 1 of chunk `p0401_p0415`, the normalizer maps it directly back to **original page 401** of *Robbins 11th Edition*.

---

## 4. End-to-End Pipeline Workflow

```text
  data/raw/reference_documents/*.pdf
                 │
                 ▼
  [1. Rights-verified registry] ─────► Rights attestation + SHA-256 + total pages
                 │
                 ▼
     [2. PDF Slicing Engine] ────────► Generates <= 15-page slices + manifest with 1-based page offsets
                 │
                 ▼
  [3. GCP Document AI Client] ───────► Sends slice to pinned live Layout Parser
                 │
                 ▼
  [4. Structured Normalizer] ────────► Normalizes supported layout types + page receipts
                 │
                 ▼
  [5. Quality & Provenance Audit] ───► Checks traceability; human gold set measures accuracy
                 │
                 ▼
  data/processed/reference_documents/
   ├── registry.json                 # private/generated, not Git-tracked
   ├── slices/*.pdf & *_manifest.json
   ├── raw_docai/*.json
   ├── normalized/*_normalized.json
   └── reports/*_quality_report.md
```

---

## 5. Provenance Invariant

> [!IMPORTANT]
> **Strict Provenance Invariant:**  
> Every extracted block in the system MUST retain:
> - `original_doc_id`: Unique identifier of the source work.
> - `original_doc_title`: Canonical title of the reference textbook.
> - `original_page_number`: 1-based absolute physical page number in the original book.
> - `bounding_box`: Normalized spatial coordinates when the pinned processor/version supplies them.
> - `content_hash`: SHA-256 digest of normalized text content.

No medical evidence or question rationale may ever cite a slice-relative page number (e.g. "page 3 of chunk 4"). It must always reference the authoritative book page.

## 6. Trust boundaries

- `LIVE_DOCAI` output from a pinned processor is the only parser mode eligible for evidence.
- `MOCK_LOCAL_PYPDF` is for synthetic tests/development and is blocked before evidence generation and embedding.
- A complete provenance report proves source/page linkage, not textual or medical correctness.
- Physical PDF pages and printed page labels are separate fields. Page-label calibration requires human verification.
- Source content is processed only after `rights_status=AUTHORIZED` and a rights basis are recorded.

## 7. Official limits and feature references

- [Layout Parser overview](https://docs.cloud.google.com/document-ai/docs/layout-parse-chunk)
- [Layout Parser quickstart](https://docs.cloud.google.com/document-ai/docs/layout-parse-quickstart)
- [Document AI quotas and limits](https://docs.cloud.google.com/document-ai/docs/limits)

## 8. Private artifact backup for another laptop

Generated JSON remains in `data/processed/reference_documents/` locally but is ignored by Git. After confirming the source is rights-authorized, copy it to the private processed bucket so it can be restored on another machine.

Preview the upload:

```bash
gcloud storage rsync --recursive --dry-run \
  data/processed/reference_documents \
  "gs://${GCP_PROCESSED_BUCKET}/reference_documents"
```

Run the same command without `--dry-run` after reviewing the targets. On the new laptop, reverse the source and destination:

```bash
gcloud storage rsync --recursive \
  "gs://${GCP_PROCESSED_BUCKET}/reference_documents" \
  data/processed/reference_documents
```

Keep the bucket private, enable object versioning/lifecycle controls appropriate to the budget, and do not upload credential JSON. Raw source PDFs should use the private raw bucket and follow the same rights policy.
