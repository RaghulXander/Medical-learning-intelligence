# Medical Exam AI — Product & Technical Roadmap

## 1. Milestone Delivery Schedule

| Milestone | Phase | Scope & Deliverables | Status |
|---|---|---|---|
| **M1: Data Pipeline** | Days 1–4 | MedMCQA raw ingestion, Pathology extraction, topic decoupling, deduplication hashing, reproducible JSONL pipelines. | **COMPLETED** |
| **M2: Database & Core Ingestion** | Days 5–6 | PostgreSQL 16 schema (`schema.sql`), SQLAlchemy models, Docker compose environment, curriculum seeding, 15,526 questions imported. | **COMPLETED** |
| **M3: Domain Decoupling** | Day 6 | 3-tier architecture: Canonical Medical Taxonomy (`primary_topic_id`), Course Curriculum (`course_curriculum_mappings`), and Question Provenance (`source_exam_id`). | **COMPLETED** |
| **M4: Repository Stabilization** | Day 7 | Monorepo structure (`apps/web`, `apps/student-native`, `packages/shared`, `packages/api-client`), Git hygiene, `.gitignore` zero secrets/data leakage. | **COMPLETED** |
| **M5: Universal Assessment Engine** | Days 8–9 | Universal Assessment Engine, +4/-1 NEET scoring, Prometric 5-state palette, distractor strike tool, font zoom, 1-click remediation, mobile WebView embedding. | **COMPLETED** |
| **M6: Question Selection & Learner Model** | Days 10–11 | Intelligent Question Selection Engine, Hard Eligibility Precedence, Cascading Fallbacks, Laplace-smoothed UserMastery, Discrete Recency Penalties, Deterministic Seeded Selection. | **COMPLETED** |
| **M7: Core Identity & Common Backend** | Days 12–13 | Google OAuth2, Argon2id/bcrypt auth, strong password generator, guest diagnostic quiz & merge engine, adaptive onboarding, daily quiz API, session management & RBAC. | **COMPLETED** |
| **M7a: UI Enrichment & Missing Flows** | Day 13 | Next.js screens: Glassmorphic Auth Modal with live password entropy bar & 1-click strong pass, Guest Diagnostic Funnel, 3-Step Adaptive Onboarding (`/onboarding`), Enriched Student Hub with Circular Readiness Dial, and Smart Mistake Vault (`/student/review`). | **COMPLETED** |
| **M8: Student Native App & Mobile Experience** | Days 14–15 | Native Mobile App (`apps/mobile`), Student Dashboard, Daily Quiz Card, Readiness Dial, Exam Runner & Analytics. | **COMPLETED** |
| **M9: Security & Entitlements** | Release Foundation | Authentication hardening, authorization/ownership, course entitlements, audit trails, and migration preparation. | *In Progress* |
| **M10: Productionization** | Release Foundation | Vercel web deployment, Render API, Neon database, migrations, CI/CD, observability, backups, and Expo native publishing. | **COMPLETED** |
| **M11: Architecture Documentation** | Team Scale | Architecture/developer documentation system and multi-developer onboarding. | *Current / In Progress* |
| **M12: Ontology, AI Review & Code Review** | Quality | Consolidated topic ontology; AI-assisted approve/reject/retire workflow with feedback; Python, React, React Native, and shared-component review. | **In progress** — baseline review and shared auth rules complete. |
| **M13: Editors & Server-Driven UI** | Product Operations | Git-backed landing CMS plus reusable schema fields, revisioned question editing, versioned native layouts, safe widget delivery and EAS Update CI. | **13B–13E completed** — landing media and rollback UI remain. |
| **M14: Surgical Pathology Knowledge Ontology** | Knowledge Architecture | Versioned, typed Surgical Pathology hierarchy; reusable morphology/IHC/molecular relationships; source provenance; Breast vertical slice; reviewed question crosswalk. | **In progress** — reversible exact-label workflow applied 360 unverified suggestions without changing question status; human review, evidence relationships, and broader crosswalk remain. |
| **M15A: Verified Book Import Pilot** | Knowledge Ingestion | Rights-verified Robbins pilot; pinned live parser; page receipts/calibration; stratified human gold set; provenance and extraction-quality gates. | **In progress** — ingestion foundation exists; safety gates added; live/gold-set validation remains. |
| **M15B: Canonical Full-Book Import** | Knowledge Ingestion | GCS batch processing, resumable canonical runs, full layout/figure normalization, private evidence corpus, embeddings, and retrieval evaluation. | *Blocked on M15A acceptance.* |
| **M16: Evidence-Bound Learning Content** | Knowledge Product | Evidence-bound MCQ/short-note generation, validation, editorial review, and rights-safe media outputs. | **M16A approved / in progress** — A0–A2 engineering foundation complete; human retrieval benchmark and M15 evidence acceptance gate real embeddings and MCQ generation. |
| **M17: Android Direct Beta & Stabilization** | Release Quality | Signed GitHub APK prereleases, checksums, diagnostics, privacy/deletion, trusted pilot, wider invited beta, release gates, and rollback; Play/F-Droid deferred. | **In progress** — icon package, EAS beta profile, release workflow, and runbook are ready; secrets/source audit, compliance, diagnostics, and device QA remain. |
| **M18: Portable Pathology Image Curation** | Multimodal Knowledge | PDF-independent inventory and cleanup of extracted book images; private reviewed catalog; source/page/text linkage; 30-question image-grounded pilot. | **Deferred to extraction machine** — detailed AI-agent handoff is ready; 18A–18C require only the private extracted-image bundle and existing PostgreSQL text corpus; 18D remains gated by M16 retrieval accuracy. |
| **M50: Payments & Subscriptions** | Commercialization | Pricing, checkout, billing, renewals, invoices, and payment-provider webhooks. | *Future* |

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
