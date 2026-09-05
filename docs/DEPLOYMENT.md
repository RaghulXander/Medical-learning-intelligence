# DocEdge Deployment Guide

The production-alpha topology is:

- Next.js web on Vercel
- FastAPI container on Render
- PostgreSQL on Neon
- Native preview/production artifacts through Expo EAS
- MkDocs engineering documentation in a separate Vercel project

## 1. Render API

Render deploys `Dockerfile.backend` using `render.yaml`. Configure:

```text
APP_ENV=production
DATABASE_URL=<Neon PostgreSQL URL with sslmode=require>
JWT_SECRET_KEY=<generated high-entropy value>
GOOGLE_CLIENT_IDS=<web,Android,and iOS client IDs separated by commas>
CORS_ALLOWED_ORIGINS=https://<production-project>.vercel.app
R2_PUBLIC_URL=https://<exact-R2-development-or-custom-domain-prefix>
```

`R2_PUBLIC_URL` is required by the authenticated image-review proxy. It is an
exact SSRF allowlist prefix, not an R2 access-key secret. Derive the value from
the stored catalog without exposing object paths by running this in the Neon SQL
editor:

```sql
SELECT split_part(storage_uri, '/pathology/', 1) AS r2_public_url,
       count(*) AS image_count
FROM image_assets
WHERE storage_uri IS NOT NULL
GROUP BY 1;
```

Copy the single returned prefix into Render → `docedge-api` → Environment as
`R2_PUBLIC_URL`, save, and redeploy. Do not use the full URL of one image and do
not add a trailing slash. The proxy deliberately fails closed when the setting
is absent or does not exactly match the stored object prefix.

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
- Android: package `ai.docedge.student` plus the EAS signing SHA-1. The Android
  client identifies the signed app and is not passed as a JavaScript variable.
- iOS: bundle identifier `ai.docedge.student`.

The native client requests its backend ID token for the **Web OAuth client ID**.
Set that ID as `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` in EAS and include the same ID
in Render's comma-separated `GOOGLE_CLIENT_IDS`. Do not add OAuth client secrets
to web or mobile bundles.

The installed Android application uses native Google Sign-In. It requires a new
EAS build and cannot run inside Expo Go. Password authentication remains usable
in Expo Go. A Google `DEVELOPER_ERROR` normally means that the Android OAuth
client does not match both the package and the certificate SHA-1.
The integration starts a new `1.0.1` update runtime so older `1.0.0` binaries
cannot receive JavaScript that imports a native module they do not contain.

Android configuration checklist:

1. Run `eas credentials -p android`, select the preview profile and copy the
   signing certificate's **SHA-1** fingerprint.
2. In the same Google Cloud project as the Web OAuth client, create an Android
   OAuth client for package `ai.docedge.student` and that SHA-1.
3. Put the **Web** OAuth client ID—not the Android ID—in EAS as
   `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` for preview and production.
4. Put the same Web client ID in Render's `GOOGLE_CLIENT_IDS`. Keep any Web
   client ID used by the Next.js application in that comma-separated list too.
5. If the OAuth consent screen is still in Testing mode, add the account used on
   the phone under Test users.

## 5. Expo/EAS native builds

`apps/mobile/eas.json` defines development, preview and production profiles.
Configure preview values before building:

```text
EXPO_PUBLIC_API_URL=https://<render-service>.onrender.com
EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID=<iOS OAuth client ID when used>
EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID=<Web OAuth client ID used by the backend>
```

Create these as EAS project environment variables for both `preview` and
`production`; do not rely on the repository's root `.env`. The mobile app reads
them at bundle time and EAS cloud workers do not inherit local shell values.
`EXPO_PUBLIC_*` values are embedded in the client and therefore must never hold
private keys or OAuth client secrets.

The profiles explicitly select their matching EAS environments. Confirm them
before building:

```bash
cd apps/mobile
eas env:list --environment preview
eas env:list --environment production
```

Build a shareable Android alpha APK:

```bash
cd apps/mobile
eas build --platform android --profile preview --clear-cache
```

The current pilot distribution target is a signed APK attached to a GitHub
prerelease. The manually triggered **Android Beta Release** workflow uses the
`github-beta` EAS profile, calculates a SHA-256 checksum, and publishes both
artifacts. Configure `EXPO_TOKEN` in GitHub's protected `preview` environment,
then follow the [Android beta distribution runbook](ANDROID_BETA_DISTRIBUTION.md).

Build the signed Android App Bundle for Google Play only after the preview gate
passes and store publication is re-prioritized:

```bash
cd apps/mobile
eas build --platform android --profile production
```

For the first Play upload, listing copy, graphics, privacy/deletion work,
reviewer access, testing tracks, and promotion gates, follow the
[Android beta and Google Play listing runbook](PLAY_STORE_LISTING.md).

Uninstall stale alpha APKs when validating a native configuration change.
Android will reject an APK when an installed copy of `ai.docedge.student` was
signed by a different key, or when its version code is newer. Preview builds now
auto-increment their version code, but a differently signed existing copy still
has to be uninstalled first.

If installation succeeds but the app closes, capture the actual native failure
instead of relying on Metro's development logs:

```bash
adb logcat -c
adb logcat | grep -E "AndroidRuntime|ReactNativeJS|ai.docedge.student"
```

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

## 6. Vercel documentation and ontology preview

Use two Vercel projects connected to the same GitHub repository so the Next.js
application and MkDocs portal keep independent build settings:

| Vercel project | Root directory | Configuration | Purpose |
| --- | --- | --- | --- |
| DocEdge web | `apps/web` | `apps/web/vercel.json` | Public application and `/pathology` ontology explorer |
| DocEdge engineering docs | repository root | `vercel.json` | MkDocs portal built into `site/` |

For the documentation project, import the existing GitHub repository again in
Vercel, leave the root directory at the repository root, and select **Other** as
the framework if Vercel does not detect the root configuration automatically.
`vercel.json` installs `requirements-docs.txt`, runs the strict MkDocs build, and
publishes `site/` as the output directory.

Both projects should track `main` as their production branch. Vercel's Git
integration then creates a production deployment after each pushed commit and a
preview deployment for non-production branches. Source documentation belongs in
`docs/`; generated `site/` remains uncommitted.

The ontology explorer is available at `/pathology` on the existing web project.
It is built directly from the versioned seed and does not require the API or a
seeded production database to display the current editorial hierarchy.

Preview documentation locally with:

```bash
python -m mkdocs serve
```

Then open `http://127.0.0.1:8000`. The local preview is useful while writing,
but the Vercel documentation project is the shared, durable copy.

## 7. Production-alpha smoke test

1. Open the stable Vercel URL in a private window.
2. Register and complete onboarding.
3. Verify free-user entitlement messaging.
4. Verify Google web sign-in.
5. Install the latest EAS preview build and verify password and Google sign-in.
6. Grant subscription access through the admin flow and verify it persists.
7. Confirm `/api/ready` reports database readiness.
8. Confirm imported questions are not silently promoted to `APPROVED`.

## 8. Before public launch

- Replace sleeping/free compute if cold starts are unacceptable.
- Establish automated backups and perform a recorded restore test.
- Add error monitoring and uptime checks.
- Separate migration execution from application startup when the platform supports
  a reliable pre-deploy job.
- Configure managed Redis only when queued/background behavior is enabled.
- Review provider terms, quotas, privacy controls and incident ownership.
