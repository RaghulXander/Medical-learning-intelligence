# Medical Exam AI — Product & Technical Roadmap

## 1. 15-Day Delivery Schedule

| Milestone | Phase | Scope & Deliverables | Status |
|---|---|---|---|
| **M1: Data Pipeline** | Days 1–4 | MedMCQA raw ingestion, Pathology extraction, topic decoupling, deduplication hashing, reproducible JSONL pipelines. | **COMPLETED** |
| **M2: Database & Core Ingestion** | Days 5–6 | PostgreSQL 16 schema (`schema.sql`), SQLAlchemy models, Docker compose environment, curriculum seeding, 15,526 questions imported. | **COMPLETED** |
| **M3: Domain Decoupling** | Day 6 | 3-tier architecture: Canonical Medical Taxonomy (`primary_topic_id`), Course Curriculum (`course_curriculum_mappings`), and Question Provenance (`source_exam_id`). | **COMPLETED** |
| **M4: Repository Stabilization** | Day 7 | Repository audit, Git hygiene, `.gitignore` exclusions, documentation, and GitHub baseline preparation. | **IN PROGRESS** |
| **M5: ML Signal Service** | Days 8–9 | Python FastAPI service for PubMedBERT (`jamezoon/medmcqa-pubmedbert-mcqa`) MCQA prediction and agreement signal. | *Upcoming* |
| **M6: Question Bank & Admin UI** | Days 10–11 | Next.js admin dashboard: Question review, full-text search, topic filtering, status transitions, and `question_courses` curation. | *Upcoming* |
| **M7: Exam Engine & Student UI** | Days 12–13 | Timed mock exam engine, blueprint generation (topic + difficulty distribution), timer, instant scoring, and review breakdown. | *Upcoming* |
| **M8: Reporting & Analytics** | Days 14–15 | User error reporting, admin correction workflow, and resident performance analytics. | *Upcoming* |

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
