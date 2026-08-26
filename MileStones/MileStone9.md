# Milestone 9 — Security Hardening, Access Control & Course Entitlements

> [!IMPORTANT]
> **Status: PLANNED — must be completed before production deployment.**
>
> Milestone 9 stabilizes the trust boundaries of the existing FastAPI, Next.js, and Expo application. It does not add AI generation, payments, a CMS, or deployment automation.

---

## 1. Objective

Make the current Pathology platform safe and predictable for real users by completing five foundations:

1. Production-safe authentication and session handling.
2. Server-enforced roles, permissions, and resource ownership.
3. Course and exam-preparation bundle entitlements.
4. Versioned PostgreSQL migrations.
5. Persistent reporting and audit trails.

The key rule is:

```text
Authentication answers: Who is this user?
Authorization answers: What may this user do?
Entitlements answer: Which educational content may this user access?
Ownership answers: Which user-owned records may this user read or change?
```

These concepts must not be combined into a single `role`, `course_id`, or frontend visibility check.

---

## 2. Scope Boundary

### Included in M9

- Google and email/password authentication hardening.
- Secure web and native session strategy.
- Permission dependencies for FastAPI routes.
- Assessment-attempt ownership enforcement.
- Course, bundle, and user-entitlement models.
- Configurable default Pathology assignment after signup.
- Admin grant, revoke, extend, and inspect flows.
- Alembic migrations and database upgrade documentation.
- Persistent question reports and administrative audit logs.
- Security-focused service, API, and integration tests.
- Correction of architecture documentation where it affects security decisions.

### Explicitly excluded

- Hosting, domains, managed PostgreSQL selection, app-store publication, and release CI: **M10**.
- Full architecture/developer documentation portal: **M11**.
- Python/React/React Native code review and shared-component consolidation: **M12**.
- Landing-page widget CMS: **M13**.
- Payments and subscriptions. M9 models must support future paid access, but no payment provider is added.
- PubMedBERT, RAG, question generation, or pathology image models.

---

## 3. Current Risks M9 Must Resolve

The following are release blockers in the current implementation:

1. Question edit/status routes do not consistently require an authenticated reviewer/admin.
2. Assessment routes accept caller-controlled `user_id` or `attempt_id` without complete ownership checks.
3. Google authentication contains development shortcuts, including direct-email authentication and unsigned token decoding.
4. The web client stores access and refresh tokens in `localStorage`.
5. A development JWT secret is used if production configuration is missing.
6. Super-admin identity is hard-coded and automatically enforced during database initialization.
7. CORS permits all origins.
8. Login throttling is process-local and therefore inconsistent across multiple API instances.
9. Schema changes use `create_all()` and best-effort `ALTER TABLE` calls rather than versioned migrations.
10. The question-report endpoint returns success without persisting a report.
11. The repository currently has courses but no durable user enrollment/bundle entitlement system.

M9 is complete only when these risks are fixed and tested, not merely hidden in the UI.

---

## 4. Target Authorization Model

### 4.1 Platform roles

Keep the existing roles, but do not rely on a numeric role hierarchy for every decision:

| Role | Intended responsibility |
|---|---|
| `SUPER_ADMIN` | Platform bootstrap, admin governance, sensitive configuration |
| `ADMIN` | User administration, entitlement assignment, operational oversight |
| `REVIEWER` | Medical/editorial review and question approval |
| `EDUCATOR` | Draft and edit educational content without final approval |
| `USER` | Student learning and assessment access |

### 4.2 Permission matrix

Create named permissions in backend policy code. A database permission system is not required for this milestone.

| Permission | SUPER_ADMIN | ADMIN | REVIEWER | EDUCATOR | USER |
|---|---:|---:|---:|---:|---:|
| `users.read` | ✓ | ✓ | — | — | — |
| `users.manage_roles` | ✓ | Limited | — | — | — |
| `entitlements.read` | ✓ | ✓ | Own | Own | Own |
| `entitlements.manage` | ✓ | ✓ | — | — | — |
| `questions.read_editorial` | ✓ | ✓ | ✓ | ✓ | — |
| `questions.edit` | ✓ | ✓ | ✓ | ✓ | — |
| `questions.review` | ✓ | ✓ | ✓ | — | — |
| `questions.approve` | ✓ | ✓ | ✓ | — | — |
| `questions.retire` | ✓ | ✓ | ✓ | — | — |
| `reports.submit` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `reports.resolve` | ✓ | ✓ | ✓ | — | — |
| `attempts.read_any` | ✓ | Limited support use | — | — | — |

Implement reusable FastAPI dependencies such as:

```python
current_user = Depends(require_authenticated_user)
reviewer = Depends(require_permission("questions.review"))
admin = Depends(require_permission("entitlements.manage"))
```

Frontend guards may improve navigation, but backend permission checks are authoritative.

### 4.3 Ownership rules

- A student can start an attempt only for their authenticated user ID.
- Student requests must not accept a `user_id` body/query parameter.
- A student can heartbeat, submit, view results, or review only their own attempt.
- Guest attempts require a valid, unexpired guest-session secret and cannot access registered-user history.
- Mastery and history endpoints operate on `/me`, not arbitrary user IDs.
- Admin support access must use a separate permission-protected endpoint and must be audited.
- Correct answers and explanations are returned only after submission or when the assessment mode explicitly permits tutor feedback.

---

## 5. Authentication & Session Hardening

### 5.1 Google OAuth

Production Google sign-in must:

- Accept only a Google ID token from the configured client ID(s).
- Verify signature, issuer, audience, expiry, subject, and `email_verified`.
- Reject direct-email authentication.
- Remove unsigned JWT decoding.
- Remove the GET quick-auth behavior.
- Keep any simulated identity provider inside tests only.
- Link accounts by verified email only under a documented conflict policy.
- Record success, failure, and account-link events without storing tokens.

### 5.2 Email/password

- Validate email using a shared server-side schema.
- Use Argon2id as the preferred password hash; allow verified legacy hashes during migration.
- Use generic login failures to avoid account enumeration.
- Add password-reset tokens that are random, hashed in the database, single-use, and time-limited.
- Do not mark normal email/password registrations as verified until verification is completed.
- Revoke appropriate sessions after password reset/change.

Email delivery may use a development adapter in M9. Production provider wiring belongs to M10.

### 5.3 Web sessions

- Store the refresh token in a `Secure`, `HttpOnly`, `SameSite=Lax` cookie.
- Keep the short-lived access token in memory where practical.
- Never store the refresh token in `localStorage` or readable cookies.
- Rotate refresh tokens and detect reuse.
- Add CSRF protection to cookie-authorized state-changing routes.
- Clear cookies on logout and revoke the server-side session.

### 5.4 Native sessions

- Store native refresh tokens only in Expo SecureStore/OS keychain storage.
- Keep access tokens short-lived.
- Reuse the same backend refresh rotation and revocation model.
- Ensure the web fallback of the Expo app follows the web-session rules.

### 5.5 Configuration safety

- Production startup must fail when `JWT_SECRET_KEY` or required OAuth configuration is absent.
- Provide development defaults only when `APP_ENV=development` or `test` is explicit.
- Move bootstrap super-admin emails to deployment configuration.
- Replace automatic super-admin mutation in `init_db()` with an explicit idempotent bootstrap command.
- Redact credentials, access tokens, refresh tokens, reset tokens, and authorization headers from logs.

### 5.6 Rate limiting

- Use Redis-backed rate limiting for login, signup, refresh, password reset, guest-session creation, and question reports.
- Include IP plus normalized identity where appropriate.
- Return `429` with a safe retry indication.
- Do not depend on an in-memory dictionary in production.

---

## 6. Course, Bundle & Entitlement Architecture

### 6.1 Domain separation

```text
Course
  Defines an educational curriculum, e.g. PATHOLOGY_NEET_SS

ExamPrepBundle
  A grantable product/configuration, e.g. PATHOLOGY_FOUNDATION_2026

BundleCourse
  Maps a bundle to one or more courses

UserEntitlement
  Records a user's effective access, its source, status, and validity

EntitlementAuditLog
  Records who granted, revoked, or extended access
```

Do not add one `course_id` or bundle JSON array to `users`.

### 6.2 Proposed tables

#### `exam_prep_bundles`

- `id`
- `code` — unique and stable
- `name`
- `description`
- `is_active`
- `is_default_for_new_users`
- `metadata` — non-authoritative display configuration only
- `created_at`, `updated_at`

#### `bundle_courses`

- `bundle_id`
- `course_id`
- `access_level` — initially `FULL`; reserved for future extension
- unique constraint on `(bundle_id, course_id)`

#### `user_entitlements`

- `id`
- `user_id`
- `bundle_id` nullable
- `course_id` nullable
- `status`: `PENDING | ACTIVE | SUSPENDED | EXPIRED | REVOKED`
- `source`: `SIGNUP_DEFAULT | ADMIN_GRANT | MIGRATION | PROMOTION | PURCHASE`
- `starts_at`
- `expires_at` nullable
- `assigned_by_user_id` nullable for system assignment
- `revoked_by_user_id` nullable
- `revoked_at` nullable
- `reason` nullable
- `created_at`, `updated_at`

Exactly one access target must be present: bundle or direct course. Enforce this with a database check constraint.

#### `entitlement_audit_logs`

- `id`
- `entitlement_id`
- `actor_user_id` nullable for system actions
- `action`: `GRANTED | ACTIVATED | EXTENDED | SUSPENDED | REVOKED | EXPIRED`
- `before_state`, `after_state`
- `reason`
- `created_at`

### 6.3 Default signup assignment

New users currently receive Pathology access. Make this configuration-driven:

```text
Verified signup
  -> resolve active default signup bundle
  -> create entitlement idempotently
  -> audit source = SIGNUP_DEFAULT
  -> return effective entitlements in session/profile response
```

Rules:

- There must be at most one active default signup bundle per deployment/tenant scope.
- Assignment must be idempotent; retrying signup or OAuth callbacks cannot create duplicates.
- Existing users receive the initial Pathology entitlement through a one-time migration/backfill.
- Role assignment does not automatically grant course access.
- Deactivating a bundle prevents new grants but does not silently delete historical entitlements.
- Revoking access does not delete attempts, results, or learning history.

### 6.4 Entitlement enforcement

Before creating an assessment, the backend must verify that the user has effective access to the requested course/content scope.

Effective access means:

```text
status = ACTIVE
AND starts_at <= now
AND (expires_at IS NULL OR expires_at > now)
AND referenced bundle/course is active
```

Question-selection and assessment services receive an authorized content scope. They must not trust course codes supplied by the frontend.

### 6.5 Admin API/UI

Admin capabilities:

- View a user's current and historical entitlements.
- Grant an active bundle or direct course.
- Set start/expiry dates.
- Extend, suspend, or revoke access with a reason.
- See the actor and audit history.
- Filter users by bundle/course/access status.
- Configure which bundle is assigned to new users.

Every write requires `entitlements.manage` and creates an audit record in the same database transaction.

---

## 7. Database Migration Strategy

Adopt Alembic as the only supported production schema-change mechanism.

### Required work

1. Add Alembic configuration and connect it to SQLAlchemy metadata.
2. Create a baseline migration representing the currently deployed schema.
3. Add M9 tables, constraints, and indexes in a new migration.
4. Backfill existing users with the default Pathology entitlement.
5. Add verification queries for orphaned or duplicate data.
6. Test upgrade from a representative pre-M9 database.
7. Test downgrade for development where safe; document irreversible data migrations.
8. Replace runtime `ALTER TABLE` synchronization.
9. Keep `create_all()` only for isolated unit tests, not deployed environments.

### Deployment-safe rules

- Migrations are committed with the code that requires them.
- Never edit a migration already applied to a shared environment.
- Backups are taken before destructive or large data migrations.
- Application startup does not automatically perform risky migrations.
- M10 will define who runs `alembic upgrade head` in each deployment environment.

---

## 8. Question Reporting & Editorial Audit

The existing report endpoint must persist a real `QuestionReport`.

Required behavior:

- Authenticated users can report a question they encountered.
- Store `reporter_id`, `question_id`, optional `attempt_id`, category, notes, and timestamps.
- Validate category using the complete product taxonomy.
- Store enough question-version/snapshot information to understand later edits.
- Prevent accidental rapid duplicate submissions while allowing genuinely separate reports.
- Reviewer/admin can change `OPEN -> UNDER_REVIEW -> RESOLVED | DISMISSED`.
- Resolution stores actor, action, notes, and timestamp.
- Reporting a question does not automatically change its medical ground truth.
- Retirement/approval/status changes are separate, explicit audited actions.

Add the missing report categories:

- Incorrect answer
- Incorrect explanation
- Ambiguous question
- Multiple possible answers
- Poor wording
- Wrong topic
- Wrong difficulty
- Outdated information
- Source/reference problem
- Other

---

## 9. API Contract Changes

### Authentication

- Replace browser token-body responses with cookie-oriented web endpoints or a documented BFF/session adapter.
- Keep a secure bearer-token flow for native clients.
- Remove GET authentication and development identity shortcuts.
- Add `/api/auth/sessions` and session revocation endpoints.

### Student assessment APIs

Prefer authenticated self-scoped routes:

```text
POST /api/assessments/{assessment_id}/attempts
GET  /api/me/attempts/{attempt_id}
PATCH /api/me/attempts/{attempt_id}/heartbeat
POST /api/me/attempts/{attempt_id}/submit
GET  /api/me/attempts/{attempt_id}/results
GET  /api/me/attempts/{attempt_id}/review
GET  /api/me/mastery
GET  /api/me/history
```

### Entitlements

```text
GET    /api/me/entitlements
GET    /api/admin/users/{user_id}/entitlements
POST   /api/admin/users/{user_id}/entitlements
PATCH  /api/admin/entitlements/{entitlement_id}
GET    /api/admin/entitlements/{entitlement_id}/audit
GET    /api/admin/bundles
POST   /api/admin/bundles
PATCH  /api/admin/bundles/{bundle_id}
```

Use Pydantic response models rather than untyped dictionaries for changed/new APIs. Update `packages/shared` and `packages/api-client` contracts in the same change.

---

## 10. CORS, Headers & API Safety

- Configure allowed origins through environment variables.
- Do not combine wildcard origins with credentialed browser requests.
- Restrict methods and headers to those used by the clients.
- Add secure response headers at the Next.js edge/server layer.
- Define maximum request sizes.
- Validate pagination and search limits.
- Avoid returning internal exceptions, database details, or token-verification errors to clients.
- Ensure OpenAPI docs are disabled or protected in production if operational policy requires it.

---

## 11. Test Plan

### Unit tests

- Permission matrix for every role.
- Entitlement effective-access calculation, start/expiry boundaries, suspension, and revocation.
- Default bundle resolution and idempotent assignment.
- Password/reset-token and refresh-token behavior.
- Google claims validation through a mocked verified-token adapter.

### API integration tests

- Anonymous caller cannot edit/approve/retire questions.
- Educator cannot approve a question.
- Reviewer can approve but cannot manage user roles or entitlements.
- Admin permissions cannot promote beyond policy.
- User A cannot read, heartbeat, submit, or review User B's attempt.
- Student cannot access content outside active entitlements.
- Expired/revoked access is denied without deleting history.
- Signup assigns exactly one default entitlement under retries.
- Report creation and resolution are persisted and audited.
- Refresh-token rotation and reuse detection revoke affected sessions.
- Production configuration rejects missing secrets and invalid CORS configuration.

### Migration tests

- Fresh database upgrades from zero to head.
- Existing pre-M9 schema upgrades to head.
- Existing users receive one correct Pathology entitlement.
- Migration can run twice only through Alembic's normal no-op head behavior.
- Constraints reject duplicate and invalid entitlement records.

### Client tests

- Web session survives access-token renewal without exposing refresh token to JavaScript.
- Logout clears the browser session and revokes it server-side.
- Native tokens remain in secure storage.
- Admin entitlement UI handles loading, error, empty, expired, and revoked states.
- Unauthorized navigation does not leak protected API data.

---

## 12. Implementation Stages

### M9A — Security release blockers

- Remove unsafe Google authentication fallbacks.
- Require production secrets and explicit environment mode.
- Secure CORS.
- Add reusable permission and ownership dependencies.
- Protect question and assessment endpoints.
- Add regression tests for IDOR and role bypasses.

### M9B — Session hardening

- Implement secure browser refresh cookie flow and CSRF controls.
- Retain native SecureStore bearer flow.
- Add Redis-backed throttling.
- Complete session listing, rotation, reuse detection, and revocation tests.

### M9C — Migrations

- Establish Alembic baseline.
- Remove runtime schema synchronization from production.
- Document local upgrade and rollback workflow.

### M9D — Bundles and entitlements

- Add bundle, mapping, entitlement, and audit models/migrations.
- Seed the default Pathology bundle.
- Backfill existing users.
- Assign default access idempotently during signup.
- Enforce access in assessment creation/selection.
- Add admin APIs and UI.

### M9E — Reporting and final verification

- Persist question reports and resolutions.
- Audit all sensitive operations.
- Run backend tests, TypeScript checks, web build, and mobile checks.
- Perform manual two-user ownership testing.
- Update relevant data-model and API documentation.

Stages should be delivered in this order because later entitlement features depend on secure identity, authorization, and migrations.

---

## 13. Definition of Done

M9 is complete only when all of the following are true:

- [ ] No production Google login path accepts an email or unsigned token as identity proof.
- [ ] Production refuses to start with development secrets or missing required configuration.
- [ ] Web refresh tokens are inaccessible to browser JavaScript.
- [ ] Native refresh tokens use secure OS storage.
- [ ] Redis-backed rate limiting protects authentication and abuse-sensitive endpoints.
- [ ] Every mutating question endpoint has a tested permission requirement.
- [ ] Every attempt/history/mastery endpoint enforces self-ownership or audited admin access.
- [ ] Correct answers cannot be retrieved before allowed by assessment policy.
- [ ] Course/bundle access is represented through entitlements, not user roles.
- [ ] New users receive the configured Pathology bundle exactly once.
- [ ] Admins can grant, extend, suspend, and revoke access with a complete audit trail.
- [ ] Existing users are safely backfilled.
- [ ] PostgreSQL schema changes run through Alembic migrations.
- [ ] Question reports are persisted and resolvable.
- [ ] CORS uses an explicit environment-specific allowlist.
- [ ] API contracts and shared TypeScript types are updated together.
- [ ] Backend tests, type checks, web production build, and mobile checks pass in a clean environment.
- [ ] No raw medical dataset, secret, or user token is added to Git or logs.

---

## 14. Required Deliverables

```text
backend/
  core/authorization.py
  core/config.py
  services/entitlement_service.py
  api/routes/entitlements.py

database/
  migrations/                 # Alembic environment and revisions
  models.py                   # Bundle/entitlement/audit additions

packages/shared/
  entitlement and session contracts

packages/api-client/
  self-scoped attempt, session, and entitlement clients

apps/web/
  secure session integration
  admin entitlement management UI

apps/mobile/
  verified secure token lifecycle

tests/
  authorization, ownership, entitlement, auth, report, and migration tests

docs/
  updated security decisions, data model, and local migration commands
```

Exact filenames may follow the repository's conventions, but responsibilities must remain separated.

---

## 15. Follow-on Milestones

### M10 — Production Deployment & Release Engineering

Will cover Netlify web deployment and domain configuration, hosted FastAPI deployment, managed PostgreSQL/Redis/object storage, backups, secrets, observability, Alembic release migrations, staging/production environments, Expo EAS builds, Apple App Store/Google Play publishing, and CI/CD release workflows.

### M11 — Architecture & Developer Documentation

Will document the actual system using Architecture Decision Records, C4 diagrams, OpenAPI-generated API reference, database diagrams, contributor/runbook documentation, and a searchable documentation site so multiple developers can work safely.

### M12 — Codebase Review & Shared UI Architecture

Will review Python, React, and React Native code; remove duplication; define module boundaries; consolidate shared design tokens, form schemas, API contracts, and reusable auth/onboarding components while respecting web/native platform differences.

### M13 — Landing Page Widget CMS

Will add an admin-controlled, schema-driven page composition system for showing, hiding, ordering, scheduling, and configuring approved landing-page sections without permitting arbitrary production code execution.

