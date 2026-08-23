# Medical Exam AI — Data Pipeline & Dataset Reproduction

This directory manages external raw data sources and processed medical question datasets.

---

## 1. Data Privacy & Git Policy

To maintain a clean, lightweight, and fast repository:
- **Raw Parquet/CSV files** (e.g. MedMCQA raw splits ~86 MB) are excluded from version control via `.gitignore`.
- **Large generated JSONL files** (e.g. `pathology_all.jsonl` ~31 MB, `pathology_labeled.jsonl` ~30.5 MB) are excluded from version control.
- **Reproducibility Manifests** ([manifest.json](file:///R:/Repositories/medical-exam-ai/data/processed/pathology/manifest.json) and [summary_report.json](file:///R:/Repositories/medical-exam-ai/data/processed/pathology/summary_report.json)) are tracked to guarantee deterministic, verifiable builds.

---

## 2. Dataset Reproduction Workflow

Anyone cloning this repository can reproduce the entire Pathology dataset from scratch with deterministic verification:

### Step 1: Download Raw MedMCQA Splits
Download the official MedMCQA dataset splits into `data/raw/medmcqa/`:
```bash
python scripts/import_medmcqa.py
```
This fetches:
- `data/raw/medmcqa/train.parquet` (182,822 questions)
- `data/raw/medmcqa/validation.parquet` (4,183 questions)
- `data/raw/medmcqa/test.parquet` (6,150 questions)

### Step 2: Run Pathology Ingestion & Normalization Pipeline
Filter for Pathology, sanitize text while preserving medical symbols, decouple topics, compute SHA-256 deduplication hashes, and export JSONL files:
```bash
python scripts/run_pipeline.py
```

Outputs produced under `data/processed/pathology/`:
- `pathology_all.jsonl` — All **15,526** Pathology questions (train + val + test).
- `pathology_labeled.jsonl` — **15,221** labeled questions with ground truth answers and explanations.
- `pathology_train.jsonl` — 14,884 training questions.
- `pathology_validation.jsonl` — 337 validation questions.
- `pathology_test.jsonl` — 305 benchmark test questions.
- `summary_report.json` & `manifest.json` — Comprehensive summary report with data quality metrics.

### Step 3: Seed & Import into PostgreSQL Database
Ensure Docker is running, then initialize schema, seed authoritative curriculum taxonomy, and batch-import questions:
```bash
# Start PostgreSQL (pgvector) & Redis
docker compose -f infrastructure/docker-compose.yml up -d

# Seed taxonomy and import questions
python scripts/import_to_db.py
```

---

## 3. Dataset Attribution & Integrity Rules

- **Source Dataset**: MedMCQA ([arXiv:2203.14361](https://arxiv.org/abs/2203.14361) / [GitHub](https://github.com/medmcqa/medmcqa)).
- **Provenance Rule**: MedMCQA answers and explanations are educational inputs; they do not carry verified textbook-level citations. The platform never hallucinates or invents textbook references for imported MedMCQA questions.
