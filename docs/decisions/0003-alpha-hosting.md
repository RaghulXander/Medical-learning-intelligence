# ADR 0003 — Use managed free-tier services for the alpha

- Status: Accepted
- Date: 2026-08-27
- Owners: Release maintainers
- Supersedes: Netlify frontend deployment attempt

## Context

The alpha has one or two users and should not incur recurring infrastructure cost.
Netlify's Next.js runtime repeatedly failed to package the Bun monorepo at runtime.
Render's free PostgreSQL expires after 30 days.

## Decision

Use Vercel for Next.js, Render for the FastAPI container, Neon for PostgreSQL and
Expo EAS for native builds. Accept Render cold starts during alpha.

## Consequences

The platform remains free within provider limits and avoids operating servers.
There are multiple provider configurations and no production SLA. Promotion from
alpha requires a cost, backup, observability and availability review.

## Alternatives considered

- Netlify: rejected for the current Bun/Next monorepo runtime packaging failure.
- Render PostgreSQL: rejected as durable storage because the free database expires.
- Self-hosting: rejected due to operational cost and maintenance.

## Validation

Revisit before public launch, payment support, sensitive clinical data, or when
free-tier cold starts and quotas affect users.
