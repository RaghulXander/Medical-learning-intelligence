# Medical Exam AI (DocEdge) — Active Session Context

> [!NOTE]
> This file is automatically loaded by the AI agent on every new chat session to prevent loss of context.
> Last Updated: 2026-09-05

---

## 1. Current Objective & Active Milestone

* **Active Milestones**: human review of [MileStone19D.md](MileStones/MileStone19D.md) and curation work for [MileStone19E.md](MileStones/MileStone19E.md)
* **Goal**: Finish text-candidate review while independently curating private images for a gated 30-question multimodal pilot.
* **Key Tasks**:
  1. M19B Provenance Manifests (Passed 3/3 reference books: 2,845 chunks, 0 missing/duplicate pages).
  2. M19C Paid Vertex AI Embeddings (Run `cba90495-1c99-416d-989d-fdd246212218`, 2,845/2,845 vectors in Neon DB).
  3. M19C Retrieval Evaluation (55 gold-set cases evaluated, 0 citation mismatches).
  4. M19D pilot-safe generation integration, approved blueprint, dry run, cost checkpoint, and human review.

---

## 2. Project Architecture & Key Entrypoints

* **Backend (FastAPI)**:
  * Main App: [backend/api/main.py](file:///r:/Repositories/medical-learning-intelligence/backend/api/main.py)
  * Hybrid Retrieval Service: [backend/services/hybrid_retrieval_service.py](file:///r:/Repositories/medical-learning-intelligence/backend/services/hybrid_retrieval_service.py)
  * Provenance Manifests: [backend/ingestion/provenance_manifest.py](file:///r:/Repositories/medical-learning-intelligence/backend/ingestion/provenance_manifest.py)
  * Evaluation Script: `scripts/evaluate_retrieval.py`
  * Evidence Embeddings Script: `scripts/generate_evidence_embeddings.py`
  * M19D Pilot Service: `backend/services/generation/m19d_pilot.py`
  * M19D Pilot Runner: `scripts/run_m19d_text_pilot.py`
  * M19D Blueprint: `data/generation/blueprints/m19d_text_pilot_v1.json`
  * Status Report: [docs/M19C_RETRIEVAL_ACCEPTANCE_REPORT.md](file:///r:/Repositories/medical-learning-intelligence/docs/M19C_RETRIEVAL_ACCEPTANCE_REPORT.md)
* **Web Frontend (Next.js 14 / React / TypeScript)**:
  * Directory: `apps/web/`
  * Student Results: [apps/web/src/app/student/results/[attemptId]/page.tsx](file:///r:/Repositories/medical-learning-intelligence/apps/web/src/app/student/results/[attemptId]/page.tsx)
  * Error Handling: [apps/web/src/app/global-error.tsx](file:///r:/Repositories/medical-learning-intelligence/apps/web/src/app/global-error.tsx)
* **Mobile App (Future Milestone 8)**:
  * Directory: `apps/student-native/` or `apps/mobile/`

---

## 3. Dev Commands & Environment

* **Start Full Dev Stack**:
  ```powershell
  # Using PowerShell kickstart script:
  .\start-dev.ps1

  # Or directly via Python dev runner:
  python dev.py
  ```
* **Individual Dev Servers**:
  ```powershell
  # Backend only (port 8000)
  bun run dev:backend

  # Web frontend only (port 3000)
  bun run dev:web

  # Database migrations
  bun run db:migrate
  ```
* **Retrieval Evaluation & Embedding**:
  ```powershell
  # Validate evaluation benchmark against existing DB embeddings:
  python scripts/evaluate_retrieval.py --dataset data/evaluation/retrieval/verified/m16a_retrieval_eval_v1.jsonl --embedding-run-id cba90495-1c99-416d-989d-fdd246212218
  ```
* **Testing & Quality**:
  ```powershell
  bun run typecheck
  bun run lint
  bun test packages/shared/src
  ```

---

## 4. Daily Continuity & Handoff Log

When starting a new conversation:
1. Agent reads this file first to restore exact context.
2. At the end of the day or before clearing context, the agent updates the summary below.

### Latest State (2026-09-05):
- **Milestone 19B (Provenance Gate)**: **PASSED (3/3 Books)** (Robbins Review, Robbins Basis 11th, Sternberg 2nd: 2,845 chunks, 0 missing/duplicate pages).
- **Milestone 19C (Vertex AI Embeddings)**: **COMPLETED 100%** (2,845 / 2,845 vectors in DB, Run ID: `cba90495-1c99-416d-989d-fdd246212218`).
- **Milestone 19C (Retrieval Acceptance Gate)**: **PASSED (`gate_passed: true`)**
  - **Overall Recall@5**: **98.0%** (49/50 in-corpus hits) [Target: ≥90%]
  - **Recall@10**: **98.0%** | **Recall@1**: **68.0%** | **MRR**: **0.797**
  - **Domain Recall@5**: Diagnostic (100%), Hematopathology (100%), Neoplasia (100%), Systemic (100%), General (90%) [Target: ≥80%]
  - **Out-of-corpus Refusal**: **100.0%** (5/5 controls refused)
  - **Citation Mismatches**: **0**
- **Milestone 19D (Vertex Text Calibration Pilot)**: **EXECUTION COMPLETE**
  - 50 blueprint rows attempted against Vertex AI `gemini-2.5-flash` (`us-central1`).
  - **43 candidates generated and persisted** into PostgreSQL with complete evidence receipts (38 in `HUMAN_REVIEW`, 5 in `AI_REVIEW`, 0 auto-approved).
  - 7 rows failed closed safely due to strict claim-to-evidence validation.
  - Actual estimated cost: **$0.1005 USD** (well below $1.00 budget cap).
  - Full report saved in [docs/M19D_CALIBRATION_PILOT_REPORT.md](file:///r:/Repositories/medical-learning-intelligence/docs/M19D_CALIBRATION_PILOT_REPORT.md).
- **Milestone 19E (Image Curation + Multimodal Pilot)**: **PART A READY**
  - 72 candidates shortlisted and tagged in DB with SHA-256 local hash verification.
  - Local image proxy integrated into backend for zero-latency review in Admin UI.
  - Manual image review deferred in favor of automated AI vision pre-annotation.
- **Question Bank Status**: **51 APPROVED Questions** (all reviewed and validated), 2 REJECTED, 0 AI_REVIEW.
- **Milestone 20 (1,200+ Question Corpus Expansion: Direct Textbook Q&As + AI Generation + Image MCQs)**: **ACTIVE / NEXT**
  - Planned expansion to **1,200+ questions**: 500+ direct textbook review Q&As (*Robbins Review* & *Sternberg Review*), 400+ subspecialty AI-generated questions with `VERY_HARD` tier, and 300+ image-grounded MCQs.
  - Detailed milestone specification documented in [MileStones/MileStone20.md](MileStones/MileStone20.md).
- **Milestone 25 (AI-Assisted Pathology Vision Review & Pre-Annotation)**: **PLANNED (DEFERRED FOR LATER)**
  - Planned integration with specialized pathology vision models (**PLIP**, **BiomedCLIP**, **Gemini Multimodal**) to pre-populate stains, organ systems, diagnoses, and captions automatically, cutting human curation time by 90%.
  - Detailed milestone specification documented in [MileStones/MileStone25.md](MileStones/MileStone25.md).
