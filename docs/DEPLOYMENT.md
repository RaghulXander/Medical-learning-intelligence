# DocEdge Deployment Guide

The production-alpha topology is:

- Next.js web on Vercel
- FastAPI container on Render
- PostgreSQL on Neon
- Native preview/production artifacts through Expo EAS

## 1. Render API

Render deploys `Dockerfile.backend` using `render.yaml`. Configure:

```text
APP_ENV=production
DATABASE_URL=<Neon PostgreSQL URL with sslmode=require>
JWT_SECRET_KEY=<generated high-entropy value>
GOOGLE_CLIENT_IDS=<web,Android,and iOS client IDs separated by commas>
CORS_ALLOWED_ORIGINS=https://<production-project>.vercel.app
```

The container entrypoint applies `alembic upgrade head` before Uvicorn starts.
Verify after every release:

```text
https://<render-service>.onrender.com/api/health
https://<render-service>.onrender.com/api/ready
https://<render-service>.onrender.com/api/version
```

Render free web services sleep after inactivity. A cold start during alpha is
expected and does not indicate database loss.

## 2. Neon PostgreSQL

Neon replaces the expiring Render free database; it does not replace the Render
API. Copy the Neon connection string into Render's `DATABASE_URL` and retain
`sslmode=require`.

Before switching a database containing required data:

1. export the existing database;
2. restore into Neon;
3. run Alembic against Neon;
4. point Render to Neon;
5. verify users, questions, roles and assessments;
6. retain the old database until verification is complete.

For disposable alpha data, migrations plus the controlled seed/import scripts
are sufficient.

## 3. Vercel web

Import the monorepo and set the Vercel project root directory to `apps/web`.
`apps/web/vercel.json` installs from the workspace root and builds shared packages
before Next.js.

Configure:

```text
API_URL=https://<render-service>.onrender.com
NEXT_PUBLIC_API_URL=https://<render-service>.onrender.com
NEXT_PUBLIC_GOOGLE_CLIENT_ID=<Google web OAuth client ID>
NEXT_PUBLIC_CONTACT_EMAIL=raghuljayan@gmail.com
NEXT_PUBLIC_SITE_URL=https://<production-project>.vercel.app
NEXT_PUBLIC_APP_ENV=production
```

`NEXT_PUBLIC_*` values are compiled into browser code. They are not secrets.
Never place database credentials, JWT secrets or OAuth client secrets in them.

### Landing-page CMS publishing

The CMS editor is available to administrators at `/admin/content`. Published
content is committed to `apps/web/content/landing-page.json`, so the existing
Vercel Git integration rebuilds the site after a successful publication.

Configure these server-only values on the Render API service:

```text
CMS_GITHUB_OWNER=RaghulXander
CMS_GITHUB_REPOSITORY=Medical-learning-intelligence
CMS_GITHUB_BRANCH=main
CMS_GITHUB_CONTENT_PATH=apps/web/content/landing-page.json
CMS_GITHUB_TOKEN=<fine-grained token or GitHub App token>
```

Restrict the credential to this repository and repository-content write access.
Do not create `NEXT_PUBLIC_CMS_GITHUB_TOKEN`. The editor uses the existing user
JWT; the Render backend performs GitHub operations after RBAC and schema checks.

If GitHub variables are absent, administrators can load and preview the bundled
local content but publishing returns `503` without modifying files. A stale file
SHA returns `409`, requiring the editor to reload instead of overwriting another
administrator's publication.

### Question and native-layout publication

The question editor is available at `/admin/questions/<question-id>`. Its saves
go to PostgreSQL and create immutable question revisions; they do not commit
medical content to the landing CMS repository.

The native home-layout editor is available at `/admin/mobile-layout`. Published
layouts are stored as versioned database records and delivered from:

```text
GET /api/mobile-ui/screens/home?platform=ANDROID&app_version=1.0.0
```

Run the current migration before using either editor:

```bash
python -m alembic upgrade head
```

The native client includes a bundled fallback, so database, network or invalid
remote-content failure does not leave the dashboard blank.

## 4. Google OAuth

Create separate OAuth clients as required:

- Web: authorize the stable Vercel production origin.
- Android: package `ai.docedge.student` plus the EAS signing SHA-1.
- iOS: bundle identifier `ai.docedge.student`.

Add every ID-token audience accepted from clients to Render's
`GOOGLE_CLIENT_IDS`. Do not add OAuth client secrets to web or mobile bundles.

## 5. Expo/EAS native builds

`apps/mobile/eas.json` defines development, preview and production profiles.
Configure preview values before building:

```text
EXPO_PUBLIC_API_URL=https://<render-service>.onrender.com
EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID=<Android OAuth client ID>
EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID=<iOS OAuth client ID when used>
EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID=<web OAuth client ID for Expo web>
```

Build a shareable Android alpha APK:

```bash
cd apps/mobile
eas build --platform android --profile preview --clear-cache
```

Uninstall stale alpha APKs when validating a native configuration change.

### EAS Update channels

The application now includes `expo-updates`. Create one new preview and
production native build after this integration; older installed builds do not
contain this update runtime.

Compatible JavaScript or asset changes can then be published with:

```bash
cd apps/mobile
bun run update:preview -- --message "Describe the tested change"
bun run update:production -- --message "Describe the approved change"
```

The GitHub Actions workflow **Publish Mobile Update** performs package builds,
mobile type checking and publication. Add an Expo access token as the repository
or protected-environment secret `EXPO_TOKEN`. Publish to preview first, validate
the installed preview build, and use production only for an approved change.

Changing native dependencies, Expo SDK, permissions, bundle identifiers or
other native configuration requires a new EAS build and compatible runtime; do
not publish such a change only through EAS Update.

This Bun workspace intentionally uses isolated dependency linking because the
Next.js application uses React 18 while Expo SDK 54 uses React 19. Expo Doctor
may report same-version Expo packages in Bun's peer-context store as duplicates;
Expo tracks this as a Bun-monorepo false positive. CI therefore runs
`expo install --check`, native TypeScript validation and the EAS build itself
instead of suppressing actual package-version incompatibilities.

## 6. Production-alpha smoke test

1. Open the stable Vercel URL in a private window.
2. Register and complete onboarding.
3. Verify free-user entitlement messaging.
4. Verify Google web sign-in.
5. Install the latest EAS preview build and verify password and Google sign-in.
6. Grant subscription access through the admin flow and verify it persists.
7. Confirm `/api/ready` reports database readiness.
8. Confirm imported questions are not silently promoted to `APPROVED`.

## 7. Before public launch

- Replace sleeping/free compute if cold starts are unacceptable.
- Establish automated backups and perform a recorded restore test.
- Add error monitoring and uptime checks.
- Separate migration execution from application startup when the platform supports
  a reliable pre-deploy job.
- Configure managed Redis only when queued/background behavior is enabled.
- Review provider terms, quotas, privacy controls and incident ownership.
