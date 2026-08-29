# Milestone 14 — Versioned Surgical Pathology Knowledge Ontology

> Progress (2026-08-29): Phases 14.1–14.3 have started. The versioned schema,
> structural validation, core hierarchy, and limited Breast draft seed are present.
> The sixth-edition WHO Breast source is an online beta, so the scheme remains
> `DRAFT`; feature relationships, evidence, question crosswalk, and admin UI remain.

## 1. Purpose

Milestone 14 creates a maintainable Surgical Pathology knowledge ontology inspired
by standard organ-system practice, including the structure supplied from *Rosai and
Ackerman's Surgical Pathology*. It replaces the temporary flat grouping taxonomy
with a versioned hierarchy that can support question classification, blueprinting,
diagnostic entity search, AI review, evidence retrieval and future image-based cases.

This milestone builds an ontology and editorial workflow. It does not ingest or
reproduce copyrighted textbook chapters, tables, figures or descriptive prose.

## 2. Important scope boundary

Surgical Pathology is one major branch of Pathology, not the whole discipline.
The ontology created here covers:

- surgical pathology principles and diagnostic methods;
- organ-system and anatomic-site branches;
- non-neoplastic and neoplastic diagnostic entities;
- morphology, IHC, molecular and grading/staging relationships.

General Pathology, Hematology, Clinical Pathology, Transfusion Medicine, Autopsy,
Laboratory Management and undergraduate competencies remain parallel knowledge
domains. They may reference the same reusable concepts but must not be forced below
the Surgical Pathology root.

## 3. Design principles

1. Stable machine codes are independent of display names.
2. Raw source topics remain immutable provenance.
3. A diagnostic entity is distinct from its features and evidence.
4. IHC markers and molecular alterations are reusable concepts, not repeated text.
5. Course syllabi map onto the knowledge graph; they do not define the graph.
6. AI can suggest mappings but cannot verify or publish them.
7. Every node and relationship is versioned and auditable.
8. Textbook-derived claims require legitimate access and a precise source link.
9. No inferred citation is represented as human verified.
10. Existing question mappings are migrated through a reversible crosswalk.

## 4. Target hierarchy

```text
Pathology Knowledge Root
  Surgical Pathology
    Principles & Methods
      Specimen handling, grossing & staging
      Frozen section & intraoperative consultation
      Quality assurance
      Synoptic reporting
      Histotechnology
    Ancillary Diagnostics
      Immunohistochemistry
      Molecular pathology
      Cytogenetics and FISH
      Electron microscopy
      Digital pathology and computational pathology
    Cardiovascular
      Heart
      Blood vessels
      Cardiac and vascular tumors
    Hematolymphoid Surgical Pathology
      Lymph node
      Spleen
      Bone marrow
    Head, Neck & Upper Aerodigestive Tract
      Oral cavity and oropharynx
      Nasopharynx
      Jaw and odontogenic lesions
      Salivary glands
      Larynx, hypopharynx and trachea
      Eye, ocular adnexa and ear
    Skin
    Thoracic
      Lung and bronchial tree
      Pleura and pericardium
      Mediastinum and thymus
    Gastrointestinal
      Esophagus
      Stomach
      Small intestine
      Appendix
      Colon, rectum and anus
      Peritoneum and retroperitoneum
    Hepatobiliary & Pancreas
      Liver
      Gallbladder and extrahepatic bile ducts
      Pancreas and ampullary region
    Genitourinary
      Kidney and renal pelvis
      Ureter, bladder and urethra
    Male Reproductive
      Prostate and seminal vesicles
      Testis and epididymis
      Penis
    Female Reproductive
      Vulva and vagina
      Cervix
      Endometrium and myometrium
      Ovary and fallopian tube
      Placenta and gestational trophoblastic disease
    Breast
    Endocrine & Neuroendocrine
      Thyroid
      Parathyroid
      Adrenal and paraganglia
      Pituitary
    Bone & Joints
    Soft Tissue
    Central Nervous System
    Peripheral Nerve & Skeletal Muscle
```

The tree above establishes navigation and ownership. Diagnostic entities are
added below the appropriate anatomic or method node during reviewed vertical
slices rather than attempting to seed every known disease at once.

## 5. Node types

Every ontology node has an explicit semantic type:

- `ROOT`
- `DISCIPLINE`
- `METHOD_GROUP`
- `METHOD`
- `ANATOMIC_SYSTEM`
- `ORGAN`
- `ANATOMIC_SITE`
- `DISEASE_FAMILY`
- `DIAGNOSTIC_ENTITY`
- `MORPHOLOGIC_FEATURE`
- `CLINICAL_FEATURE`
- `GROSS_FEATURE`
- `IHC_MARKER`
- `MOLECULAR_ALTERATION`
- `GRADING_SYSTEM`
- `STAGING_SYSTEM`
- `LEARNING_OBJECTIVE`

An entity such as invasive breast carcinoma is not stored as an IHC marker or
organ. Typed nodes prevent structurally invalid mappings.

## 6. Relationship types

The graph supports relationships beyond a single parent tree:

- `IS_A`
- `PART_OF`
- `LOCATED_IN`
- `HAS_CLINICAL_FEATURE`
- `HAS_GROSS_FEATURE`
- `HAS_MICROSCOPIC_FEATURE`
- `EXPRESSES_MARKER`
- `LACKS_MARKER`
- `HAS_MOLECULAR_ALTERATION`
- `USES_GRADING_SYSTEM`
- `USES_STAGING_SYSTEM`
- `DIFFERENTIAL_OF`
- `MIMICS`
- `ASSOCIATED_WITH`
- `SUPERSEDES`

Relationships may carry context, polarity, diagnostic weight, confidence,
verification status and evidence links. For example, marker expression must not
be treated as universally present merely because an entity can express it.

## 7. Diagnostic entity profile

Each diagnostic entity exposes consistent sections without duplicating feature
definitions:

```text
Diagnostic entity
  Identity
    preferred name
    synonyms
    classification/version
  Clinical context
    typical site
    presentation
    epidemiologic context
  Gross pathology
  Microscopic pathology
    architecture
    cytology
    background/stroma
  Ancillary findings
    positive/supportive IHC
    negative/exclusionary IHC
    molecular/cytogenetic alterations
  Classification
    variants/subtypes
    grade
    stage
  Differential diagnosis
  Evidence and verification
```

The application must distinguish expected, common, variable, rare and absent
findings. It must also distinguish diagnostic, supportive, prognostic and
predictive biomarkers.

## 8. Proposed data model

### `ontology_schemes`

- `id`, `code`, `name`
- `version`, `status`
- `description`
- `released_at`, `created_at`, `created_by`

### `ontology_nodes`

- `id`, `scheme_id`, `code`
- `preferred_name`, `node_type`
- `parent_id`, `display_order`
- `status`, `metadata`
- `valid_from`, `valid_to`
- `created_at`, `updated_at`

### `ontology_aliases`

- `node_id`, `alias`
- `alias_type`, `language`
- `source`, `verification_status`

### `ontology_relationships`

- `source_node_id`, `relationship_type`, `target_node_id`
- `qualifier`, `polarity`, `frequency`
- `diagnostic_weight`, `confidence`
- `verification_status`
- `created_by`, `reviewed_by`, timestamps

### `ontology_evidence`

- `relationship_id` or `node_id`
- existing `source_id`, `document_id`, `chunk_id`
- chapter, section and page range
- verification status and confidence

### `question_ontology_mappings`

- `question_id`, `node_id`
- `mapping_role` (`PRIMARY`, `SECONDARY`, `DIFFERENTIAL`, `METHOD`)
- `mapping_method` (`RULE`, `AI_SUGGESTED`, `HUMAN`)
- `confidence`, `verification_status`
- `ontology_version`, actor and timestamps

The existing `CurriculumTopic` structure remains available during migration.
It is not destructively replaced until crosswalk coverage and application reads
have been verified.

## 9. Curriculum overlays

The same ontology nodes can be mapped independently to:

- NMC MBBS competencies;
- NMC MD Pathology outcomes;
- NBEMS DNB Pathology curriculum;
- DM/DrNB Oncopathology curriculum;
- NEET-PG and INI-CET blueprints;
- NEET-SS and institutional examination blueprints.

Each mapping stores course, competency code, depth, core/elective status,
weightage and source. A syllabus change must not rename or duplicate the medical
knowledge node.

## 10. Provenance and copyright policy

- The supplied hierarchy may be used as an editorial starting taxonomy.
- Do not copy textbook paragraphs, tables, images or entity descriptions.
- Record the exact edition and legitimately accessed chapter/page when a medical
  assertion is extracted or summarized.
- Bibliographic presence does not prove that every node was derived from that
  source.
- WHO terminology and classification versions must be version-labelled.
- AI-suggested source mappings remain `AI_SUGGESTED` until human verification.

## 11. Implementation phases

### Phase 14.1 — Source and scope review

- Register legitimate editions and official curricula in the source catalog.
- Compare the supplied outline with current NMC/NBEMS and permitted references.
- Approve node naming conventions, boundaries and ownership.
- Publish an ontology design ADR.

### Phase 14.2 — Schema and versioning

- Add Alembic migrations for schemes, typed nodes, aliases, relationships,
  evidence and question mappings.
- Add uniqueness, cycle-prevention and type-validation rules.
- Add draft, released, deprecated and retired lifecycle states.

### Phase 14.3 — Core hierarchy seed

- Seed the root, principles/methods and organ-system branches.
- Add aliases from existing raw topics without deleting provenance.
- Produce a versioned machine-readable seed artifact.

### Phase 14.4 — First vertical slice: Breast

- Create breast site, disease families and a limited reviewed entity set.
- Connect morphology, IHC, molecular, grade, stage and differential concepts.
- Attach verified evidence only where legitimate source access exists.
- Map existing breast questions and measure precision.

### Phase 14.5 — Question mapping workflow

- Deterministic alias mapping first.
- AI suggestion for unresolved questions.
- Human accept, correct or reject queue.
- Bulk operations with audit history and rollback.
- Never change a question to `APPROVED` because its topic was mapped.

### Phase 14.6 — Admin ontology workspace

- Tree and graph navigation.
- Node, alias and relationship editing.
- Duplicate and orphan detection.
- Evidence and version comparison.
- Mapping coverage and reviewer workload reports.

### Phase 14.7 — Remaining organ-system slices

- Implement one owned/reviewed system at a time.
- Prioritize by question volume and course demand.
- Release new ontology versions through migrations and crosswalks.

## 12. Validation rules

- Stable codes are unique within a scheme.
- No parent/child cycles.
- Entity nodes cannot be parents of organ-system nodes.
- Every released entity belongs to at least one valid anatomic or method branch.
- Every asserted feature relationship records its verification state.
- Deprecated nodes provide a replacement or explicit retirement reason.
- Question mappings reference an ontology version.
- Raw source labels are never overwritten.
- Production exam selection continues to require question approval independently.

## 13. Deliverables

- Ontology ADR and naming standard.
- Database migrations and SQLAlchemy models.
- Versioned Surgical Pathology core seed.
- Breast vertical-slice seed and tests.
- Legacy-to-v2 crosswalk and dry-run report.
- Admin review APIs and initial ontology workspace.
- Mapping coverage, ambiguity and orphan reports.
- Source/evidence verification workflow.

## 14. Acceptance criteria

Milestone 14 is complete when:

1. the root, method and organ-system hierarchy is stored as a released version;
2. all nodes and relationships are typed, versioned and auditable;
3. aliases and source labels are separate from preferred names;
4. the Breast vertical slice demonstrates entity-feature relationships;
5. existing question mappings can be previewed and rolled back;
6. AI suggestions require human verification;
7. no copyrighted textbook content has been copied into the repository;
8. no question becomes exam-eligible merely through ontology mapping;
9. tests cover cycles, invalid types, versioning and mapping transitions; and
10. documentation explains how contributors safely extend the ontology.

## 15. Out of scope

- Complete transcription of every entity from any textbook.
- Automatic publication of AI-created medical relationships.
- Full WHO tumor-classification ingestion without licensing/provenance review.
- Diagnostic use for patient care.
- Image-model inference or whole-slide image storage.
- Replacing the existing curriculum model before a verified migration.
