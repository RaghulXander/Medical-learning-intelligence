# Medical Exam AI — Product & Technical Roadmap

## 1. Milestone Delivery Schedule

| Milestone | Phase | Scope & Deliverables | Status |
|---|---|---|---|
| **M1: Data Pipeline** | Days 1–4 | MedMCQA raw ingestion, Pathology extraction, topic decoupling, deduplication hashing, reproducible JSONL pipelines. | **COMPLETED** |
| **M2: Database & Core Ingestion** | Days 5–6 | PostgreSQL 16 schema (`schema.sql`), SQLAlchemy models, Docker compose environment, curriculum seeding, 15,526 questions imported. | **COMPLETED** |
| **M3: Domain Decoupling** | Day 6 | 3-tier architecture: Canonical Medical Taxonomy (`primary_topic_id`), Course Curriculum (`course_curriculum_mappings`), and Question Provenance (`source_exam_id`). | **COMPLETED** |
| **M4: Repository Stabilization** | Day 7 | Monorepo structure (`apps/web`, `apps/student-native`, `packages/shared`, `packages/api-client`), Git hygiene, `.gitignore` zero secrets/data leakage. | **COMPLETED** |
| **M5: Universal Assessment Engine** | Days 8–9 | Universal Assessment Engine, +4/-1 NEET scoring, Prometric 5-state palette, distractor strike tool, font zoom, 1-click remediation, mobile WebView embedding. | **COMPLETED** |
| **M6: AI Question Generation & PubMedBERT** | Days 10–11 | Python FastAPI ML service for PubMedBERT (`jamezoon/medmcqa-pubmedbert-mcqa`) MCQA evaluation signal & RAG question blueprints. | *Upcoming* |
| **M7: Feedback & Resident Analytics** | Days 12–13 | User question error reporting, admin editorial desk, and spaced repetition analytics. | *Upcoming* |
| **M8: Image Pathology & Multimodal PLIP** | Days 14–15 | Image-based histopathology MCQs and PLIP vision integration. | *Upcoming* |

---

## 2. Future Vision & Extension Points

### Phase 2: RAG & AI-Assisted Question Generation
- **Authoritative Text Embeddings**: pgvector-based retrieval across textbook chunks (*Robbins*, *WHO Blue Books*).
- **Structured Blueprint Generation**: Topic $\rightarrow$ Learning Objective $\rightarrow$ Evidence Retrieval $\rightarrow$ Blueprint $\rightarrow$ Candidate MCQ $\rightarrow$ Evaluator $\rightarrow$ Editorial Review.

### Phase 3: Pathology Image Analysis (PLIP & Multimodal Vision)
- Image-based gross and histopathology questions.
- Integration of **PLIP** (Pathology Language-Image Pretraining) and future multimodal vision models for morphological feature extraction and differential diagnosis aid.

### Phase 4: AI Pathology Viva & Case Tutor
- Interactive case-based examination with dynamic follow-up questioning and rubric-based oral viva scoring.
