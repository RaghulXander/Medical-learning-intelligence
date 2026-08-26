# DocEdge — Medical Exam AI Platform

[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-blue.svg)](https://www.postgresql.org/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-green.svg)](https://www.python.org/)
[![Bun 1.4+](https://img.shields.io/badge/Bun-1.4%2B-FBF0DF.svg)](https://bun.sh/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14%20App%20Router-black.svg)](https://nextjs.org/)
[![tsdown](https://img.shields.io/badge/tsdown-Rolldown%20Bundler-orange.svg)](https://github.com/tsdown/tsdown)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)

> **Scalable AI-assisted medical examination and question bank platform.**  
> Initial focus: **Pathology** (Postgraduate/Super-Specialty preparation for **DM/DrNB Oncopathology**, **MD Pathology**, **NEET-PG**, and **INI-CET**).

---

## 1. Project Overview

Medical Exam AI is an educational platform designed to provide rigorous, evidence-backed mock examinations and question-bank analytics for medical trainees and residency candidates.

### Three-Tier Domain Architecture

The platform cleanly decouples medical knowledge from educational curricula and historical question provenance:

```mermaid
flowchart TD
    subgraph Tier1["1. Canonical Medical Knowledge (Exam-Agnostic)"]
        Topic["CurriculumTopic\n(e.g., TOPIC-BREAST-PATH)"]
        LO["Learning Objective\n(e.g., LO-HER2-IHC-SCORE)"]
        Topic --> LO
    end

    subgraph Tier2["2. Core Question Bank & Provenance"]
        Q["Question\n- primary_topic_id (Canonical medical topic)\n- source_exam_id (Optional past exam/paper code)\n- external_source: medmcqa | manual | ai\n- stem, options, explanation, content_hash"]
        Exam["Source / Historical Exam\n(e.g., NEET-PG-2021, AIIMS-MAY-2018)"]
        Exam -.->|source_exam_id| Q
    end

    subgraph Tier3["3. Course Curriculum Frameworks"]
        C1["Course: DM-ONCOPATH\n(Depth: super_specialty, Weight: 20%)"]
        C2["Course: MD-PATH\n(Depth: postgraduate, Weight: 10%)"]
        C3["Course: MBBS-PATH\n(Depth: undergraduate, Weight: 5%)"]
    end

    Q ==>|primary_topic_id| Topic
    Topic ==>|CourseCurriculumMapping| C1
    Topic ==>|CourseCurriculumMapping| C2
    Topic ==>|CourseCurriculumMapping| C3
```

1. **Canonical Medical Taxonomy (`CurriculumTopic`)**: Exam-agnostic medical hierarchy:
   $$\text{Speciality} \longrightarrow \text{Subject} \longrightarrow \text{Topic} \longrightarrow \text{Subtopic} \longrightarrow \text{Learning Objective}$$
2. **Course Curriculum (`Course` & `CourseCurriculumMapping`)**: Academic programs (`MBBS`, `MD`, `DM`, `NEET-PG`) declare required topics with course-specific depth expectations (`undergraduate`, `postgraduate`, `super_specialty`) and exam weightages.
3. **Question Provenance (`source_exam_id` & `external_source`)**: Historical past-paper provenance is tracked without artificially restricting questions to a single syllabus.

---

## 2. Monorepo Structure

The platform is structured as a **Bun-powered monorepo** with shared typed packages and isomorphic APIs:

```
medical-learning-intelligence/
├── package.json                  # Root Bun workspace configuration
├── bunfig.toml                   # Bun package manager configuration
│
├── packages/
│   ├── shared/                   # @medical/shared (TS Types & Zod Schemas)
│   │   ├── src/
│   │   │   ├── types/            # Question, Topic, Assessment, Scoring models
│   │   │   ├── schemas/          # Zod validation schemas
│   │   │   └── index.ts
│   │   └── tsdown.config.ts      # Rolldown-powered library bundler (dual ESM/CJS)
│   │
│   └── api-client/               # @medical/api-client (Isomorphic HTTP API SDK)
│       ├── src/
│       │   ├── client.ts         # Base HTTP client with error handling
│       │   ├── assessments.ts    # Endpoints matching FastAPI backend
│       │   └── index.ts
│       └── tsdown.config.ts
│
├── apps/
│   ├── web/                      # Next.js 14 Web Portal (Admin + Student)
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── page.tsx                          # Overview & Launchpad
│   │   │   │   ├── student/page.tsx                  # Student Practice & 1-Click Presets
│   │   │   │   ├── student/exam/[attemptId]/page.tsx # Timed Exam Runner & Palette
│   │   │   │   ├── student/results/[attemptId]/page.tsx # Diagnostic Scorecard
│   │   │   │   ├── student/review/[attemptId]/page.tsx  # Ground Truth & Citations Review
│   │   │   │   └── admin/page.tsx                    # Question Bank Curation Portal
│   │   │   ├── components/ui/    # Clean Shadcn UI (Button, Card, Badge, Progress, Separator)
│   │   │   └── styles/globals.css # Dark-mode medical theme tokens & glassmorphism
│   │
│   └── student-native/           # React Native / Expo workspace scaffold
│       └── src/index.ts          # Ready to consume @medical/shared and @medical/api-client
│
├── backend/                      # FastAPI Universal Assessment Engine (Port 8000)
│   ├── api/
│   │   ├── main.py               # Main FastAPI app & CORS middleware
│   │   └── routes/assessments.py # Presets, attempt runner sync, scoring & reviews
│   └── services/                 # AssessmentService business logic
│
├── database/                     # PostgreSQL 16 schema & SQLAlchemy models
├── data/                         # Data pipeline storage (raw/ & processed/)
└── scripts/                      # Data pipeline & DB seeders
```

---

## 3. Currently Implemented Capabilities

- **MedMCQA Pathology Ingestion Pipeline**: Ingestion and normalization of **15,526** Pathology questions (15,221 labeled questions with 98.04% explanation coverage).
- **Universal Assessment Engine (FastAPI)**: Complete backend for 1-click exam presets (*NEET-SS Oncopathology*, *NEET-PG Sprint*, *Daily Dose*), sub-second heartbeat state sync, and +4 / -1 scoring computation.
- **Next.js Web Client (`apps/web`)**:
  - **Launchpad**: Interactive overview with live platform stats and exam triggers.
  - **Student Hub**: 1-click test launcher and instant attempt creation.
  - **Active Timed Exam Runner**: Live countdown timer, Question Palette matrix, response sync, marked-for-review toggle, and submission modal.
  - **Diagnostic Scorecard**: Raw marks (+4 / -1 penalties), accuracy %, time spent, and topic mastery progress bars with celebration confetti.
  - **Question Review**: Side-by-side ground truth vs student answer highlighting with *Robbins & Cotran* and *WHO Blue Books* citations.
  - **Admin Curation Portal**: Question bank search, topic filtering, status transitions, and duplicate cluster detection.
- **`tsdown` (Rolldown) Library Bundling**: Lightning-fast build pipeline for `@medical/shared` and `@medical/api-client` producing dual ESM (`.mjs`) / CJS (`.cjs`) and `.d.ts` types.
- **Zero Data-Loss Deduplication**: SHA-256 content hashing and normalized stem clustering without discarding records.
- **PostgreSQL 16 Persistence Layer**: Full schema with custom ENUMs, JSONB options/metadata, and indexed relationships.

---

## 4. Quickstart & Local Development

Prerequisites: Docker Desktop, Python 3.11/3.12, and Bun 1.4+.

```bash
# Configure and install
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
bun install --frozen-lockfile

# Start PostgreSQL and Redis
docker compose -f infrastructure/docker-compose.yml up -d

# Initialize curriculum (then optionally reproduce/import MedMCQA)
python -m scripts.seed_curriculum
python scripts/run_pipeline.py
python scripts/import_to_db.py

# Run backend and web in separate terminals
python -m uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000
bun run dev:web
```

Open the web app at `http://localhost:3000`, the API at `http://127.0.0.1:8000`, and API documentation at `http://127.0.0.1:8000/docs`.

The dataset download/import is optional for booting the application but required to run question-based exams. For Windows commands, mobile networking, database verification, test/build commands, and troubleshooting, follow [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md).

---

## 5. Current Roadmap

- Milestones 1–8: data pipeline, PostgreSQL model, curriculum, assessment engine, selection, identity, web experience, and Expo student app.
- [Milestone 9](MileStones/MileStone9.md): security hardening, ownership, course/bundle entitlements, migrations, and reporting.
- Milestone 10: production hosting, managed services, database release migrations, CI/CD, and native app publishing.
- Milestone 11: architecture and multi-developer documentation.
- Milestone 12: Python/React/React Native review and shared-component architecture.
- Milestone 13: landing-page widget CMS.

See [docs/ROADMAP.md](docs/ROADMAP.md) and the specifications in [`MileStones/`](MileStones/) for detailed scope.

---

## 6. License & Medical Disclaimer

This platform is developed for medical education and examination preparation. Educational content and question banks do not constitute autonomous clinical diagnostic advice.
