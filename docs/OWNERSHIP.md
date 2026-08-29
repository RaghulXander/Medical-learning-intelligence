# Ownership and Change Impact

Ownership means responsibility for reviewing impact, not exclusive permission to
edit a directory.

| Area | Source of truth | Consumers/deployment | Required checks |
|---|---|---|---|
| Domain schemas | `packages/shared` | Web, mobile, API client | package build/typecheck; web and mobile typecheck |
| HTTP client | `packages/api-client` | Web and mobile | package build; Android Metro export; web build |
| Web UI | `apps/web` | Vercel | typecheck and Next production build |
| Native UI | `apps/mobile` | Expo/EAS | typecheck, Metro Android export, relevant EAS preview build |
| Authentication | `backend/services/auth_service.py`, auth routes, both client adapters | Render, Vercel, EAS, Google | auth tests; audience/CORS review; web/mobile smoke tests |
| Authorization | `backend/core/authorization.py`, route dependencies | All protected API consumers | role/ownership denial tests |
| Questions | question routes/services and `database/models.py` | Admin and assessment flows | backend tests and migration review |
| Assessments | assessment routes/service | Web/mobile student clients | selection, submit, results and entitlement tests |
| Database schema | `database/models.py`, `alembic/versions` | Neon/local PostgreSQL | Alembic upgrade and schema tests; backup plan |
| Ingestion | `scripts`, `backend/ingestion` | PostgreSQL question bank | pipeline tests; immutable raw-data check |
| Production API | `Dockerfile.backend`, `render.yaml` | Render | container build, readiness and migration checks |
| Documentation | `docs`, `mkdocs.yml`, milestone specs | All developers | `mkdocs build --strict` |

## Cross-platform change checklist

When changing login, onboarding, assessment or session behavior:

1. Update the shared schema/API client when the contract changes.
2. Update FastAPI validation and authorization.
3. Update the Next.js adapter/view.
4. Update the Expo adapter/view.
5. Verify web and native build paths independently.
6. Update the relevant architecture flow or ADR if a boundary changed.

## Sensitive areas

- OAuth client IDs are public identifiers; client secrets and signing credentials
  are secrets.
- JWT secrets, database URLs and provider credentials belong only in environment
  configuration.
- User data and assessment history are application data; never paste production
  records into documentation or fixtures.
- Medical evidence must retain provenance and verification status.
