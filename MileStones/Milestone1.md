# Milestone 1 — Data Pipeline, Subject Extraction, Schema Normalization & Deduplication

## 1. Objective & Executive Summary

The primary objective of Milestone 1 is to establish an immutable, reproducible, and verifiable **data processing pipeline** that ingests the raw [MedMCQA](https://github.com/medmcqa/medmcqa) dataset, extracts all **Pathology** examination questions across all dataset splits, normalizes them into our canonical medical question schema, decouples topic metadata, and computes cryptographic deduplication hashes without dropping or mutating raw records.

> [!IMPORTANT]
> **Core Invariant**: Raw source datasets remain 100% immutable. Processing scripts must be fully deterministic, idempotent, and capable of generating reproducible processed JSONL artifacts from scratch.

---

## 2. Pipeline Architecture & Data Flow

```
                      RAW MEDMCQA DATASET (Parquet)
                  [ train.parquet | validation.parquet | test.parquet ]
                                   │
                                   ▼
                       SUBJECT EXTRACTION FILTER
                      (subject_name == "Pathology")
                                   │
                                   ▼
                         SCHEMA NORMALIZATION
           ├── Preserve Medical Unicode (NFKC, α/β/γ, ↑/↓ symbols)
           ├── Standardize Options: [{"key": "A", "text": "..."}]
           ├── Map Correct Option (0-3 / 1-4 -> 'A'-'D' & index 0-3)
           ├── Isolate Blind Test Split (is_labeled = False)
           └── Decouple Topic Metadata (UNMAPPED | RAW_ONLY | MAPPED)
                                   │
                                   ▼
                      DEDUPLICATION & CLUSTERING
           ├── SHA-256 content_hash (stem + sorted normalized options)
           ├── SHA-256 norm_stem_hash (normalized alphanumeric stem)
           └── Non-Destructive Duplicate Annotations (duplicate_signals)
                                   │
                                   ▼
                        PROCESSED JSONL EXPORT
           ├── pathology_all.jsonl        (15,526 total records)
           ├── pathology_labeled.jsonl    (15,221 labeled records)
           ├── pathology_train.jsonl      (14,441 train records)
           ├── pathology_validation.jsonl (780 validation records)
           ├── pathology_test.jsonl       (305 blind test records)
           └── summary_report.json        (comprehensive audit metadata)
```

---

## 3. Dataset Audit & Extraction Statistics

An inspection of the raw MedMCQA dataset for the `Pathology` subject reveals the following volume, split distribution, and characteristics:

| Split | Raw Total Qs | Extracted Pathology Qs | Labeled Qs | Unlabeled (Blind) Qs | Explanation Coverage |
|---|---|---|---|---|---|
| **Train** | 182,822 | **14,441** | 14,441 | 0 | 99.4% (14,357 Qs) |
| **Validation** | 4,183 | **780** | 780 | 0 | 99.5% (776 Qs) |
| **Test** | 6,150 | **305** | 0 | 305 | 0.0% (Unlabeled) |
| **Total** | **193,155** | **15,526** | **15,221** | **305** | **97.5% Overall** |

### Key Dataset Findings:
1. **Provenance & Source Exam Identifiers**: Questions originate from past Indian postgraduate medical entrance exams (AIIMS, NEET-PG, JIPMER, PGI).
2. **Textbook References Absence**: MedMCQA does **not** provide verified textbook page citations (e.g. *Robbins*, *Sternberg*, *WHO Blue Books*). Generic references found inside the explanation field (e.g., `"Ref: Robbins 9th ed"`) are treated as raw text and **never** automatically promoted to verified citations.
3. **Raw Topic Diversity**: 31 unique raw topic strings exist in the raw dataset (e.g. *General pathology*, *Hematology*, *Neoplasia*, *Cardiovascular system*, *Renal pathology*), with some null or unmapped values that require decoupled handling.

---

## 4. Schema Normalization Specification

### 4.1 Raw MedMCQA vs Target Normalized Schema

```mermaid
classDiagram
    class RawMedMCQARecord {
        +string id
        +string question
        +string opa
        +string opb
        +string opc
        +string opd
        +int cop
        +string choice_type
        +string exp
        +string subject_name
        +string topic_name
    }

    class NormalizedQuestionRecord {
        +string id (UUID)
        +string external_source ("medmcqa")
        +string external_source_id ("medmcqa-{id}")
        +string speciality ("Pathology")
        +string subject ("Pathology")
        +string topic_name_original
        +string topic_name_normalized
        +string topic_mapping_status ("UNMAPPED"|"RAW_ONLY"|"MAPPED")
        +string curriculum_topic_id (UUID | null)
        +string question_type ("single_best_answer")
        +string stem
        +array options [{"key":"A","text":"..."}]
        +string correct_option ("A"|"B"|"C"|"D"|null)
        +int correct_index (0..3 | -1)
        +boolean is_labeled
        +string explanation
        +string status ("IMPORTED")
        +string origin_cohort ("OLD_MCQ")
        +array tags
        +string content_hash (SHA-256)
        +string exact_stem_hash (SHA-256)
        +string norm_stem_hash (SHA-256)
        +object duplicate_signals
        +object metadata
        +string created_by ("system_import")
        +string created_at (ISO-8601)
        +string updated_at (ISO-8601)
    }

    RawMedMCQARecord --> NormalizedQuestionRecord : Transformed by scripts/normalize_medmcqa.py
```

### 4.2 Field Transformation & Sanitization Rules

1. **Deterministic Identifiers**:
   - `external_source_id`: Formatted as `f"medmcqa-{raw_id}"`.
   - `id`: Deterministic UUID v5 generated from `uuid.uuid5(INGESTION_NAMESPACE, external_source_id)` to guarantee repeatable imports.
2. **Options Array Structuring**:
   - Raw individual options (`opa`, `opb`, `opc`, `opd`) are sanitized and combined into a structured JSON array:
     ```json
     [
       {"key": "A", "text": "Option A text"},
       {"key": "B", "text": "Option B text"},
       {"key": "C", "text": "Option C text"},
       {"key": "D", "text": "Option D text"}
     ]
     ```
3. **Correct Answer (`cop`) Resolution**:
   - MedMCQA stores `cop` as a 0-indexed integer (0=A, 1=B, 2=C, 3=D) or 1-indexed in certain distributions.
   - Normalizer maps `0 -> ('A', 0)`, `1 -> ('B', 1)`, `2 -> ('C', 2)`, `3 -> ('D', 3)`.
   - Blind test records (`cop = -1` or `null`) are labeled with `correct_option = None`, `correct_index = -1`, and `is_labeled = False`.
4. **Unicode & Medical Character Preservation**:
   - Sanitization uses `unicodedata.normalize("NFKC", text)`.
   - Strips non-breaking spaces (`\u00a0`) and zero-width spaces (`\u200b`).
   - Preserves critical medical symbols: Greek letters ($\alpha, \beta, \gamma$), arrows ($\uparrow, \downarrow$), mathematical notations, and chemical formulas.
5. **Topic Decoupling**:
   - If `topic_name` is missing or `"nan"`: `topic_mapping_status = "UNMAPPED"`, `topic_name_original = None`.
   - If `topic_name` is present: `topic_mapping_status = "RAW_ONLY"`, `topic_name_original = raw_topic`, `topic_name_normalized = cleaned_topic`.
   - `primary_topic_id` / `curriculum_topic_id` is initialized to `None` (deferred to canonical curriculum mapping).

---

## 5. Deduplication & Similarity Hashing

To detect duplicates and similar questions without deleting historical exam records:

### 5.1 Cryptographic Hash Definitions

1. **`exact_stem_hash`**:
   $$\text{SHA-256}(\text{UTF-8}(\text{stem}))$$
2. **`norm_stem_hash`**:
   $$\text{SHA-256}(\text{UTF-8}(\text{lowercase, alphanumeric-only stem}))$$
3. **`content_hash`**:
   $$\text{SHA-256}(\text{UTF-8}(\text{norm\_stem} \parallel \text{sorted(norm\_options)}))$$

### 5.2 Non-Destructive Duplicate Annotation (`duplicate_signals`)

All questions are preserved. If a duplicate or stem collision occurs, metadata is annotated:

```json
{
  "duplicate_signals": {
    "is_content_duplicate": true,
    "content_cluster_id": "c62b9a...",
    "content_duplicate_count": 2,
    "content_duplicate_index": 1,
    "is_stem_collision": true,
    "stem_cluster_id": "a91e4f...",
    "stem_collision_count": 3,
    "stem_collision_index": 1
  }
}
```

---

## 6. Implementation Scripts

The data pipeline is implemented across 5 modular scripts in [`scripts/`](file:///r:/Repositories/medical-learning-intelligence/scripts):

| Script | Purpose & Key Functions |
|---|---|
| [`scripts/import_medmcqa.py`](file:///r:/Repositories/medical-learning-intelligence/scripts/import_medmcqa.py) | Downloads raw MedMCQA Parquet files (`train.parquet`, `validation.parquet`, `test.parquet`) from Hugging Face repository into `data/raw/medmcqa/`. |
| [`scripts/extract_pathology.py`](file:///r:/Repositories/medical-learning-intelligence/scripts/extract_pathology.py) | Filters datasets by `subject_name.str.strip().str.lower() == "pathology"`. Extracts train, validation, and test splits. |
| [`scripts/normalize_medmcqa.py`](file:///r:/Repositories/medical-learning-intelligence/scripts/normalize_medmcqa.py) | Implements `normalize_question_record()`, `sanitize_text()`, `compute_content_hashes()`, and `normalize_topic()`. |
| [`scripts/deduplicate_questions.py`](file:///r:/Repositories/medical-learning-intelligence/scripts/deduplicate_questions.py) | Computes content and stem clusters across all splits and annotates `duplicate_signals`. |
| [`scripts/run_pipeline.py`](file:///r:/Repositories/medical-learning-intelligence/scripts/run_pipeline.py) | End-to-end orchestrator executing Steps 1 through 5, exporting JSONL files and `summary_report.json`. |

---

## 7. Execution & Reproduction Guide

To execute the data pipeline from scratch:

```bash
# 1. Download raw MedMCQA dataset splits
python scripts/import_medmcqa.py

# 2. Run complete extraction, normalization, and deduplication pipeline
python scripts/run_pipeline.py --raw-dir data/raw/medmcqa --processed-dir data/processed/pathology
```

### Output File Artifacts:
- `data/processed/pathology/pathology_all.jsonl` (15,526 records, ~31 MB)
- `data/processed/pathology/pathology_labeled.jsonl` (15,221 records, ~30.5 MB)
- `data/processed/pathology/pathology_train.jsonl` (14,441 records)
- `data/processed/pathology/pathology_validation.jsonl` (780 records)
- `data/processed/pathology/pathology_test.jsonl` (305 records)
- `data/processed/pathology/summary_report.json` (audit metrics)

---

## 8. Verification & Test Suite

The data pipeline is verified by a dedicated test suite in [`tests/test_pipeline.py`](file:///r:/Repositories/medical-learning-intelligence/tests/test_pipeline.py):

```bash
python -m unittest tests/test_pipeline.py
```

### Test Coverage Checklist:
- [x] **Subject Extraction Filtering**: Correctly extracts case-insensitive `Pathology` records while ignoring other medical subjects.
- [x] **Labeled Question Normalization**: Validates option structuring, `cop` to `correct_option` mapping, UUID generation, and hash computation.
- [x] **Unlabeled Blind Test Normalization**: Ensures `is_labeled = False`, `correct_option = None`, and `correct_index = -1`.
- [x] **Unicode Sanitization**: Verifies preservation of medical symbols ($\alpha$-thalassemia, $\downarrow$ platelet count) and removal of non-breaking whitespace.
- [x] **Topic Decoupling**: Verifies `UNMAPPED` vs `RAW_ONLY` states and whitespace trimming.
- [x] **Deduplication Preservation**: Verifies 100% of records are retained while duplicate clusters are accurately annotated.
- [x] **JSONL Serialization Round-Trip**: Verifies seamless write and read serialization of normalized records without data corruption.

---

## 9. Milestone Deliverables Summary

1. **Reproducible Pipeline**: Fully functional Python pipeline scripts in `scripts/`.
2. **Standardized Processed Datasets**: 15,526 normalized Pathology questions exported to JSONL format in `data/processed/pathology/`.
3. **Comprehensive Audit Report**: Generated `summary_report.json` detailing split counts, label percentages, and topic distributions.
4. **Automated Unit Tests**: 100% passing tests in `tests/test_pipeline.py`.
