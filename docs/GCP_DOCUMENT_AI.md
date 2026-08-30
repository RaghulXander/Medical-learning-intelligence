# GCP Document AI & Reference Document Ingestion Architecture

**Project:** Medical Examination Intelligence Platform (DocEdge AI)  
**Component:** Reference Document Intake, PDF Slicing, Layout Parsing & Provenance Engine  
**Processor:** `docedge-layout-parser` (`a4fbeaa389c5955d`)  
**Location:** `us` (US Multi-region)  

---

## 1. Overview & Purpose

The Medical Examination Intelligence Platform relies on authoritative reference textbooks (such as *Robbins & Cotran Pathologic Basis of Disease*, *Sternberg's Diagnostic Surgical Pathology*, and *Robbins Review of Pathology*) to supply verified medical knowledge, ground-truth evidence, and grounding for automated MCQ validation and curriculum blueprints.

This subsystem provides:
1. **Immutable Document Registry**: Cryptographically verified cataloging of raw reference PDFs with SHA-256 hash tracking and deterministic document IDs.
2. **Pilot PDF Preparation & Slicing**: Accurate extraction of PDF chunks (e.g. 10–15 pages or targeted chapters) while preserving exact **1-based original page offsets**.
3. **GCP Document AI Integration**: High-accuracy layout parsing leveraging Google Cloud Document AI's **Layout Parser** (`a4fbeaa389c5955d`).
4. **Structured JSON Normalization**: Transformation of raw Document AI layout trees into clean, hierarchical domain blocks (`HeadingBlock`, `ParagraphBlock`, `TableBlock`, `ListBlock`, `FigureBlock`) with absolute page provenance.
5. **Quality & Provenance Auditing**: Automated quality scoring and 100% mathematical verification that no extracted token or block ever loses its original source title and page number.

---

## 2. GCP Infrastructure Specification

Based on the online GCP environment configured in `GCP.txt`:

| Resource | Configuration / Value |
|---|---|
| **GCP Project ID** | `doc-egde-rag` |
| **GCP Project Number** | `249137456895` |
| **Location** | `us` |
| **Processor Name** | `docedge-layout-parser` |
| **Processor ID** | `a4fbeaa389c5955d` |
| **Processor Type** | `Layout Parser` |
| **Prediction Endpoint** | `https://us-documentai.googleapis.com/v1/projects/249137456895/locations/us/processors/a4fbeaa389c5955d:process` |
| **Raw Bucket** | `gs://doc-egde-rag-rag-raw` |
| **Processed Output Bucket** | `gs://doc-egde-rag-rag-processed` |
| **Service Account** | `docedge-ingestion@doc-egde-rag.iam.gserviceaccount.com` |
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
* **Maximum page count:** Up to 500–1000 pages per batch request.
* **Input/Output:** Requires Cloud Storage buckets (`gs://...`).
* **Execution:** Returns a Long Running Operation (LRO) metadata token; structured JSON shards are written to the output bucket.
* **Best used for:** Complete volume/textbook ingestion runs.

### Slicing Strategy for Textbooks
Our raw reference textbooks:
1. `Robbins and Cotran Review of Pathology.pdf`: 496 pages (75.66 MB)
2. `Robbins_and_Cotran_Pathologic_Basis_of_Disease_11th_Edition.pdf`: 1227 pages (635.10 MB)
3. `Sternberg's diagnostic surgical pathology review 2nd Ed.pdf`: 1171 pages (70.12 MB)

Because the full books exceed the 15-page and 20MB online limits:
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
  [1. Immutable Document Registry] ──► Computes SHA-256, validates total pages, records registry.json
                 │
                 ▼
     [2. PDF Slicing Engine] ────────► Generates <= 15-page slices + manifest with 1-based page offsets
                 │
                 ▼
  [3. GCP Document AI Client] ───────► Sends slice to Layout Parser (online/batch or offline mock)
                 │
                 ▼
  [4. Structured Normalizer] ────────► Normalizes layout tree into typed Headings, Paragraphs, Tables, Figures
                 │
                 ▼
  [5. Quality & Provenance Audit] ───► Verifies 100% page/source retention + OCR confidence stats
                 │
                 ▼
  data/processed/reference_documents/
   ├── registry.json
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
> - `bounding_box`: Exact normalized spatial coordinates $[y_{min}, x_{min}, y_{max}, x_{max}]$ on the page.
> - `content_hash`: SHA-256 digest of normalized text content.

No medical evidence or question rationale may ever cite a slice-relative page number (e.g. "page 3 of chunk 4"). It must always reference the authoritative book page.
