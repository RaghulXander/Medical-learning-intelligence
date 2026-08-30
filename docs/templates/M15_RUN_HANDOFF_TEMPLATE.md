# M15 Reference-Document Run Handoff

Copy this file into the generated `data/processed/reference_documents/` directory and replace every placeholder. Do not include credentials, access tokens, service-account key contents, or private rights documents.

## Run identity

- Run ID: `<RUN_ID>`
- Status: `<PILOT | FAILED | PASSED>`
- Started at UTC: `<TIMESTAMP>`
- Completed at UTC: `<TIMESTAMP>`
- Git commit: `<GIT_SHA>`
- Operator/reviewer: `<NAME_OR_INTERNAL_ID>`
- GCS artifact prefix: `gs://<PROCESSED_BUCKET>/reference-document-runs/<RUN_ID>/`

## Parser configuration

- GCP location: `<LOCATION>`
- Processor ID: `<PROCESSOR_ID>`
- Processor version ID: `<PINNED_VERSION_ID>`
- Processing mode: `LIVE_DOCAI`
- Normalization version: `<VERSION_FROM_MANIFEST>`
- Mock fallback: `false`

## Documents

| Short name | Document ID | Edition | File SHA-256 | Total PDF pages | Expected chunks | Completed chunks | Audit status |
|---|---|---|---|---:|---:|---:|---|
| `robbins_review` | `<ID>` | `<EDITION>` | `<SHA256>` | `<PAGES>` | `<COUNT>` | `<COUNT>` | `<STATUS>` |
| `robbins_pathologic_basis_11th` | `<ID>` | `<EDITION>` | `<SHA256>` | `<PAGES>` | `<COUNT>` | `<COUNT>` | `<STATUS>` |

## Artifact inventory

- Registry present: `<YES/NO>`
- Raw Document AI JSON count: `<COUNT>`
- Normalized JSON count: `<COUNT>`
- Evidence JSON count: `<COUNT>`
- Quality report count: `<COUNT>`
- Provenance manifests present: `<YES/NO>`
- Slice PDFs excluded from transfer: `<YES/NO>`

## Quality and provenance

- Rights status verified: `<YES/NO>`
- File integrity verified on extraction machine: `<YES/NO>`
- Missing physical pages: `<COUNT/LIST>`
- Duplicate physical pages: `<COUNT/LIST>`
- Failed chunks: `<COUNT/LIST>`
- Mixed parser modes: `<YES/NO>`
- Mixed processor versions: `<YES/NO>`
- Printed-page calibration reviewed: `<YES/NO>`
- Human gold-sample result: `<SUMMARY>`
- Ready for database import: `NO — importer/migration not implemented`

## Known limitations or follow-up

- `<ITEM>`

## Review sign-off

- Medical/content reviewer: `<NAME>`
- Engineering reviewer: `<NAME>`
- Decision: `<PASS | FAIL | REPROCESS>`
- Decision timestamp UTC: `<TIMESTAMP>`
