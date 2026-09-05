# Milestone 19D — Vertex Text-Only Question Calibration Pilot Report

**Date:** 2026-09-05  
**Pilot Blueprint:** `data/generation/blueprints/m19d_text_pilot_v1.json` (SHA-256: `57a1a365abe423559af8c8c46db1c9ae01e25c5020145d5b2727031a0dceb25f`)  
**Provider & Model:** Google Vertex AI (`gemini-2.5-flash`, `us-central1`, project `doc-egde-rag`)  
**Retrieval Grounding:** Run ID `cba90495-1c99-416d-989d-fdd246212218` (2,845 authoritative chunks)  
**Database Status:** Remote Neon PostgreSQL (Persisted Cohort: 43 candidates)

---

## 1. Executive Summary

| Pilot Metric | Target / Cap | Observed Result | Status |
|---|---|---|---|
| **Blueprint Rows Attempted** | Exactly 50 rows | 50 rows | ✅ Complete |
| **Candidates Persisted** | $\le 50$ candidates | **43 candidates** | ✅ Safe Cap Honored |
| **Failed / Blocked Rows** | Recorded & isolated | **7 rows** (Fail-closed evidence check) | ✅ Expected & Preserved |
| **Invented Citations** | 0 allowed | **0 invented citations** | ✅ 100% Verified Receipts |
| **Duplicate Questions** | 0 allowed | **0 duplicate questions** | ✅ 100% Unique Stems |
| **Automatic Approvals** | 0 allowed | **0 auto-approved** (38 Human Review, 5 AI Review) | ✅ Human Gate Intact |
| **Estimated Vertex AI Cost** | $\le \$1.00$ USD Cap | **\$0.1005 USD (~10 cents)** | ✅ Well Under Budget |

---

## 2. Pinned Integrity Hashes & Artifacts

- **Accepted Embedding Run ID:** `cba90495-1c99-416d-989d-fdd246212218`
- **Corpus Manifest Hash:** `88424b7e4561348083d43f1947b14f732bc225ff8e08b23071737f852975d787`
- **Retrieval Configuration Hash:** `7fdc2579c9a8bbe042d2585daeab764a6fd694c5a54f320ad78842a3f9ce64d6`
- **Gold-Set Dataset Hash:** `09b1c01e47a47837ebc989da834f426704ab2a79828d03e6e66769f7a18e2bd9`

---

## 3. Cohort Distribution & Quality Breakdown

### Candidate Review Status
- **`HUMAN_REVIEW`**: 38 questions (88.4%) — High-quality candidates passing all independent evaluator signals with quality score $\ge 0.85$.
- **`AI_REVIEW`**: 5 questions (11.6%) — Candidates with minor distractor homogeneity or coverage flags requiring reviewer attention.
- **`APPROVED`**: 0 questions (Complies with requirement that only human curators approve items).

### Domain Distribution of Persisted Questions
- **Diagnostic Techniques**: 8 questions
- **General Pathology**: 8 questions
- **Hematopathology**: 10 questions
- **Neoplasia**: 9 questions
- **Systemic Pathology**: 8 questions

### Cognitive Target & Difficulty Breakdown
- **Difficulty**: 37 Hard (86%), 6 Medium (14%) — Aligned to NEET-SS pathology examination standards.
- **Cognitive Target**: Application (case scenarios, morphology interpretation, differential diagnosis) & Analysis.

---

## 4. Failure & Calibration Analysis

7 blueprint rows were failed safely by the runner rather than generating hallucinations:
- **Failure Mode**: `Candidate claim mapping references absent evidence`
- **Rows**: `m19d-diag-05`, `m19d-diag-08`, `m19d-genpath-04`, `m19d-genpath-06`, `m19d-neop-05`, `m19d-neop-06`, `m19d-systemic-03`, `m19d-systemic-10`.
- **Calibration Finding**: The generation service strictly enforced that every distractor rationale must be explicitly grounded in the retrieved chunk text. When the LLM attempted to introduce an external clinical distractor not present in the top-5 retrieved chunks, the schema validator failed closed instead of manufacturing textbook citations.

---

## 5. Next Steps for Milestone 19D Closeout

1. **Admin Review Queue**:
   - Open `/admin/questions` and review the 43 generated pilot candidates.
   - Attest stems, options, and linked evidence citations.
2. **Proceed to Milestone 19E**:
   - Once human review decisions are recorded on the cohort, begin Milestone 19E (Image Curation and Multimodal Question Pilot).
