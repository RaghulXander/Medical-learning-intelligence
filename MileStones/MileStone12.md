# Milestone 12 — Code Review, Shared Feature Architecture, Ontology & AI Review

## 1. Purpose

Milestone 12 improves the maintainability and content-quality foundations of the
alpha before more product features are added. It combines four related efforts:

1. review the Python/FastAPI implementation;
2. review the Next.js and Expo applications;
3. move duplicated business behavior into portable shared packages; and
4. establish the canonical topic and question-review workflow required to create
   an eligible approved assessment pool.

This is an incremental refactoring milestone, not a framework rewrite.

## 2. Desired outcome

Changes to authentication, onboarding, assessment rules or question lifecycle
should have one authoritative implementation wherever the platforms permit it.
Web and native views remain different renderers, but must not independently
invent validation, routing decisions, API payloads or domain transitions.

## 3. Initial audit findings

### Python

- `database/models.py` is approximately 936 lines and mixes many bounded areas.
- `assessment_service.py` is approximately 777 lines and combines creation,
  selection, attempts, scoring, results and analytics.
- `student_service.py` and `auth_service.py` are also large and require transaction,
  authorization and error-contract review.
- Route request models are defined locally and some status transitions accept
  strings instead of a centralized transition policy.
- Strong tests exist for selection and authentication, providing a refactoring
  safety net.

### Web and React Native

- Login, registration and onboarding decisions are duplicated.
- Web and native correctly require separate UI primitives and OAuth adapters,
  but shared validation and post-auth routing rules are missing.
- The web authentication modal is large and contains form state, Google adapter,
  taxonomy loading, password tools and navigation in one component.
- The native app uses reusable visual primitives, but some screens contain large
  inline style and orchestration blocks.
- React versions differ intentionally: React 18 for Next.js 14 and React 19 for
  Expo SDK 54. UI packages must not assume one React runtime.
- `apps/student-native` is an obsolete workspace and increases install/typecheck
  ambiguity.

### Ontology and review

- The model separates canonical topics, curriculum mapping and provenance, but
  the database still contains a broad historical topic set.
- Exam eligibility correctly requires `APPROVED` questions, leaving an empty pool
  until mapping and review are completed.
- Status values exist, but allowed transitions, review evidence and AI evaluation
  records need explicit policy.
- User reports exist but are not yet converted into structured signals for the
  next review cycle.

## 4. Target client architecture

```text
packages/shared
  domain types
  validation
  state decisions
  feature configuration

packages/api-client
  request/response transport
  token injection
  normalized API errors

apps/web
  DOM components
  browser storage
  Google web identity adapter
  Next.js navigation

apps/mobile
  React Native components
  secure native storage
  Google Android/iOS adapter
  Expo Router navigation
```

Shared packages must not import React DOM, React Native, browser globals or native
SDKs. Platform shells translate shared decisions into platform navigation/UI.

## 5. Shared-feature extraction order

1. Authentication input normalization and validation.
2. Onboarding-completion and post-auth destination rules.
3. Registration payload and error types.
4. Assessment palette/attempt state transitions.
5. Question-report categories and status labels.
6. Design tokens that can be represented on both platforms.

Literal DOM/React Native components are not shared in the first pass.

## 6. Python review checklist

- Route/service/database responsibility separation.
- Explicit transaction ownership and rollback behavior.
- Authorization and resource-ownership enforcement.
- Pydantic request/response models instead of untyped dictionaries where useful.
- Stable domain exceptions mapped once to HTTP responses.
- Query count, eager-loading and pagination behavior.
- UTC timestamp and enum consistency.
- No runtime schema mutation outside Alembic.
- Provider-independent interfaces for AI and identity integration.
- Tests for failure and denial paths, not only successful operations.

Large files are split only along demonstrated domain boundaries. Line count alone
does not justify abstraction.

## 7. Frontend review checklist

- Separate view, orchestration and transport responsibilities.
- Remove `any` at API/domain boundaries.
- Avoid duplicated server state when a query abstraction is justified.
- Standardize loading, empty, forbidden and error states.
- Verify effects for stale closures, repeated calls and race conditions.
- Ensure components remain keyboard/screen-reader accessible.
- Keep secrets out of `NEXT_PUBLIC_*` and `EXPO_PUBLIC_*` configuration.
- Test shared decisions independently from platform rendering.

## 8. Canonical topic ontology

The replacement ontology begins with a curated Pathology tree rather than
automatically accepting every raw dataset topic.

```text
Pathology
  General Pathology
  Hematopathology
  Breast Pathology
  Gastrointestinal & Hepatobiliary Pathology
  Thoracic Pathology
  Gynecologic Pathology
  Genitourinary Pathology
  Head & Neck Pathology
  Bone & Soft Tissue Pathology
  Neuropathology
  Pediatric Pathology
  Dermatopathology
  Cytopathology
  Immunohistochemistry
  Molecular Pathology
  Autopsy & Forensic Pathology
```

Each canonical topic has a stable ID, display name, parent, aliases, active flag
and optional specialty metadata. Raw dataset topics remain immutable provenance
and map to canonical topics through explicit reviewed mappings.

Existing 150+ raw topics are not deleted merely because they are not canonical.
They become source labels/aliases or remain unmapped until reviewed.

## 9. Question lifecycle

Allowed production-oriented flow:

```text
IMPORTED or GENERATED
  -> AI_REVIEW
  -> HUMAN_REVIEW
  -> APPROVED
  -> RETIRED
```

Alternative transitions include rejection, report-driven return to human review,
and correction followed by re-review. `APPROVED` is the only normally eligible
exam state.

Transition policy must define:

- allowed source/target states;
- required role;
- required reason/evidence;
- actor and timestamp;
- previous/new content revision;
- whether existing assessment snapshots remain immutable.

## 10. AI-assisted review

AI provides review signals, not publishing authority.

Signals may include:

- answer/explanation consistency;
- topic mapping suggestion;
- duplicate similarity;
- distractor quality;
- ambiguity/outdated-content risk;
- source-evidence support;
- model agreement;
- recommended status and confidence.

Store provider/model/prompt version, structured output, evidence IDs, confidence,
timestamp and errors. A human reviewer accepts or rejects suggestions.

## 11. Feedback loop

Question reports are normalized into review signals:

```text
student report
  -> triage
  -> aggregate by question/category
  -> reopen review when threshold/policy is met
  -> correct or retire
  -> record resolution
  -> inform future evaluator rules
```

User feedback must never directly train or prompt a model without sanitization,
provenance and a documented data-use policy.

## 12. Phases

### Phase 12.1 — Baseline and review report

- Capture builds, typechecks and Python tests.
- Record findings by severity and ownership.
- Identify dead code/workspaces and unsafe duplication.

### Phase 12.2 — Shared authentication slice

- Centralize input normalization, validation and onboarding completion.
- Replace duplicated web/native decisions.
- Add portable unit tests.

### Phase 12.3 — Shared assessment behavior

- Extract portable attempt/palette state rules.
- Standardize answer synchronization and error states.
- Keep UI primitives platform-specific.

### Phase 12.4 — Python boundary refactoring

- Introduce domain exceptions and typed service results.
- Split assessment and model modules along proven boundaries.
- Preserve API behavior and database migrations.

### Phase 12.5 — Ontology consolidation

- Seed the curated canonical Pathology tree.
- build alias/mapping review tools;
- migrate question mappings without deleting source labels;
- produce mapping coverage reports.

### Phase 12.6 — AI and human review workflow

- Add evaluation and transition audit models.
- Implement provider-independent evaluator interface.
- Add admin queues for AI review, human review, approval, rejection and retirement.
- incorporate question-report signals.

### Phase 12.7 — Verification and cleanup

- Remove or archive `apps/student-native` after confirming no unique code.
- Run Python tests, web build/typecheck, native typecheck/Metro export.
- Update architecture/ADRs and prioritized remaining debt.

## 13. Acceptance criteria

- [ ] Shared authentication validation and onboarding decisions are used by both clients.
- [ ] Platform OAuth adapters send the same backend ID-token contract.
- [ ] No business rule is duplicated only because DOM and native views differ.
- [ ] Backend review findings have severity, evidence, owner and disposition.
- [ ] Canonical Pathology topics are stable and raw topics retain provenance.
- [ ] Question status transitions are explicit, authorized and audited.
- [ ] AI cannot publish a question directly.
- [ ] User feedback can return a question to review or retirement.
- [ ] Approved question-pool coverage is measurable by canonical topic.
- [ ] Web, mobile and Python verification suites pass.
- [ ] Historical native workspace is removed or formally retained with rationale.

## 14. Out of scope

- Pixel-identical shared DOM/native components.
- Microservice extraction based solely on file size.
- Automatic approval based only on an LLM or PubMedBERT prediction.
- Deleting raw topic/provenance data.
- Landing-page CMS (M13).
- Payment automation (M50).

## 15. First implementation slice

1. Add shared auth normalization, validation and navigation decisions.
2. Adopt them in web and mobile login/registration/navigation.
3. Add portable tests for the shared rules.
4. Run shared, web and native verification.
5. Record the next highest-severity review findings.
