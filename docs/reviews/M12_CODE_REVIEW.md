# Milestone 12 Code Review Baseline

Status: In progress
Scope: Python backend, Next.js web, Expo/React Native, shared packages, topic ontology, and question review workflow.

## Implemented first

Authentication rules that do not depend on a browser or native runtime now live in
`@medical/shared/features/auth`. Web and native use the same validation, email
normalization, onboarding-completion rule, and post-auth destination decision.

The shared rules have unit tests and are checked by both application type-checks.

## Prioritized findings

### P0 — Native sessions are not persisted securely — Resolved

`apps/mobile/lib/storage/secure-store.ts` uses an in-memory fallback on native.
Tokens previously disappeared when the app process restarted. Native storage now uses
`expo-secure-store` with device-only, when-unlocked keychain accessibility. Web retains
`localStorage`; native storage failures fail closed rather than writing tokens to an
insecure fallback.

### P1 — Registration has conflicting speciality ownership — Resolved for MVP

Clients can collect `primary_speciality`, but the backend registration service assigns
Pathology itself. Choose one canonical contract. For the current Pathology-only MVP,
the API should explicitly document the fixed value instead of silently ignoring client
input. The API now accepts and documents Pathology/Oncopathology input, rejects unrelated
specialities, and stores the canonical MVP value `Pathology`. Later expansion should
validate submitted specialities against the curriculum.

### P1 — Question status changes have no transition policy — Resolved

`PATCH /questions/{question_id}/status` accepts any valid enum value from any current
state. Add an explicit transition matrix, record actor/time/reason, and prevent an AI
result from publishing directly to `APPROVED`. A transition matrix now blocks invalid
jumps, AI review cannot publish directly, rejection/retirement require notes, and every
successful change creates a `QuestionReview` audit row.

### P1 — Topic identity is still split — In progress

`CurriculumTopic` and `Question.primary_topic_id` provide the correct canonical path,
but historical free-text topics remain. New exam selection and reporting should use
canonical topic IDs; raw source topic text should remain immutable provenance. Migration
must produce mapped, unmapped, and ambiguous reports before old topics are hidden. The
Pathology v1 ontology and deterministic mapper are now active: 5,231 of 15,526 local
records have been grouped while their original topic values remain unchanged. Records
with missing, exam-label, miscellaneous, or ambiguous topics remain unmapped.

### P2 — Backend modules have multiple responsibilities

The largest hotspots are `database/models.py`, `assessment_service.py`,
`student_service.py`, and `auth_service.py`. Refactor by domain boundary in small,
tested changes. Do not split the deployment into additional services.

### P2 — A historical native workspace remains

`apps/student-native` overlaps with the active `apps/mobile` application and remains in
workspace metadata. Confirm it has no required code, then archive or remove it in a
separate change so dependency resolution and developer onboarding have one native app.

### P2 — Authentication orchestration remains duplicated

Validation and routing are now shared, but each app still owns token persistence,
refresh, Google credential acquisition, and error presentation. Extract portable auth
session operations next while retaining platform-specific Google UI and storage adapters.

## Review sequence

1. Stabilize secure native session persistence.
2. Add the question-status transition policy and audit history.
3. Introduce the curated Pathology ontology and migration dry run.
4. Split backend hotspots behind characterization tests.
5. Create shared UI primitives inside each platform, then share only portable feature
   logic across platforms.
6. Remove the obsolete native workspace after verification.

## Verification baseline

- Shared auth tests: passing
- `@medical/shared` build: passing
- `@medical/api-client` build: passing
- Web TypeScript check: passing
- Mobile TypeScript check: passing
