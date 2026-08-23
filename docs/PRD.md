# Medical Exam AI — Product Requirements Document (PRD)

## 1. Product Vision & Objective

Build an AI-assisted medical examination and education platform. The initial vertical focuses on **Pathology** (Postgraduate/Super-specialty level preparation, specifically DM/DrNB Oncopathology, MD Pathology, NEET-PG/SS).

---

## 2. Core User Personas & Requirements

### Admin Persona
- **Question Bank Management**: Search, filter, inspect, edit, approve, reject, or retire questions.
- **Evidence Management**: View supporting textbook citations, attach verified sources, review AI-suggested evidence.
- **Report Resolution**: Review user-reported inaccuracies (e.g. wrong answer, ambiguous stem, outdated guideline) and apply corrections.
- **Ingestion Tools**: Trigger and inspect dataset import pipelines (MedMCQA, AI generation batches).

### Student Persona
- **Instant Mock Exams**: Start timed exams customized by topic, question count, and difficulty.
- **Timed Exam Interface**: Clean, distraction-free test-taking UI with timer, question navigation grid, and option selector.
- **Instant Scoring & Review**: Post-submission breakdown of score, accuracy by topic, detailed explanations, and supporting evidence.
- **Question Reporting**: Submit structured feedback on questions (ambiguous phrasing, disputed answer key).

---

## 3. Milestones & Delivery Roadmap

| Milestone | Phase | Description | Status |
|---|---|---|---|
| **M1: Data Pipeline** | Days 1–4 | MedMCQA ingestion, Pathology extraction, topic decoupling, normalization, deduplication analysis, unit tests. | **COMPLETED** |
| **M2: ML Signal Service** | Days 5–6 | FastAPI microservice for PubMedBERT (`jamezoon/medmcqa-pubmedbert-mcqa`) MCQA prediction and agreement signal. | *Upcoming* |
| **M3: Core Backend & DB** | Days 7–8 | PostgreSQL database schema, migrations, Node.js API with question bank querying & authentication. | *Upcoming* |
| **M4: Question Bank & Admin UI** | Days 9–11 | Next.js admin dashboard for question review, filtering, editing, and status transitions. | *Upcoming* |
| **M5: Exam Engine & Student UI** | Days 12–13 | Timed mock-exam engine, exam blueprint generation, scoring, and review interface. | *Upcoming* |
| **M6: Reporting & Analytics** | Days 14–15 | User feedback loop, question correction workflow, and performance analytics. | *Upcoming* |
