# ADR 0004 — Introduce a versioned Surgical Pathology ontology

- Status: Accepted
- Date: 2026-08-29
- Owners: Pathology editors and backend maintainers

## Context

The existing `CurriculumTopic` tree is useful for course navigation, but it cannot
represent typed diagnostic entities, reusable markers or molecular alterations,
multi-parent relationships, classification versions, or reviewed question mappings.
Surgical Pathology also must remain one branch of Pathology rather than becoming a
replacement for General Pathology, Hematology, Clinical Pathology, or other domains.

The publisher identifies *Rosai and Ackerman's Surgical Pathology*, 11th edition
(2017), as its latest edition. IARC has begun the sixth WHO Classification of Tumours
edition and currently lists Breast Tumours as an online beta. A beta classification
can inform a draft ontology but must not silently become a released platform standard.

## Decision

Add a parallel, versioned ontology model consisting of schemes, typed nodes, aliases,
relationships, evidence, and auditable question mappings. Keep `CurriculumTopic`
operational during migration and connect courses to ontology nodes in a later reviewed
increment.

The initial `2026.08-draft.1` artifact includes:

- the Surgical Pathology methods and organ-system hierarchy;
- a limited Breast vertical slice based on publicly visible classification names;
- no textbook prose, figures, tables, copied diagnostic criteria, or inferred claims;
- explicit draft status while the WHO Breast sixth edition remains beta.

Released scheme versions are immutable. Corrections create a new version and a
crosswalk. Topic mapping never changes a question's editorial approval status.

## Consequences

The application can evolve beyond a flat topic list while preserving existing exam
selection. Editors must now manage ontology and curriculum versions separately.
Feature, IHC, molecular, grade, stage, and differential relationships require a
verification state and legitimate evidence before release.

## Sources checked

- [Elsevier: Rosai and Ackerman's Surgical Pathology, 11th edition](https://shop.elsevier.com/books/rosai-and-ackermans-surgical-pathology-2-volume-set/goldblum/978-0-323-26339-9)
- [IARC: sixth-edition future titles and beta status](https://whobluebooks.iarc.who.int/future-titles/)
- [IARC: current public Breast Tumours classification structure](https://whobluebooks.iarc.who.int/structures/breast-tumours/)
- [Elsevier: Robbins, Cotran & Kumar Pathologic Basis of Disease, 11th edition](https://shop.elsevier.com/books/robbins-cotran-and-kumar-pathologic-basis-of-disease/kumar/978-0-443-26452-8)

## Validation

Revisit the Breast nodes before the first ontology release, when the WHO beta changes,
or when a legitimately accessed source is used to add diagnostic relationships.
