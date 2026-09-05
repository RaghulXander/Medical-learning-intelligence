# Medical Exam AI (DocEdge) — Active Session Context

> [!NOTE]
> This file is automatically loaded by the AI agent on every new chat session to prevent loss of context.
> Last Updated: 2026-09-05

---

## 1. Current Objective & Active Milestone

* **Active Milestone**: [MileStone19D.md](MileStones/MileStone19D.md)
* **Goal**: Controlled 50-question, text-only, evidence-backed NEET-SS calibration pilot.
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
- Complete documentation saved in [docs/M19C_RETRIEVAL_ACCEPTANCE_REPORT.md](file:///r:/Repositories/medical-learning-intelligence/docs/M19C_RETRIEVAL_ACCEPTANCE_REPORT.md).
- **Milestone 19D**: implementation and no-cost dry run complete; the 50-row
  blueprint was approved by the project owner on 2026-09-05. Vertex execution
  remains blocked only on an explicit cost cap.
