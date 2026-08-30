# Surgical Pathology ontology contributor guide

Milestone 14 introduces a versioned, typed ontology alongside the existing curriculum
tree. The current seed is `2026.08-draft.1`; it is not a production classification.

## Preview the hierarchy

The Next.js application exposes a read-only explorer at `/pathology`. It renders
the versioned seed during the web build, so reviewers can browse the hierarchy,
search codes and aliases, filter node types, and inspect parent/child paths without
requiring database access. The page intentionally preserves `DRAFT` and
`AI_SUGGESTED` labels and must not imply that the ontology has been released.

Run the web application locally and open:

```text
http://localhost:3005/pathology
```

## Current scope

The seed contains 84 nodes:

- one Pathology root and one Surgical Pathology discipline;
- principles, methods, and ancillary diagnostics;
- top-level organ systems and sites;
- a limited Breast slice with epithelial, in-situ/lobular, invasive, and
  fibroepithelial groups and selected diagnostic entities.

The public Rosai publisher table of contents was used only to check organ-system
coverage. The current public IARC Breast classification structure was used for entity
names. The IARC sixth-edition Breast volume is still an online beta, so every seeded
node remains `DRAFT`.

## Load the draft locally

Apply migrations, then seed the draft:

```bash
bun run db:migrate
bun scripts/run_python.mjs scripts/seed_surgical_pathology_ontology.py
```

The command is idempotent. It can update an existing draft but refuses to mutate a
released version whose seed hash has changed.

## Add a topic safely

Edit `data/ontology/surgical-pathology-2026.08-draft.1.json` while the version is a
draft. Every node needs:

- a stable uppercase code that does not encode an edition;
- a preferred name;
- an explicit node type;
- a valid parent code (except the single root);
- a display order and lifecycle status.

Aliases are separate records. Historical names should use an alias type such as
`LEGACY_TERM`; AI-proposed aliases must remain `AI_SUGGESTED` until reviewed.

Run the focused tests after each edit:

```bash
bun scripts/run_python.mjs -m pytest -q tests/test_surgical_pathology_ontology.py
```

## Evidence boundary

Names and hierarchy are not diagnostic evidence. Do not add morphology, IHC,
molecular, grading, staging, or differential relationships from memory. Each such
relationship needs a legitimate source record, precise location when available, and
a verification status. Bibliographic metadata alone never makes an assertion
`HUMAN_VERIFIED`.

Do not copy textbook prose, tables, figures, or images into the seed. Do not use
unauthorized textbook PDFs. Public web tables of contents may guide editorial scope,
but they do not authorize ingestion of the underlying work.

## Release workflow

Before changing a scheme from `DRAFT` to `RELEASED`:

1. review all node names and parent assignments;
2. resolve AI-suggested aliases;
3. compare against the then-current official classification;
4. run cycle, type, version, and database tests;
5. generate a legacy-topic crosswalk preview;
6. record the editor and release date.

After release, corrections require a new version plus explicit `SUPERSEDES`
relationships or a crosswalk. Never rewrite a released seed in place.
