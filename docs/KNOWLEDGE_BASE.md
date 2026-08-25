# Medical Knowledge Base & RAG Architecture

**Project:** Medical Examination Intelligence Platform
**Document:** Knowledge Base, RAG & Question Generation Architecture
**Status:** Experimental / MVP
**Primary Initial Domain:** Pathology / Oncopathology
**Future Domains:** MBBS, MD/MS, DM/MCh, NEET-PG, NEET-SS and other medical specialties

---

## 1. Purpose

This document defines the architecture for building a structured medical knowledge base from authorized digital/reference material and using it as the evidence layer for:

1. Retrieval-Augmented Generation (RAG)
2. Medical question generation
3. Question explanation generation
4. Question validation
5. Evidence-backed answers
6. Curriculum mapping
7. Learning-objective generation
8. User error analysis
9. Future personalized learning
10. Future medical image/diagnostic AI systems

The knowledge base is deliberately separated from the question bank.

The core principle is:

> **Books and authoritative references provide knowledge and evidence. Questions are derived artifacts.**

The same knowledge base should eventually support multiple products and specialties.

---

# 2. Initial Scope

The first implementation focuses on Pathology and Oncopathology.

### Primary reference sources

* Robbins and Cotran Pathologic Basis of Disease
* Robbins and Cotran Review of Pathology
* Diagnostic Immunochemistry
* Diagnostic Flow Cytometry
* Sternberg's Diagnostic Surgical Pathology
* Ackerman's Surgical Pathology
* WHO Classification of Tumours / WHO Blue Books
* WHO Classification of Haematolymphoid Tumours
* WHO Classification of Myeloid Neoplasms and Acute Leukaemias
* Koss' Diagnostic Cytology and its Histopathologic Bases

Additional review books, guidelines, articles and educational resources may be added later.

---

# 3. Important Content Principle

The system must distinguish between:

### Knowledge source

Examples:

* textbook
* WHO classification
* guideline
* review article
* educational reference

### Question source

Examples:

* MedMCQA
* previous examination
* manually authored question
* Google Forms submission
* educator-created question
* AI-generated question
* imported question corpus

A question should never automatically become authoritative merely because it cites a textbook.

---

# 4. High-Level Architecture

```text
                         MEDICAL KNOWLEDGE BASE
                                  |
              +-------------------+-------------------+
              |                   |                   |
          Textbooks             WHO               Guidelines
              |                   |                   |
              +-------------------+-------------------+
                                  |
                             Ingestion
                                  |
                         Document Processing
                                  |
                    +-------------+-------------+
                    |                           |
               Raw Document                Metadata
                    |                           |
                    +-------------+-------------+
                                  |
                             Chunking
                                  |
                         Semantic Enrichment
                                  |
                 +----------------+----------------+
                 |                                 |
             Embeddings                       Metadata
                 |                                 |
                 +----------------+----------------+
                                  |
                            Vector Store
                                  |
                           Retrieval Layer
                                  |
                 +----------------+----------------+
                 |                                 |
             Question                         Explanation
             Generation                       Generation
                 |                                 |
                 +----------------+----------------+
                                  |
                            Validation
                                  |
                         Evidence Verification
                                  |
                       AI_REVIEW / Human Review
                                  |
                         Approved Question Bank
```

---

# 5. Knowledge Base vs Question Bank

These should remain separate systems.

## Knowledge Base

Contains:

```text
Document
Chapter
Section
Paragraph
Chunk
Evidence
Citation
Embedding
Topic
Subtopic
Learning Objective
```

## Question Bank

Contains:

```text
Question
Options
Correct Answer
Explanation
Difficulty
Cognitive Level
Topic
Subtopic
Learning Objective
Question Source
Evidence References
Quality Score
Review Status
```

Relationship:

```text
Knowledge Base
      |
      | provides evidence
      v
Question Generator
      |
      v
Question Bank
```

---

# 6. Document Registry

Every imported source should have a document record.

Suggested structure:

```text
KnowledgeDocument
├── id
├── title
├── author
├── publisher
├── edition
├── publication_year
├── source_type
├── specialty
├── language
├── file_hash
├── file_format
├── ingestion_method
├── status
├── license_metadata
├── created_at
└── updated_at
```

### Example

```json
{
  "title": "Robbins and Cotran Pathologic Basis of Disease",
  "edition": 11,
  "source_type": "TEXTBOOK",
  "specialty": "PATHOLOGY",
  "file_format": "PDF",
  "status": "ACTIVE"
}
```

---

# 7. Source Types

The system should support:

```text
TEXTBOOK
REFERENCE_BOOK
WHO_CLASSIFICATION
GUIDELINE
REVIEW_ARTICLE
JOURNAL_ARTICLE
LECTURE_NOTE
EDUCATIONAL_DOCUMENT
PREVIOUS_EXAM
MANUAL_REFERENCE
```

Question sources should use a different enumeration:

```text
MEDMCQA
PREVIOUS_EXAM
GOOGLE_FORM
MANUAL
EDUCATOR
AI_GENERATED
IMPORTED
```

---

# 8. Document Ingestion Pipeline

```text
PDF / EPUB / HTML / DOCX
          |
          v
     File Validation
          |
          v
   Text Extraction
          |
          v
     OCR if needed
          |
          v
   Page Preservation
          |
          v
  Chapter Detection
          |
          v
 Section Detection
          |
          v
 Semantic Chunking
          |
          v
 Metadata Enrichment
          |
          v
 Embedding Generation
          |
          v
 Vector Database
```

---

# 9. PDF Processing

The system should first determine whether the document is:

1. Text-native PDF
2. Scanned PDF
3. Mixed PDF

Preferred processing order:

```text
PDF
 |
 +-- Text available?
 |       |
 |      YES
 |       |
 |   PyMuPDF / equivalent
 |
 NO
 |
 OCR
 |
 OCRmyPDF / Tesseract / equivalent
```

Text extraction must preserve:

* page number
* chapter
* section
* headings
* tables where possible
* figure references
* captions
* footnotes
* references

---

# 10. Page-Level Provenance

Every chunk must retain its source location.

Example:

```json
{
  "document_id": "robbins-11",
  "chapter": "Neoplasia",
  "section": "Molecular Basis of Cancer",
  "page_start": 265,
  "page_end": 267
}
```

This enables:

> "Show the evidence used to generate this question."

---

# 11. Chunking Strategy

Do not blindly split every document into fixed 500-token chunks.

Medical textbooks have semantic structures.

Preferred hierarchy:

```text
Document
  |
  +-- Chapter
       |
       +-- Section
            |
            +-- Subsection
                 |
                 +-- Paragraph / Table / Figure
```

Then create semantic chunks.

### Initial target

Approximately:

```text
300–800 tokens
```

with overlap where required.

The exact chunk size should be evaluated experimentally.

---

# 12. Special Handling of Tables

Tables are highly valuable in pathology.

Examples:

* WHO classification tables
* immunohistochemistry panels
* differential diagnosis tables
* molecular alterations
* staging tables
* diagnostic criteria

Do not flatten a table into meaningless text.

Represent it as:

```text
Table
├── title
├── headers
├── rows
├── source_document
└── source_page
```

A table may also be converted into a textual representation for embedding.

---

# 13. Special Handling of Figures

Figures may contain clinically important information.

Initially:

```text
Figure
├── caption
├── source page
└── image reference
```

Later:

```text
Figure
├── image embedding
├── visual features
├── caption
└── diagnostic labels
```

This becomes the foundation for the future image-based diagnostic system.

---

# 14. Knowledge Chunk Schema

Recommended conceptual schema:

```text
KnowledgeChunk
├── id
├── document_id
├── chapter
├── section
├── subsection
├── content
├── content_type
├── page_start
├── page_end
├── topic_id
├── subtopic_id
├── learning_objective_id
├── embedding
├── metadata
├── content_hash
├── created_at
└── updated_at
```

---

# 15. Medical Ontology Mapping

Knowledge chunks should eventually map to the project's canonical curriculum.

```text
Course
  |
  v
Speciality
  |
  v
Subject
  |
  v
Topic
  |
  v
Subtopic
  |
  v
Learning Objective
```

Example:

```text
DM-ONCOPATH
   |
   +-- Oncopathology
        |
        +-- Breast
             |
             +-- Breast Carcinoma
                  |
                  +-- HER2 Testing
                       |
                       +-- HER2 IHC Scoring
```

A document's native chapter name must be preserved.

Do not overwrite the original source terminology.

Use:

```text
source_section
canonical_topic_id
mapping_status
```

---

# 16. Mapping Status

Suggested values:

```text
UNMAPPED
AUTO_MAPPED
AI_SUGGESTED
HUMAN_VERIFIED
```

Example:

```json
{
  "source_section": "Tumors of the Breast",
  "canonical_topic_id": "TOPIC-BREAST-PATH",
  "mapping_status": "AI_SUGGESTED"
}
```

---

# 17. Embedding Layer

Every knowledge chunk should receive an embedding.

Conceptually:

```text
Chunk
  |
  v
Embedding Model
  |
  v
Vector
  |
  v
Vector Database
```

Embedding models should remain configurable.

Do not hard-code a single embedding model into the architecture.

Suggested configuration:

```env
EMBEDDING_PROVIDER=...
EMBEDDING_MODEL=...
VECTOR_DATABASE=...
```

---

# 18. Vector Database

The MVP may use:

* PostgreSQL + pgvector

This is preferred initially because the application already uses PostgreSQL.

Architecture:

```text
PostgreSQL
 |
 +-- application tables
 |
 +-- question bank
 |
 +-- curriculum
 |
 +-- knowledge metadata
 |
 +-- pgvector
       |
       +-- knowledge embeddings
       +-- future question embeddings
```

A dedicated vector database can be introduced later if scale requires it.

---

# 19. Retrieval Strategy

Do not use vector similarity alone.

Use hybrid retrieval:

```text
User Query
    |
    +---- Semantic Search
    |
    +---- Keyword Search
    |
    +---- Metadata Filtering
    |
    +---- Curriculum Filtering
    |
    +---- Source Filtering
    |
    +---- Reranking
    |
    v
Top Evidence
```

Example query:

> HER2 scoring in invasive breast carcinoma

Filters:

```text
speciality = Pathology
topic = Breast
subtopic = HER2
source = Robbins / WHO
```

Then perform semantic retrieval.

---

# 20. RAG Pipeline

```text
Question Blueprint
       |
       v
Query Construction
       |
       v
Hybrid Retrieval
       |
       v
Top-K Evidence
       |
       v
Reranking
       |
       v
Context Assembly
       |
       v
LLM
       |
       v
Structured Output
```

---

# 21. Question Generation

Question generation should be driven by a blueprint.

Example:

```json
{
  "topic": "Breast Pathology",
  "subtopic": "HER2 Testing",
  "difficulty": "HARD",
  "cognitive_level": "APPLICATION",
  "question_type": "SINGLE_BEST_ANSWER",
  "question_count": 10
}
```

The generator retrieves relevant evidence and generates questions against that evidence.

---

# 22. Question Generation Prompt Architecture

The generator should receive:

```text
SYSTEM INSTRUCTIONS

QUESTION BLUEPRINT

CURRICULUM CONTEXT

RETRIEVED EVIDENCE

QUESTION STYLE EXAMPLES

OUTPUT SCHEMA
```

The model should return structured JSON.

Example:

```json
{
  "stem": "...",
  "options": [
    {"key": "A", "text": "..."},
    {"key": "B", "text": "..."},
    {"key": "C", "text": "..."},
    {"key": "D", "text": "..."}
  ],
  "correct_option": "B",
  "explanation": "...",
  "difficulty": "MEDIUM",
  "cognitive_level": "APPLICATION",
  "evidence_ids": [
    "chunk-123",
    "chunk-456"
  ]
}
```

---

# 23. Evidence-First Generation

The model must not be allowed to generate a medical question purely from its pretrained knowledge when the application is operating in evidence-backed mode.

Preferred:

```text
Evidence
  ↓
Question
  ↓
Answer
  ↓
Explanation
```

rather than:

```text
LLM
 ↓
Question
```

This reduces unsupported medical claims.

---

# 24. Question Validation

Every AI-generated question should pass multiple checks.

```text
Generated Question
       |
       +-- Schema validation
       |
       +-- Option validation
       |
       +-- Answer validation
       |
       +-- Evidence validation
       |
       +-- Duplicate detection
       |
       +-- Difficulty evaluation
       |
       +-- Cognitive-level evaluation
       |
       +-- Medical consistency
       |
       +-- Explanation validation
       |
       v
    AI_REVIEW
```

---

# 25. Evidence Validation

The validator should check:

```text
Is the correct answer supported by the retrieved evidence?

Does the explanation accurately represent the evidence?

Does the question introduce information not present in the evidence?

Are there conflicting references?

Is the evidence current?
```

Output:

```json
{
  "evidence_supported": true,
  "confidence": 0.94,
  "issues": []
}
```

---

# 26. Conflicting Sources

Medical references may disagree because of:

* edition differences
* classification updates
* WHO revisions
* guideline changes
* terminology changes

The system must preserve source identity.

Example:

```text
Robbins 11th Edition
WHO 5th Edition
WHO 6th Edition
```

Never merge conflicting statements into one anonymous chunk.

Instead:

```text
Evidence A
Evidence B
Conflict detected
```

Then flag for review.

---

# 27. Source Priority

A configurable source-priority system should eventually exist.

Example:

```text
WHO Classification
      >
Major Current Guideline
      >
Major Textbook
      >
Review Book
      >
Review Article
      >
Educational Material
```

The exact priority should depend on the question.

For classification questions, WHO may take precedence.

For foundational pathology, Robbins may be preferred.

---

# 28. Question Provenance

Every generated question should maintain provenance.

Example:

```json
{
  "generation": {
    "model": "MODEL_NAME",
    "prompt_version": "v1.3",
    "generated_at": "...",
    "blueprint_id": "...",
    "retrieval_id": "..."
  },
  "evidence": [
    {
      "document_id": "robbins-11",
      "page_start": 123,
      "page_end": 125,
      "chunk_id": "..."
    }
  ]
}
```

This is essential for debugging AI-generated content.

---

# 29. Question Quality Lifecycle

```text
AI_GENERATED
      |
      v
AI_REVIEW
      |
      +---- FAIL ----> NEEDS_REVIEW
      |
      v
REVIEWER
      |
      v
APPROVED
      |
      v
PRODUCTION
```

Possible statuses:

```text
DRAFT
AI_REVIEW
NEEDS_REVIEW
REVIEWED
APPROVED
PUBLISHED
RETIRED
```

---

# 30. User Feedback Loop

Users should be able to report:

```text
Incorrect answer
Incorrect explanation
Ambiguous question
Poor wording
Outdated information
Typographical error
Wrong topic
Wrong difficulty
Other
```

Pipeline:

```text
Student
   |
   v
Report Question
   |
   v
Question Feedback
   |
   v
Admin / AI Review
   |
   +---- Correct
   |
   +---- Modify
   |
   +---- Retire
   |
   +---- Reclassify
```

---

# 31. Self-Evaluation Loop

The platform should eventually evaluate questions automatically.

For every question:

```text
Question
  |
  +-- Answer correctness
  +-- Evidence support
  +-- Distractor quality
  +-- Difficulty
  +-- Cognitive level
  +-- Ambiguity
  +-- Duplicate similarity
```

This creates a quality score.

Example:

```text
quality_score = 0.91
```

The score should be treated as a review signal, not as proof of correctness.

---

# 32. Difficulty Model

Initial difficulty can be manually or AI assigned:

```text
EASY
MEDIUM
HARD
UNKNOWN
```

Later, empirical difficulty can be calculated from user performance:

```text
Question
   |
   +-- attempts
   +-- correct rate
   +-- average time
   +-- discrimination
   |
   v
Observed Difficulty
```

Do not overwrite the original assigned difficulty.

Store:

```text
declared_difficulty
observed_difficulty
```

---

# 33. Cognitive Level

Use a configurable taxonomy.

Initial:

```text
RECALL
UNDERSTANDING
APPLICATION
ANALYSIS
```

This allows questions to move beyond pure factual recall.

Example:

```text
"What is the marker for X?"
→ RECALL

"Which diagnosis best explains this presentation?"
→ APPLICATION

"Which combination of findings best differentiates X from Y?"
→ ANALYSIS
```

---

# 34. RAG Evaluation Dataset

The system should maintain a separate evaluation corpus.

Potential sources:

```text
MedMCQA
Robbins Review
Manually verified questions
Educator questions
Previous examinations
```

These should not automatically become production questions.

They can be used to evaluate:

```text
retrieval accuracy
answer accuracy
question quality
difficulty classification
explanation quality
```

---

# 35. MedMCQA Integration

MedMCQA remains a separate question source.

Current project data:

```text
Pathology questions
≈ 15,526
```

Use it for:

* initial question bank
* exam engine
* baseline evaluation
* topic discovery
* question similarity
* question-generation examples

Do not treat MedMCQA explanations as verified textbook citations unless provenance is independently established.

---

# 36. Robbins Review Integration

Robbins Review can be treated as a high-value question-style/evaluation source.

Potential metadata:

```text
source = ROBBINS_REVIEW
edition = 5
chapter = ...
question_number = ...
source_page = ...
```

The extracted content should remain private to the authorized development environment unless appropriate rights permit redistribution.

The production system should store only content that the project is authorized to use.

---

# 37. Knowledge Base Versioning

Every source should be versioned.

Example:

```text
Robbins
├── Edition 10
└── Edition 11

WHO Haematolymphoid
├── Version X
└── Version Y
```

Knowledge chunks should retain:

```text
document_version
ingestion_version
embedding_model
embedding_version
```

This allows reproducibility.

---

# 38. Re-ingestion

Documents may be updated.

Pipeline:

```text
New Edition
    |
    v
Hash / Version Detection
    |
    v
Re-ingestion
    |
    v
New Chunks
    |
    v
New Embeddings
    |
    v
Old Version Retained
```

Never silently replace an old reference version.

---

# 39. Data Storage

Recommended separation:

```text
data/
├── raw/
│   ├── medmcqa/
│   └── reference_documents/
│
├── intermediate/
│   ├── extracted_text/
│   ├── pages/
│   └── parsed_documents/
│
├── processed/
│   ├── knowledge/
│   └── questions/
│
└── evaluation/
```

Copyrighted/reference files should not be committed to Git unless the project has appropriate redistribution rights.

---

# 40. Recommended Database Components

PostgreSQL:

```text
knowledge_documents
knowledge_sections
knowledge_chunks
knowledge_embeddings
knowledge_citations
knowledge_topics
knowledge_learning_objectives
```

Existing:

```text
questions
curriculum_topics
courses
course_curriculum_mapping
```

Future:

```text
question_evidence
question_versions
question_feedback
generation_runs
retrieval_runs
evaluation_runs
```

---

# 41. Question-Evidence Relationship

A question may reference multiple pieces of evidence.

Therefore use:

```text
Question
   |
   +---- QuestionEvidence
             |
             +---- KnowledgeChunk
```

Not:

```text
Question
  |
  +---- source_page
```

because one question may require multiple sources.

---

# 42. Generation Run

Every AI generation batch should be traceable.

```text
GenerationRun
├── id
├── model
├── model_version
├── prompt_version
├── blueprint_id
├── retrieval_config
├── number_requested
├── number_generated
├── number_approved
├── created_at
└── metadata
```

This allows comparison between models and prompts.

---

# 43. Experimental Model Strategy

Models should be replaceable.

```text
Application
    |
    +-- LLM Provider
    |
    +-- Generation Model
    |
    +-- Validation Model
    |
    +-- Embedding Model
    |
    +-- Reranker
```

Do not couple the application to a specific model.

This allows experiments with:

* Gemini
* MedGemma
* general open medical LLMs
* PubMed-trained models
* future local models

without redesigning the backend.

---

# 44. RAG vs Fine-Tuning

Initial strategy:

```text
Phase 1
RAG
```

Then:

```text
Phase 2
RAG + Few-shot Examples
```

Then:

```text
Phase 3
RAG + Evaluation
```

Only after sufficient validated data:

```text
Phase 4
Fine-tuning / LoRA experiments
```

Fine-tuning should improve:

* question style
* formatting
* reasoning style
* difficulty calibration
* domain-specific generation behaviour

The knowledge itself should remain retrievable from the knowledge base.

---

# 45. Recommended Initial RAG Pipeline

For the MVP:

```text
PDF
 ↓
PyMuPDF
 ↓
Chapter/Section detection
 ↓
Semantic chunking
 ↓
Pydantic structured metadata
 ↓
Embeddings
 ↓
PostgreSQL + pgvector
 ↓
Hybrid retrieval
 ↓
LLM
 ↓
Structured MCQ
 ↓
Validation
 ↓
AI_REVIEW
```

Do not introduce a large distributed architecture yet.

---

# 46. Initial MVP Scope

The first implementation only needs:

### Documents

* PDF ingestion
* text extraction
* chapter detection
* page provenance
* chunking

### Knowledge

* PostgreSQL
* pgvector
* embeddings
* metadata
* curriculum mapping

### RAG

* semantic retrieval
* metadata filtering
* top-K evidence
* context construction

### Generation

* MCQ generation
* answer
* explanation
* difficulty
* cognitive level
* evidence references

### Validation

* JSON validation
* answer validation
* evidence validation
* duplicate detection

### Workflow

```text
AI_REVIEW
   ↓
Admin Review
   ↓
APPROVED
```

---

# 47. Future Architecture

Once the core system is stable:

```text
                     MEDICAL AI PLATFORM
                              |
       +----------------------+----------------------+
       |                      |                      |
   Knowledge Base        Question Engine       User Learning
       |                      |                      |
       |                 Assessment Engine      Analytics
       |                      |                      |
       |                 AI Generation        Personalization
       |                      |                      |
       +----------------------+----------------------+
                              |
                       Future AI Systems
                              |
                       Medical Imaging
                              |
                             PLIP
```

The same knowledge/evidence architecture can eventually support image interpretation workflows by connecting image findings to pathology entities, diagnostic criteria, immunohistochemistry, molecular findings and reference literature.

---

# 48. Initial Development Milestones

## KB-1 — Document Ingestion

* PDF validation
* text extraction
* OCR fallback
* page preservation
* document metadata

## KB-2 — Structured Parsing

* chapter detection
* section detection
* semantic chunking
* tables
* figures
* provenance

## KB-3 — Knowledge Database

* document tables
* chunk tables
* embeddings
* pgvector
* metadata filters

## KB-4 — Curriculum Mapping

* topic mapping
* subtopic mapping
* learning objectives
* mapping confidence
* human verification

## KB-5 — RAG

* query construction
* hybrid retrieval
* reranking
* context assembly
* evidence citations

## KB-6 — Question Generation

* blueprint
* MCQ generation
* explanation generation
* difficulty
* cognitive level

## KB-7 — Validation

* evidence validation
* answer validation
* duplicate detection
* quality scoring
* AI review

## KB-8 — Human Review

* reviewer workflow
* approve/reject/edit
* feedback
* versioning

## KB-9 — Learning Loop

* user reports
* user performance
* observed difficulty
* weak-topic detection
* question improvement

## KB-10 — Model Optimization

* evaluation dataset
* prompt optimization
* RAG evaluation
* model comparison
* LoRA/fine-tuning experiments

---

# 49. Definition of Done

The knowledge-base MVP is considered functional when:

* A reference PDF can be ingested.
* The system preserves document and page provenance.
* Chapters and sections can be identified.
* Text can be converted into semantic chunks.
* Chunks can be embedded.
* Chunks can be retrieved by medical query.
* Curriculum metadata can be attached.
* Retrieved evidence can be passed to an LLM.
* The LLM can generate a structured MCQ.
* Every generated question contains evidence references.
* The generated answer can be validated against retrieved evidence.
* Duplicate questions can be detected.
* AI-generated questions enter `AI_REVIEW`.
* Approved questions can enter the production question bank.
* The entire generation process is reproducible through model/prompt/retrieval version metadata.

---

# 50. Core Design Principles

1. **Knowledge and questions are separate.**
2. **Evidence must be traceable.**
3. **Source provenance must never be invented.**
4. **Original source terminology must be preserved.**
5. **Canonical curriculum mapping is separate from source metadata.**
6. **AI output is never automatically authoritative.**
7. **Human review remains available.**
8. **Models must be replaceable.**
9. **Documents must be versioned.**
10. **Question generation must be reproducible.**
11. **Difficulty should eventually be evidence-based from user performance.**
12. **RAG should precede fine-tuning.**
13. **The database should support multiple specialties from the beginning.**
14. **The MVP should remain simple enough for a single developer.**
15. **Reference material should only be used and redistributed in ways permitted by the applicable license/rights.**

---

# 51. Long-Term Vision

The final system is not simply a chatbot trained on medical books.

It is an **evidence-backed medical learning intelligence platform**:

```text
                    Medical References
                           |
                           v
                    Knowledge Graph
                           |
                    +------+------+
                    |             |
                    v             v
                  RAG          Curriculum
                    |             |
                    +------+------+
                           |
                    Medical LLM
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
     Questions        Explanations      Learning
          |                |                |
          v                v                v
     Assessments      Evidence         Personalization
          |                                 |
          +----------------+----------------+
                           |
                    User Performance
                           |
                           v
                     Feedback Loop
                           |
                           v
                 Improved Question Bank
```

The initial implementation may be focused on **Pathology and DM Oncopathology**, but the architecture should allow the same system to eventually support:

```text
MBBS
MD/MS
NEET-PG
INI-CET
DM/MCh
NEET-SS
Specialty-specific learning
```

without creating a separate AI architecture for every specialty.
