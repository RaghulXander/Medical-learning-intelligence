# DocEdge AI Engineering Documentation

This site documents the architecture and operation of the medical education
platform as it exists today.

## Start here

- New developer: [Local development](LOCAL_DEVELOPMENT.md)
- System boundaries: [Architecture overview](ARCHITECTURE.md)
- Production operator: [Deployment](DEPLOYMENT.md)
- Schema or ingestion work: [Data model](DATA_MODEL.md) and
  [data sources](DATA_SOURCES.md)
- Architectural change: [Architecture decisions](decisions/README.md)
- Unsure what to edit: [Ownership and change impact](OWNERSHIP.md)

## Current production topology

| Capability | Current implementation |
|---|---|
| Public and authenticated web | Next.js on Vercel |
| Native student client | Expo/React Native, built with EAS |
| Application API | Python FastAPI container on Render |
| System of record | PostgreSQL on Neon |
| Identity | Password/JWT plus Google OpenID Connect |
| Schema changes | Alembic migrations during controlled release startup |

Documentation is maintained beside code. Update affected pages and ADRs in the
same pull request as an architectural change.
