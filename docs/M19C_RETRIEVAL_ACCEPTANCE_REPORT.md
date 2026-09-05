# Milestone 19B & 19C Comprehensive Status & Retrieval Acceptance Report

**Date:** 2026-09-05  
**Active Environment:** Remote Neon PostgreSQL + Google Vertex AI (`us-central1`)  
**Embedding Run ID:** `cba90495-1c99-416d-989d-fdd246212218`  
**Dataset Version:** `m16a-retrieval-v1` (55 cases: 50 in-corpus, 5 out-of-corpus controls)

---

## 1. Executive Summary

| Component / Gate | Status | Details |
|---|---|---|
| **Milestone 19B: Provenance Gate** | **PASSED (3/3 Books)** | All 3 reference books extracted via DocAI, 2,845 chunks, 0 missing/duplicate pages. |
| **Milestone 19C: Real Embedding Run** | **PASSED (100%)** | 2,845 / 2,845 vectors embedded with `gemini-embedding-001` (768-dim) into Neon DB. |
| **Milestone 19C: Cryptographic Integrity** | **PASSED (100%)** | 0 citation / hash mismatches across all retrieved items. |
| **Milestone 19C: Retrieval Recall@5 Gate** | **PASSED (98.0%)** | 49/50 in-corpus hits (Threshold: ≥ 90%). MRR = 0.797, Recall@1 = 68.0%. |
| **Milestone 19C: Domain Recall@5 Gate** | **PASSED (90–100%)** | Diag (100%), Heme (100%), Neop (100%), Sys (100%), General (90%) (Threshold: ≥ 80%). |
| **Milestone 19C: Out-of-Corpus Refusal** | **PASSED (100%)** | 5/5 out-of-corpus controls cleanly returned `INSUFFICIENT_EVIDENCE`. |
| **OVERALL M19C ACCEPTANCE GATE** | **PASSED (TRUE)** | `gate_passed: true` in official evaluation report. |

---

## 2. Milestone 19B Completion Details

All 3 authoritative textbooks have verified, enforceable provenance manifests stored under `data/processed/reference_documents/provenance_manifests/`:

1. **`robbins_review`**:
   - Total Chunks: 34 (15 pages/chunk)
   - Physical Pages: 496
   - Missing Pages: 0 | Duplicate Pages: 0 | Status: `PASSED`
2. **`robbins_pathologic_basis_11th`**:
   - Total Chunks: 82 (15 pages/chunk)
   - Physical Pages: 1,227
   - Missing Pages: 0 | Duplicate Pages: 0 | Status: `PASSED`
3. **`sternberg_review_2nd`**:
   - Total Chunks: 79 (15 pages/chunk)
   - Physical Pages: 1,171
   - Missing Pages: 0 | Duplicate Pages: 0 | Status: `PASSED`

**Total Authoritative Corpus Chunks in DB:** `2,845` chunks.

---

## 3. Milestone 19C Embedding Run

The paid Vertex AI embedding run was executed against the remote PostgreSQL database:

- **Run ID:** `cba90495-1c99-416d-989d-fdd246212218`
- **Embedding Model:** `gemini-embedding-001`
- **Vector Dimensions:** `768`
- **Task Types:** `RETRIEVAL_DOCUMENT` (for corpus chunks), `RETRIEVAL_QUERY` (for search queries)
- **Vectors Ingested:** `2,845 / 2,845` (100.0% completion, 0 errors)
- **Configuration Hash:** `07cf615945e78cf9258d0c6788152ae9ad99e8dea93ecbde285261b1ca59bd6f`
- **Status:** `COMPLETED` (Immutable receipt stored in `document_chunk_embeddings`)

---

## 4. Benchmark Retrieval Evaluation Results (v1 — PASSED)

Evaluation was performed with `scripts/evaluate_retrieval.py` across all 55 test cases:

### Top-Level Metrics
- **Overall Acceptance Gate:** **PASSED (`gate_passed: true`)**
- **Recall@5:** **98.0%** (49 / 50 in-corpus hits) *(Target: ≥ 90%)*
- **Recall@10:** **98.0%** (49 / 50)
- **Recall@1:** **68.0%** (34 / 50)
- **Mean Reciprocal Rank (MRR):** **0.797**
- **Citation Mismatches:** **0** (100% cryptographic integrity)
- **Out-of-Corpus Refusal Rate:** **100.0%** (5 / 5 controls cleanly refused)
- **Evaluator Dataset Hash:** `09b1c01e47a47837ebc989da834f426704ab2a79828d03e6e66769f7a18e2bd9`

### Per-Domain Recall@5
| Domain | Cases | Hits@5 | Recall@5 | Target | Status |
|---|---|---|---|---|---|
| **Diagnostic Techniques** | 10 | 10 | **100.0%** | ≥ 80% | **PASSED** |
| **General Pathology** | 10 | 9 | **90.0%** | ≥ 80% | **PASSED** |
| **Hematopathology** | 10 | 10 | **100.0%** | ≥ 80% | **PASSED** |
| **Neoplasia** | 10 | 10 | **100.0%** | ≥ 80% | **PASSED** |
| **Systemic Pathology** | 10 | 10 | **100.0%** | ≥ 80% | **PASSED** |

---

## 5. Final Miss Analysis

The accepted evaluation has one Recall@5 miss: `gen-path-002`. It remains a
valid human-reviewed benchmark case and is retained as a documented retrieval
failure rather than being relabelled merely to obtain a perfect score.

The previous evaluation's 19 misses led to evidence repair and human review.
They are historical calibration results and are not outstanding M19C work.

---

## 6. M19C Acceptance Record

The user confirmed review of the 19 corrected evidence sets on 2026-09-05.
The accepted artifacts are:

- dataset SHA-256:
  `09b1c01e47a47837ebc989da834f426704ab2a79828d03e6e66769f7a18e2bd9`;
- embedding run ID: `cba90495-1c99-416d-989d-fdd246212218`;
- embedding configuration hash:
  `07cf615945e78cf9258d0c6788152ae9ad99e8dea93ecbde285261b1ca59bd6f`;
- retrieval configuration hash:
  `7fdc2579c9a8bbe042d2585daeab764a6fd694c5a54f320ad78842a3f9ce64d6`;
- report: `data/evaluation/retrieval/reports/m19c_retrieval_eval_v1.json`;
- report-producing commit: `081c7ef1efed0f2cedbb529248de0fe04233f90c`.

The private provenance manifests are intentionally excluded from Git. The
cross-machine handoff must retain their private object location and SHA-256
values; the incomplete legacy Robbins Review manifest in a checkout is not the
accepted live manifest.

---

## 7. Next Steps & Workflow for Any Machine

When opening this repo on any other development machine:

1. **Pull Latest Changes:**
   ```bash
   git pull origin main
   ```
2. **Configure Environment (.env):**
   Ensure `.env` contains:
   ```env
   DATABASE_URL="<your_neon_postgres_url>"
   GOOGLE_APPLICATION_CREDENTIALS="docedge-key.json"
   GOOGLE_CLOUD_PROJECT="doc-egde-rag"
   GOOGLE_CLOUD_LOCATION="us-central1"
   ```
3. **Run Validation on Existing Embeddings:**
   Verify connection to the 2,845 vector run:
   ```bash
   python scripts/evaluate_retrieval.py \
     --dataset data/evaluation/retrieval/verified/m16a_retrieval_eval_v1.jsonl \
     --embedding-run-id cba90495-1c99-416d-989d-fdd246212218 \
     --validate-only
   ```
4. **Transition to Milestone 19D:**
   Use the immutable identifiers in Section 6 and proceed with
   `MileStones/MileStone19D.md`. Do not rerun paid retrieval evaluation unless
   the dataset, corpus, embedding run, or retrieval configuration changes.
