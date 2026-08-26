# Milestone 10 — Production Deployment, Release Automation & Native Publishing

> [!IMPORTANT]
> **Status: IN PROGRESS — production foundation started.**
>
> M10 deploys the stabilized product. It does not redesign the medical ontology, automatically approve imported questions, add payments, or perform the M12 code-quality review.

---

## 1. Objective

Create a repeatable path from a reviewed Git commit to a recoverable web, API, database, and native mobile release.

M10 is complete when:

1. The Next.js web application is deployed with a custom domain and HTTPS.
2. FastAPI runs as an independent production service with health checks and production secrets.
3. PostgreSQL/pgvector and Redis use managed, backed-up services.
4. Database schema changes run through versioned migrations during releases.
5. CI validates every pull request and CD promotes reviewed builds by environment.
6. Expo/EAS produces signed Android and iOS builds with documented store submission steps.
7. Logs, errors, uptime, backups, restoration, rollback, and incident ownership are documented and tested.

The production boundary is:

```text
Users
  -> app.docedge.example (Netlify / Next.js)
  -> api.docedge.example (FastAPI service)
       -> managed PostgreSQL 16 + pgvector
       -> managed Redis
       -> S3-compatible object storage

Mobile application
  -> api.docedge.example
  -> Apple App Store / Google Play releases through Expo EAS
```

---

## 2. Scope

### Included

- Development, staging, and production environments.
- Netlify web deployment and domain/DNS configuration.
- Containerized FastAPI deployment.
- Managed PostgreSQL with pgvector, connection pooling, backups, and restore drills.
- Managed Redis with authentication and TLS.
- S3-compatible storage configuration for future legitimate documents and pathology images.
- Alembic migration workflow and release-safe database upgrades.
- GitHub Actions CI and environment-controlled deployment workflows.
- Expo EAS build, signing, internal distribution, store submission, and update policy.
- Secret inventory and rotation runbook.
- Error monitoring, structured logs, uptime checks, and basic operational alerts.
- Rollback, disaster recovery, and release checklists.

### Excluded

- Payments, pricing, subscriptions, invoices, and payment webhooks: **M50**.
- Canonical topic consolidation and AI-assisted question approval/rejection/retirement: **M12**.
- Automatic publication of imported or AI-generated medical questions.
- Architecture documentation portal and developer handbook: **M11**.
- General code review/shared component consolidation: **M12**.
- Landing-page CMS: **M13**.
- Kubernetes and multi-region active-active infrastructure.

---

## 3. Environment Model

| Environment | Purpose | Data policy | Deployment |
|---|---|---|---|
| Local | Developer work | Local Docker data | Manual |
| CI | Tests/build validation | Ephemeral test database | Per workflow |
| Staging | Release verification | Synthetic or sanitized data only | Automatic from main/release branch |
| Production | Real users | Production data | Manual approval after staging |

Rules:

- Never connect preview deployments to the production database.
- Never copy real user credentials or refresh tokens into staging.
- Use distinct OAuth clients, JWT secrets, databases, Redis instances, storage buckets, and monitoring projects per environment.
- A production deploy must be reproducible from a Git commit SHA.
- Production database changes must never depend on `create_all()` or runtime `ALTER TABLE` synchronization.

---

## 4. Recommended Initial Hosting Topology

This is a modular-monolith deployment, not a microservice migration.

| Component | Initial target | Reason |
|---|---|---|
| Next.js web | Netlify | Requested web hosting, preview deploys, managed TLS/domain |
| FastAPI API | Container platform such as Render, Railway, Fly.io, or equivalent | Long-running Python process and health checks |
| PostgreSQL + pgvector | Managed PostgreSQL provider with pgvector and point-in-time recovery | Durable database operations and backups |
| Redis | Managed Redis with TLS | Rate limits, caching, and future jobs |
| Files | S3-compatible managed object storage | Durable uploads without local filesystem reliance |
| Mobile builds | Expo EAS | Reproducible signing/build/submission for Expo app |
| Source/CI | GitHub + GitHub Actions | Pull request checks and controlled releases |
| Errors/uptime | Sentry-compatible error tracking plus an external uptime monitor | Web/API visibility and alerts |

Provider selection remains replaceable. Application configuration must use standard URLs and credentials instead of provider-specific business logic.

### Why Netlify cannot host the whole current system

Netlify can host the Next.js application, but the current FastAPI process, PostgreSQL, Redis, background jobs, and persistent files need independent services. The production web application must use an absolute backend URL or a controlled Netlify proxy; local `127.0.0.1:8000` values are invalid after deployment.

---

## 5. Domain and Network Plan

Suggested DNS layout:

```text
www.example.com      -> landing/web redirect
app.example.com      -> Netlify Next.js application
api.example.com      -> FastAPI service
status.example.com   -> optional public status page
```

Required controls:

- HTTPS only, with HTTP redirected to HTTPS.
- FastAPI CORS allowlist contains only the real web origins.
- Database and Redis are not publicly exposed unless the provider requires controlled TLS endpoints.
- API documentation is disabled or access-controlled in production if it exposes operational detail.
- Health endpoints do not disclose secrets, stack traces, database URLs, or user data.
- Configure security headers, request-size limits, and upstream timeouts.

---

## 6. Production Configuration and Secrets

### Required web variables

```text
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_GOOGLE_CLIENT_ID=...
NEXT_PUBLIC_CONTACT_EMAIL=...
NEXT_PUBLIC_APP_ENV=production
```

### Required API variables

```text
APP_ENV=production
DATABASE_URL=postgresql://...sslmode=require
REDIS_URL=rediss://...
JWT_SECRET_KEY=<random secret from secret manager>
GOOGLE_CLIENT_IDS=<production web, iOS, and Android client IDs>
CORS_ALLOWED_ORIGINS=https://app.example.com
S3_ENDPOINT=...
S3_BUCKET=...
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
SENTRY_DSN=...
```

Rules:

- Secrets are stored in hosting/GitHub environment secret stores, never committed.
- `NEXT_PUBLIC_*` variables are public and must never contain secrets.
- Rotate production secrets independently of staging.
- Document owner, purpose, creation date, rotation procedure, and affected services for every secret.
- JWT rotation requires a planned overlap/key-version strategy before active sessions exist at scale.

---

## 7. Database Production Plan

### 7.1 Managed PostgreSQL requirements

- PostgreSQL 16 compatibility.
- `vector` extension support.
- TLS connections.
- Automated daily backups.
- Point-in-time recovery where affordable.
- Connection limits appropriate for web/API concurrency.
- Metrics for storage, connections, locks, CPU, and slow queries.
- Separate staging and production instances/databases.

### 7.2 Versioned migrations

M10 must finish the migration foundation planned in M9:

```text
model change
  -> generate/review Alembic revision
  -> test upgrade on empty database
  -> test upgrade on production-like snapshot
  -> deploy backward-compatible application
  -> run migration once
  -> verify schema and health
  -> remove compatibility code in a later release
```

Required commands:

```bash
alembic upgrade head
alembic current
alembic history
```

Do not run migrations independently from every API replica. Use one release job with a database advisory lock or a platform pre-deploy command.

### 7.3 Migration safety

- Prefer additive changes before destructive changes.
- Add nullable columns, backfill, then enforce constraints in a later migration.
- Avoid long table locks on `questions`, attempts, and user-history tables.
- Take/verify a backup before risky migrations.
- Every migration requires a downgrade decision; irreversible migrations must explain restoration strategy.
- Preserve all raw MedMCQA provenance and imported question states.

### 7.4 Backup and restore acceptance test

At least once before launch:

1. Create a production-style backup.
2. Restore it into an isolated database.
3. Run migration verification.
4. Compare row counts for users, questions, attempts, responses, entitlements, and audit logs.
5. Record restore duration and responsible operator.

---

## 8. API Container and Release Process

Create a production backend image that:

- Uses a pinned Python version and locked dependencies.
- Runs as a non-root user.
- Contains application code but no `.env`, raw datasets, local database, or credentials.
- Uses a production ASGI command without `--reload`.
- Exposes a lightweight liveness endpoint and dependency-aware readiness endpoint.
- Handles termination signals and drains requests cleanly.
- Writes structured logs to stdout/stderr.

Release order:

```text
CI checks
  -> build immutable image tagged with commit SHA
  -> deploy staging
  -> migrate staging
  -> smoke test
  -> production approval
  -> backup verification
  -> production migration job
  -> API deploy
  -> web deploy
  -> smoke test and monitor
```

---

## 9. Netlify Web Deployment

### Build configuration

- Base directory: repository root.
- Install command: `bun install --frozen-lockfile`.
- Build shared packages before the web build.
- Web build: `bun --filter web build` or the verified workspace equivalent.
- Publish/framework handling: Netlify Next.js runtime.
- Set the production API and Google client IDs in Netlify environment variables.

### Deployment stages

1. Deploy to the Netlify-generated domain.
2. Validate API calls, OAuth callback/origins, refresh/navigation, and deep links.
3. Attach the custom domain.
4. Configure DNS and wait for TLS issuance.
5. Add the final domain to Google OAuth origins and backend CORS.
6. Disable or isolate deploy previews that would otherwise use production services.

### Web smoke tests

- Landing page loads without mixed content.
- Email and Google authentication work.
- New user onboarding persists and reaches `/student`.
- Free users see catalog/contact gating.
- Manually subscribed users can create and complete an approved-question assessment.
- Admin access and manual entitlement changes work.
- Refreshing deep routes does not return 404.

---

## 10. CI/CD Design

### Pull request CI

Run independently where possible:

- Python formatting/linting and tests.
- TypeScript typecheck and lint.
- Shared package builds.
- Next.js production build.
- Expo diagnostics/typecheck.
- Migration upgrade on a fresh PostgreSQL database with pgvector.
- Dependency and secret scanning.
- Container build validation.

### Deployment workflows

- Staging: automatic after required checks on the chosen integration branch.
- Production: protected GitHub environment with manual approval.
- Database migration: single controlled job, never a matrix or per-instance step.
- Native builds: manual workflow dispatch or signed release tag.
- Store submission: separate approval from binary creation.

### Release identity

Every deployed surface records:

- Git commit SHA.
- semantic application version.
- build timestamp.
- environment.
- database migration revision.

---

## 11. Expo Native Publishing

### 11.1 Project setup

- Create/verify Expo project ownership under the organization account.
- Add stable iOS bundle identifier and Android application ID.
- Configure `app.config.ts` by environment.
- Keep production API URL outside source defaults.
- Configure icons, splash screen, display name, version, build number/version code, privacy strings, and deep-link scheme.

### 11.2 Credentials

- Apple Developer Program membership is required for App Store distribution.
- Google Play Console account is required for Play distribution.
- Use EAS-managed signing credentials or document an organization-controlled credentials process.
- Restrict access to signing credentials and store API keys.
- Back up recovery/ownership information outside individual developer accounts.

### 11.3 Release channels

```text
development build -> internal developers
preview build     -> QA/internal testers
production build  -> App Store Connect / Play Console
```

Recommended sequence:

1. `eas build --profile preview --platform all`
2. Test authentication, API networking, secure token storage, exam timer, background/resume, and offline failure handling on physical devices.
3. `eas build --profile production --platform android`
4. Submit Android to internal testing, then closed/open testing as appropriate.
5. `eas build --profile production --platform ios`
6. Submit iOS to TestFlight, complete review metadata, then request App Review.

### 11.4 Store readiness

- Privacy policy and support URL.
- Educational/medical disclaimer.
- Data collection and account deletion disclosures.
- App screenshots and descriptions.
- Reviewer test account and instructions.
- Google/Apple sign-in compliance.
- Account deletion flow where platform policy requires it.
- No claim that the app autonomously diagnoses or treats disease.

### 11.5 Over-the-air updates

- Use EAS Update only for compatible JavaScript/assets changes.
- Native dependency/configuration changes require a new store binary.
- Tie update channels to runtime versions.
- Provide rollback capability and test updates in preview first.

---

## 12. Observability and Operations

Minimum production signals:

- API request count, latency, status codes, and unhandled exceptions.
- Web and native JavaScript crashes.
- Authentication failures without logging credentials or tokens.
- Database connection saturation and slow queries.
- Redis availability and memory.
- Migration success/failure.
- Assessment creation failures, especially eligible-pool shortages.
- Backup completion and restore-test age.

Alerts should be actionable. Define who responds, expected response time, and the first diagnostic link/runbook.

---

## 13. Rollback and Incident Runbook

### Application rollback

- Retain previous web deploy and API image.
- Roll back by immutable version, not by rebuilding an old branch.
- Confirm database compatibility before application rollback.

### Database incident

- Stop writes when continued operation risks corruption.
- Capture current revision and relevant logs.
- Prefer a forward fix for additive migration failures.
- Restore only through the documented backup process.
- Never run destructive repair commands without a verified target and backup.

### Security incident

- Revoke affected sessions.
- Rotate compromised credentials.
- preserve audit evidence.
- identify affected users/data.
- document notification and remediation decisions.

---

## 14. Implementation Phases

### M10.1 — Production readiness audit

- [x] Define hosting topology and environment boundaries.
- [x] Define database, CI/CD, mobile, backup, and observability acceptance criteria.
- [x] Inventory runtime dependencies and current production blockers.
- [ ] Remove remaining development-only production fallbacks.
- [ ] Reconcile repository ports, environment names, and build commands.

### M10.2 — Database migrations and backend image

- [x] Add Alembic configuration and baseline migration.
- [ ] Replace runtime schema mutation with migrations.
- [x] Add production backend Dockerfile and `.dockerignore` validation.
- [x] Add liveness/readiness/version endpoints.
- [ ] Verify graceful startup/shutdown.

### M10.3 — CI foundation

- [x] Add GitHub Actions pull-request workflow.
- [x] Add PostgreSQL/pgvector and Redis test services.
- [x] Add package, web, Python, migration, and container checks.
- [ ] Add protected staging/production deployment workflow templates.

### M10.4 — Staging deployment

- [x] Add a Render Blueprint for the initial API and PostgreSQL staging deployment.
- [ ] Provision staging database, Redis, API, storage, and web.
- [ ] Configure staging Google OAuth.
- [ ] Import only approved/sanitized staging content.
- [ ] Execute full smoke test.
- [ ] Perform first backup restore drill.

### M10.5 — Native preview and stores

- [ ] Configure EAS project/profiles and environment variables.
- [ ] Produce Android/iOS preview builds.
- [ ] Complete physical-device QA.
- [ ] Prepare privacy/support/store metadata.
- [ ] Submit to internal testing and TestFlight.

### M10.6 — Production launch

- [ ] Provision production services and secrets.
- [ ] Configure domain, TLS, CORS, and OAuth origins.
- [ ] Run migration and deployment checklist.
- [ ] Verify monitoring and alerts.
- [ ] Complete rollback exercise.
- [ ] Record release version and operational ownership.

---

## 15. Definition of Done

M10 is complete only when:

- A fresh staging environment can be created from documented configuration.
- CI blocks a broken Python, TypeScript, web, migration, or container change.
- Production migrations are versioned, repeatable, and run exactly once.
- A database backup has been restored and verified.
- Netlify web and production API communicate through HTTPS with correct CORS/OAuth configuration.
- Secrets are absent from Git and development defaults cannot boot production.
- A manually subscribed test user can complete an approved-question assessment end to end.
- A free user can browse but cannot bypass entitlement enforcement.
- Android and iOS preview builds pass physical-device testing.
- Store submission requirements and ownership are documented.
- Monitoring detects an intentionally generated test error and API outage.
- Rollback steps have been exercised rather than only written.

---

## 16. Immediate Next Work

The next implementation slice is **M10.2**:

1. Inventory the current runtime/startup and schema mutation paths.
2. Introduce Alembic without losing the existing local database.
3. Create the production FastAPI container and health endpoints.
4. Add a minimal CI workflow that builds and tests those foundations.

No hosting account, paid resource, DNS mutation, or app-store submission will be performed without explicit deployment credentials and approval.

---

## 17. Initial Production Readiness Audit — 2026-08-26

### Existing foundations

- FastAPI already validates production-like JWT, Google client, and explicit CORS configuration.
- A basic `/api/health` liveness endpoint exists.
- PostgreSQL 16 with pgvector and Redis are represented in local Docker Compose.
- The Expo app already has stable iOS (`ai.docedge.student`) and Android identifiers.
- Web/native share typed domain and API-client packages.
- The repository provides a cross-platform Python launcher and documented local setup.

### Release blockers found

1. No production backend `Dockerfile` or `.dockerignore` exists.
2. No Alembic configuration/revisions exist; startup still relies on `create_all()` and runtime `ALTER TABLE` compatibility code.
3. No GitHub Actions workflows exist.
4. No `netlify.toml` or verified Netlify monorepo build configuration exists.
5. No `eas.json` release profiles exist.
6. Backend dependencies use version ranges rather than a reproducible lock/constraints artifact.
7. Health checking is liveness-only and does not verify database/Redis readiness.
8. Production API documentation exposure is not environment-controlled.
9. No structured error monitoring, release identity, or external uptime configuration exists.
10. No S3-compatible storage adapter/configuration exists yet.
11. No backup restoration script/checklist has been exercised.
12. The web repository currently has a React type-version conflict that prevents a clean global typecheck.
13. The Python virtual environment does not contain `pytest`, so CI cannot yet reproduce the expected test suite from `requirements.txt`.
14. The roadmap/documentation contains historical naming (`student-native`) while the active Expo workspace is `apps/mobile`; M11 must normalize the broader architecture documentation.

### First implementation order

```text
Alembic baseline
  -> production backend image
  -> readiness/version endpoints
  -> CI database and build checks
  -> Netlify configuration
  -> EAS preview profiles
  -> staging infrastructure
```
