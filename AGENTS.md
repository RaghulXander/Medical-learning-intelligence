# Medical Exam AI Platform — Initial Project Specification

> [!IMPORTANT]
> **Active Development Status**: For the current active milestone, daily tasks, and live context, always refer to [ACTIVE_CONTEXT.md](file:///r:/Repositories/medical-learning-intelligence/ACTIVE_CONTEXT.md) and [MileStones/MileStone7.md](file:///r:/Repositories/medical-learning-intelligence/MileStones/MileStone7.md).

## 1. Project Vision

Build a scalable medical education and mock-exam platform.

The initial focus is **Pathology**, particularly PG/SS-level preparation, starting with DM/DrNB Oncopathology-related topics.

The long-term goal is to expand to:

* Pathology
* Other medical specialties
* MBBS
* MD/MS
* DM/MCh
* NEET-PG
* NEET-SS
* Other medical examinations

The long-term platform should support:

1. Structured question banks
2. Instant exam generation
3. Timed mock exams
4. User management
5. Performance analytics
6. Question reporting and correction
7. AI-generated questions
8. Source/evidence-backed questions
9. Eventually image-based pathology questions
10. Eventually pathology image analysis using models such as PLIP and future multimodal/pathology models
11. Eventually an AI pathology viva/tutor

Do NOT attempt to implement the entire long-term vision now.

The first milestone is a working text-based pathology question bank and mock-exam platform.

---

# 2. Current Quick MVP Goal

### Admin

* User/admin authentication
* Question bank management
* Import MedMCQA
* Extract Pathology questions
* Review questions
* Approve/reject questions
* Edit questions
* Add source references
* Report question errors

### Student

* User registration/login
* Browse pathology topics
* Start instant exam
* Select number of questions
* Select difficulty
* Take timed exam
* Submit exam
* View score
* Review answers
* Report incorrect/ambiguous questions

### AI

* Generate new MCQs
* Evaluate generated MCQs
* Detect duplicate questions
* Validate answer/explanation consistency
* Retrieve supporting medical knowledge
* Eventually use PubMedBERT-based MCQA model as one validation signal

---

# 3. Initial Data Source

The first dataset is MedMCQA.

Repository:

https://github.com/medmcqa/medmcqa

A cloned copy already exists locally.

IMPORTANT:

Do not modify the original MedMCQA repository.

Treat it as an external/raw dataset.

The MedMCQA dataset contains fields such as:

* id
* question
* opa
* opb
* opc
* opd
* cop
* choice_type
* exp
* subject_name
* topic_name

MedMCQA does NOT provide reliable textbook-level references such as:

* Robbins page/chapter
* Sternberg page/chapter
* WHO volume/page
* Koss chapter/page

Therefore NEVER invent textbook references for imported MedMCQA questions.

Our application must distinguish:

### Question origin

Where the question came from.

Example:

MedMCQA

### Knowledge evidence

Which authoritative source supports the medical answer.

Example:

Robbins & Cotran
WHO Classification
Sternberg
Diagnostic Immunohistochemistry

These are separate concepts in the data model.

---

# 4. Initial Pathology Dataset Pipeline

Build this pipeline first:

MedMCQA raw dataset
↓
Normalize schema
↓
Filter subject = Pathology
↓
Deduplicate
↓
Store processed Pathology dataset
↓
Import into application database

Create scripts such as:

scripts/
import_medmcqa.py
extract_pathology.py
normalize_medmcqa.py
deduplicate_questions.py

Do not lose the original MedMCQA ID.

Use something such as:

medmcqa-{original_id}

as the external/source identifier.

---

# 5. Application Question Model

Our question model should contain substantially more metadata than MedMCQA.

Conceptually:

Question

* id
* external_source
* external_source_id
* speciality
* subject
* topic
* subtopic
* learning_objective
* question_type
* stem
* options
* correct_option
* explanation
* difficulty
* cognitive_level
* status
* quality_score
* created_by
* created_at
* updated_at

Question statuses:

IMPORTED
GENERATED
AI_REVIEW
HUMAN_REVIEW
APPROVED
REJECTED
REPORTED
RETIRED

---

# 6. Source/Evidence Model

Create a separate source system.

A question may have zero or multiple supporting sources.

Example:

Question
↓
QuestionEvidence
↓
Source

Source should support:

* title
* author
* edition
* year
* publisher
* volume
* chapter
* page/range
* section
* source_type

IMPORTANT:

For AI-inferred source mappings, store confidence and verification state.

Example:

source_verification_status:

AI_SUGGESTED
HUMAN_VERIFIED
REJECTED

Never represent an AI-inferred textbook reference as a verified reference.

---

# 7. Initial Pathology Knowledge Sources

The planned authoritative pathology corpus includes:

1. Diagnostic Immunohistochemistry
2. Diagnostic Flow Cytometry
3. Robbins & Cotran
4. Sternberg Surgical Pathology
5. Ackerman Surgical Pathology
6. WHO Blue Books
7. WHO Classification of Haematolymphoid Tumours
8. WHO Classification of Myeloid Neoplasms
9. Koss Cytology

More review books and resources will be added later.

IMPORTANT COPYRIGHT RULE:

Do not download or ingest pirated copyrighted textbooks.

The knowledge ingestion pipeline should support legitimately obtained documents/content.

---

# 8. Knowledge/RAG Architecture

Eventually implement:

Source documents
↓
Document parser
↓
Chunking
↓
Metadata extraction
↓
Embeddings
↓
Vector database
↓
Semantic retrieval
↓
Evidence returned to question generator/evaluator

Use metadata such as:

* speciality
* subject
* topic
* source
* edition
* chapter
* page
* section

The system must preserve provenance.

A generated question should ideally be traceable to the evidence used to generate it.

---

# 9. Question Generation Architecture

Do NOT simply ask an LLM:

"Generate 10 pathology questions."

Instead:

Topic
↓
Learning objective
↓
Retrieve relevant evidence
↓
Create question blueprint
↓
Generate MCQ
↓
Generate explanation
↓
Attach evidence
↓
Evaluate
↓
Store candidate
↓
Human review
↓
Approve

Question blueprint should contain:

* speciality
* subject
* topic
* subtopic
* learning objective
* difficulty
* cognitive level
* question type
* source requirements

Example:

{
"topic": "Breast carcinoma",
"learning_objective": "HER2 testing",
"difficulty": "hard",
"cognitive_level": "application",
"question_type": "single_best_answer"
}

---

# 10. MedMCQA Usage

MedMCQA should be used for:

1. Existing question bank
2. Benchmarking
3. Understanding exam question style
4. Few-shot examples for generation
5. Evaluation of question-answering models
6. Topic distribution analysis

Do NOT assume MedMCQA textbook provenance.

Do NOT automatically treat MedMCQA answers as authoritative medical truth.

---

# 11. PubMedBERT Model

Initial Hugging Face model:

jamezoon/medmcqa-pubmedbert-mcqa

Hugging Face:

https://huggingface.co/jamezoon/medmcqa-pubmedbert-mcqa

This model is NOT the primary question generator.

Treat it as a possible MCQ answer-validation/classification signal.

Create a separate Python ML service.

Suggested architecture:

Node.js API
↓
Python FastAPI ML service
↓
PubMedBERT

Example endpoint:

POST /predict

Input:

{
"question": "...",
"options": [
"...",
"...",
"...",
"..."
]
}

Output:

{
"prediction": "B",
"probabilities": {
"A": 0.10,
"B": 0.70,
"C": 0.10,
"D": 0.10
}
}

IMPORTANT:

Do not treat PubMedBERT prediction as ground truth.

Use it as one signal in an evaluator.

---

# 12. Question Evaluation

Create a Question Evaluation pipeline.

Potential checks:

1. Answer consistency
2. Explanation consistency
3. Source/evidence support
4. Distractor quality
5. Duplicate detection
6. Topic correctness
7. Difficulty estimation
8. Cognitive-level estimation
9. Medical ambiguity
10. Model agreement

Eventually:

LLM evaluator
+
PubMedBERT
+
source verification
+
duplicate detector
+
human review

→ quality score

AI-generated questions should NOT automatically become production questions.

---

# 13. Question Review Workflow

Generated question:

GENERATED
↓
AI_REVIEW
↓
HUMAN_REVIEW
↓
APPROVED

Alternative:

AI_REVIEW
↓
FAILED
↓
REGENERATE

Production exam questions should normally have:

status = APPROVED

---

# 14. User Feedback Loop

Users must be able to report questions.

Report categories:

* Incorrect answer
* Incorrect explanation
* Ambiguous question
* Multiple possible answers
* Poor wording
* Wrong topic
* Wrong difficulty
* Outdated information
* Source/reference problem
* Other

Workflow:

User report
↓
QuestionReport
↓
Admin review
↓
Correct / edit / retire
↓
Record resolution

This feedback will eventually become training/evaluation data.

---

# 15. Exam Engine

An exam is generated from an exam blueprint.

Example:

{
"speciality": "Pathology",
"questions": 50,
"difficulty": {
"easy": 10,
"medium": 25,
"hard": 15
},
"topics": {
"general_pathology": 10,
"hematopathology": 10,
"breast": 5,
"GI": 5,
"lung": 5,
"IHC": 5,
"molecular": 5,
"miscellaneous": 5
}
}

For MVP, simple random selection is acceptable.

Design the architecture so a smarter adaptive selection algorithm can be added later.

---

# 16. Recommended Technology

Use a modular monolith initially.

Frontend:

Next.js
TypeScript
Tailwind CSS

Backend:

Node.js
TypeScript

Database:

PostgreSQL

Vector search:

pgvector

Queue/background jobs:

Redis + BullMQ

ML:

Python
FastAPI
PyTorch
Hugging Face Transformers

Storage:

S3-compatible object storage

Do NOT create unnecessary microservices during MVP.

The ML service can be the only separate service initially.

---

# 17. Proposed Repository

medical-exam-ai/

├── AGENTS.md
├── README.md
│
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   └── ROADMAP.md
│
├── data/
│   ├── raw/
│   │   └── medmcqa/
│   ├── processed/
│   │   └── pathology/
│   └── knowledge/
│
├── backend/
│
├── frontend/
│
├── ml/
│   └── pubmedbert-validator/
│
├── scripts/
│   ├── extract_pathology.py
│   ├── normalize_medmcqa.py
│   ├── deduplicate_questions.py
│   └── import_medmcqa.py
│
└── infrastructure/

---

# 18. 15-Day Milestones

## Days 1–2

Project setup:

* repository
* Next.js
* Node API
* PostgreSQL
* Docker
* environment configuration
* database migrations

## Days 3–4

MedMCQA ingestion:

* inspect dataset
* normalize
* extract Pathology
* deduplicate
* database import

Deliverable:

Pathology questions visible in admin UI.

## Days 5–6

PubMedBERT:

* Python service
* model loading
* prediction endpoint
* benchmark against Pathology questions

## Days 7–9

Question generation:

* LLM integration
* structured question generation
* question blueprint
* evaluator
* candidate question storage

## Days 10–11

Question bank:

* filters
* search
* edit
* review
* approve/reject
* source metadata

## Days 12–13

Exam engine:

* exam blueprint
* instant exam
* timer
* submission
* scoring
* review

## Days 14–15

Feedback and analytics:

* question reporting
* user attempts
* basic performance analytics
* admin dashboard
* error correction workflow

---

# 19. Future Architecture

Do not implement these now, but preserve extension points for:

### Additional LLMs

* MedGemma
* other medical LLMs
* general LLMs

### Image models

* PLIP
* pathology-specific vision models
* future multimodal models

### Image workflow

Image
↓
Vision model
↓
Morphology
↓
Differential diagnosis
↓
Knowledge retrieval
↓
Educational interpretation

### AI Viva

Image/case
↓
AI examiner
↓
Interactive questions
↓
User answers
↓
Adaptive follow-up
↓
Score

---

# 20. Critical Engineering Rules

1. Do not over-engineer the MVP.
2. Do not create microservices unless there is a real need.
3. Preserve source provenance everywhere.
4. Never invent medical references.
5. Never treat AI-generated citations as verified.
6. Never automatically publish AI-generated questions.
7. Keep raw datasets immutable.
8. Keep processing scripts reproducible.
9. Keep ML code isolated from the Node application.
10. Use TypeScript types/shared schemas where appropriate.
11. Use database migrations.
12. Write tests for important data-processing functions.
13. Keep model providers replaceable.
14. Never hard-code a specific LLM provider into business logic.
15. Design the question model so image questions can be added later.
16. Design speciality/course/topic hierarchy to support MBBS → PG → SS expansion.
17. Do not ingest copyrighted textbook material unless the project has legitimate rights/access.
18. Medical content is educational; do not position the MVP as an autonomous clinical diagnostic system.

---

# 21. First Task for the Coding Agent

DO NOT start by building the entire application.

First inspect the existing MedMCQA clone and determine:

1. Exact dataset files available.
2. Dataset formats.
3. Actual field names.
4. Train/validation/test structure.
5. How Pathology is represented.
6. Number of Pathology questions.
7. Number of unique Pathology topics.
8. Any duplicate IDs/questions.
9. Whether explanations are present.
10. Whether any provenance/reference metadata exists.

Then produce a short report.

After the report, implement ONLY:

* project structure
* MedMCQA ingestion script
* Pathology extraction
* normalized JSONL output
* tests for the extraction/normalization pipeline

Do not build the frontend, exam engine, RAG, or question generator yet.

Wait for the next milestone after this is complete.

---

# 22. Development Philosophy

This is an AI-assisted development project.

The coding agent should:

* inspect before modifying
* explain architectural decisions briefly
* make small incremental changes
* run tests after changes
* avoid unnecessary dependencies
* avoid speculative abstractions
* preserve existing data
* use TODOs for future functionality rather than implementing prematurely

The goal is a working product in 15 days, not a theoretically perfect architecture.

Start with the data pipeline.
