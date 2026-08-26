# DocEdge deployment guide

This guide describes the initial M10 staging deployment:

- Web: `https://medprepai.netlify.app`
- API and PostgreSQL: Render, Singapore region
- Contact: `raghuljayan@gmail.com`

## 1. Push the deployment configuration

Render and Netlify deploy from Git, so commit and push the M10 files before creating the Blueprint.

Important root files:

- `render.yaml`
- `Dockerfile.backend`
- `netlify.toml`
- `alembic.ini`
- `migrations/`

## 2. Create the Render Blueprint

1. Sign in to Render and connect the GitHub repository.
2. Choose **New → Blueprint**.
3. Select the repository and branch containing `render.yaml`.
4. Keep the Blueprint path as `render.yaml`.
5. Review the two proposed resources:
   - `docedge-api`
   - `docedge-postgres`
6. Render will request `GOOGLE_CLIENT_IDS`. Enter the same production Google web client ID used by Netlify. Multiple IDs are comma-separated.
7. Apply the Blueprint.

The initial Blueprint uses free resources for staging. Free Render PostgreSQL expires after 30 days and has no backups; do not treat it as the final production database.

## 3. Verify Render

After deployment, copy the API URL, for example:

```text
https://docedge-api.onrender.com
```

Open:

```text
https://docedge-api.onrender.com/api/health
https://docedge-api.onrender.com/api/ready
https://docedge-api.onrender.com/api/version
```

All three must return HTTP 200. Production intentionally does not expose `/docs`.

The startup command applies `alembic upgrade head`, and migration `20260826_0002` enables the PostgreSQL `vector` extension.

## 4. Configure Netlify

In **Site configuration → Environment variables**, set:

```text
API_URL=https://docedge-api.onrender.com
NEXT_PUBLIC_API_URL=https://docedge-api.onrender.com
NEXT_PUBLIC_GOOGLE_CLIENT_ID=<production Google web client ID>
NEXT_PUBLIC_CONTACT_EMAIL=raghuljayan@gmail.com
```

Use the real Render URL, without a trailing slash. Then choose **Deploys → Trigger deploy → Clear cache and deploy site**.

## 5. Configure Google OAuth

In the Google Cloud OAuth web client, add this authorized JavaScript origin:

```text
https://medprepai.netlify.app
```

If a custom web domain is added later, add it separately to Google and to Render's `CORS_ALLOWED_ORIGINS`.

## 6. Staging smoke test

1. Open the Netlify site in a private browser window.
2. Register with email/password.
3. Complete onboarding and refresh the dashboard.
4. Verify the free-user contact banner uses `raghuljayan@gmail.com`.
5. Sign in as an administrator and manually grant exam access.
6. Verify the entitlement persists after sign-out/sign-in.
7. Confirm imported questions remain `IMPORTED`; do not bulk approve them for deployment testing.

Assessment execution remains unavailable until the M12 ontology/review workflow produces a reviewed `APPROVED` pool.

## 7. Before production users

- Upgrade Render PostgreSQL from Free to a paid plan with backups.
- Upgrade the API if cold starts are unacceptable.
- Move `alembic upgrade head` from `dockerCommand` to Render's paid pre-deploy command.
- Provision managed Redis and set `REDIS_URL`.
- Perform and record a database restoration test.
- Configure error monitoring and an uptime check for `/api/ready`.
