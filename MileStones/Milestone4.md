# Milestone 4 — Repository Stabilization & Baseline GitHub Preparation

## 1. Objective

Perform a comprehensive repository audit, eliminate redundant artifacts, structure documentation and data reproducibility pipelines, configure `.gitignore` for zero secrets/data leakage, and prepare the project for its clean, professional initial GitHub baseline commit.

> [!IMPORTANT]
> **No new feature development** during this milestone. The focus is stability, cleanliness, reproducibility, documentation, and Git hygiene.

---

## 2. Repository Audit & Cleanup Checklist

Inspect and clean the workspace according to these rules:

### A. Identify & Eliminate Redundant Files
- **Obsolete Scripts**: Remove temporary/duplicate scratch scripts (e.g. `scripts/extract_path.py` which was superseded by `scripts/extract_pathology.py`).
- **Local SQLite Artifacts**: Exclude or archive local temporary databases (e.g. `data/medical_exam.db`), ensuring PostgreSQL is the sole canonical persistence engine.
- **Cache Directories**: Ensure all Python bytecode caches (`__pycache__/`, `*.pyc`), pytest caches (`.pytest_cache/`), and test artifacts are properly ignored.

### B. Standardized Project Structure
Ensure consistent directory layout across backend, data, and docs:

```
medical-exam-ai/
├── README.md
├── AGENTS.md
├── .gitignore
├── .env.example
├── docker-compose.yml (or infrastructure/docker-compose.yml)
│
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── ROADMAP.md
│   └── DATA_SOURCES.md
│
├── backend/
│   └── ingestion/
│       ├── __init__.py
│       └── universal_ingestor.py
│
├── database/
│   ├── __init__.py
│   ├── db.py
│   ├── models.py
│   └── schema.sql
│
├── scripts/
│   ├── import_medmcqa.py
│   ├── extract_pathology.py
│   ├── normalize_medmcqa.py
│   ├── deduplicate_questions.py
│   ├── run_pipeline.py
│   ├── import_to_db.py
│   ├── ingest_cli.py
│   └── seed_curriculum.py
│
├── tests/
│   ├── __init__.py
│   ├── test_pipeline.py
│   ├── test_database.py
│   └── test_universal_ingestion.py
│
├── data/
│   ├── README.md
│   ├── raw/
│   │   └── medmcqa/ (ignored by git, kept via .gitkeep)
│   └── processed/
│       └── pathology/ (ignored by git, kept via .gitkeep)
│
└── infrastructure/
    └── docker-compose.yml
```

---

## 3. Git-Safe Data Handling & `.gitignore`

Large raw datasets and secrets must **NEVER** be committed to Git.

### Excluded Artifacts:
- **Raw Parquet Files**: `train.parquet` (~85.9 MB), `validation.parquet`, `test.parquet`.
- **Processed Datasets**: `pathology_all.jsonl` (~30.9 MB), `pathology_labeled.jsonl` (~30.5 MB), `pathology_train.jsonl`, etc.
- **Environment & Secrets**: `.env`, `.env.local`, connection credentials, API keys.
- **Local DBs & Caches**: `*.db`, `*.sqlite`, `*.sqlite3`, `__pycache__/`, `*.log`.

### Included / Tracked Artifacts:
- All source code, migrations, schemas, scripts, and tests.
- `.env.example` (clean template with placeholders).
- Documentation files (`docs/*.md`, `README.md`, `data/README.md`).
- Directory placeholders (`data/raw/medmcqa/.gitkeep`, `data/processed/pathology/.gitkeep`).

### Recommended `.gitignore` Configuration:
```gitignore
# Environment & Secrets
.env
.env.*
!.env.example

# Python Caches & Virtual Environments
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.coverage
htmlcov/
.venv/
venv/
ENV/

# Node & Frontend (for upcoming Next.js UI)
node_modules/
.next/
dist/
build/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# IDE & OS Files
.idea/
.vscode/
*.swp
*.swo
.DS_Store
Thumbs.db

# Database & Logs
*.db
*.sqlite
*.sqlite3
*.log
data/medical_exam.db

# Data Pipeline (Large Datasets - Generated via scripts/run_pipeline.py)
data/raw/medmcqa/*
!data/raw/medmcqa/.gitkeep
data/processed/pathology/*
!data/processed/pathology/.gitkeep
!data/processed/pathology/manifest.json
!data/processed/pathology/summary_report.json

# Documentation Exception
!data/README.md
```

---

## 4. Data Reproducibility (`data/README.md`)

Create `data/README.md` explaining how any developer cloning the repository can reproduce the entire data pipeline in one command:

```markdown
# Medical Exam AI — Data Pipeline & Dataset Reproduction

## Data Privacy & Git Policy
Raw MedMCQA Parquet files and large generated JSONL files are excluded from version control to maintain a lightweight, reproducible codebase.

## Dataset Reproduction Guide

### 1. Ingest Raw MedMCQA
Run the download script to fetch the official MedMCQA splits into `data/raw/medmcqa/`:
```bash
python scripts/import_medmcqa.py
```

### 2. Execute Pathology Pipeline
Extract, normalize, deduplicate, and generate processed JSONL datasets:
```bash
python scripts/run_pipeline.py
```
This generates:
- `data/processed/pathology/pathology_all.jsonl` (15,526 questions)
- `data/processed/pathology/pathology_labeled.jsonl` (15,221 questions)
- Split files (`train`, `validation`, `test`) and `summary_report.json`.

### 3. Seed Database
Start PostgreSQL via Docker and import into the database:
```bash
docker compose -f infrastructure/docker-compose.yml up -d
python scripts/import_to_db.py
```
```

---

## 5. Documentation Deliverables

Ensure the following 5 documents are up-to-date, accurate, and professional:

1. [README.md](file:///R:/Repositories/medical-exam-ai/README.md):
   - Project Vision (Pathology focus $\rightarrow$ MBBS/MD/DM multi-specialty expansion).
   - System Architecture Diagram & 3-Tier Domain Decoupling.
   - Quickstart Setup (Docker, Environment, Ingestion commands).
   - Test Execution (`python -m unittest discover tests`).
   - Roadmap (Phases 1 through 6).
2. [docs/PRD.md](file:///R:/Repositories/medical-exam-ai/docs/PRD.md): Product requirements and milestone tracker.
3. [docs/ARCHITECTURE.md](file:///R:/Repositories/medical-exam-ai/docs/ARCHITECTURE.md): System architecture, ML service isolation, and engineering guidelines.
4. [docs/DATA_MODEL.md](file:///R:/Repositories/medical-exam-ai/docs/DATA_MODEL.md): ERD, entity specifications, 3-tier decoupling (Taxonomy vs Curriculum vs Provenance), and `question_courses` roadmap.
5. [docs/DATA_SOURCES.md](file:///R:/Repositories/medical-exam-ai/docs/DATA_SOURCES.md): Authoritative reference corpus (Robbins, WHO Blue Books, Sternberg, Rosai & Ackerman, Dabbs IHC, Koss Cytology) and MedMCQA dataset provenance rules.

---

## 6. Architecture Verification Check

Confirm the repository adheres to the **Three-Tier Separation**:
1. **Medical Knowledge Taxonomy**: `questions.primary_topic_id` represents canonical medical concepts (`CurriculumTopic`).
2. **Course Curriculum**: `courses` and `course_curriculum_mappings` define academic program scopes and depth levels.
3. **Question Provenance**: `questions.source_exam_id` and `external_source` preserve historical origins (e.g. past paper tags, MedMCQA), without hardcoding questions to a single syllabus.

---

## 7. Verification & Test Suite Execution

Run the complete test suite to ensure 100% green tests:
```bash
python -m unittest discover tests
```

Verify:
- Schema initialization and model mappings.
- Provenance linkage and evidence citations.
- Universal ingestion across CSV, Google Forms, Manual, and AI candidates.
- Idempotency and batch JSONL imports.

---

## 8. Milestone Completion Deliverables

At the conclusion of this milestone, provide:
1. **Audit & Cleanup Report**: List of cleaned/pruned files.
2. **Git Status & Security Check**: Confirmation that `.env`, raw datasets, and SQLite files are untracked.
3. **Documentation Summary**: Links to updated README and docs.
4. **Test Results**: Output showing all tests passing.
5. **Recommended Git Commit Message**:
   ```
   feat: initialize core medical exam ai platform with postgresql question bank and medmcqa ingestion pipeline
   ```

> [!CAUTION]
> **STOP** after completing this milestone. Do not implement the Question Bank UI or Mock Exam Engine until this baseline is committed.