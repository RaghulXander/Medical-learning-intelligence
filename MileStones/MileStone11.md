# Milestone 11 — Architecture Documentation & Multi-Developer Enablement

## 1. Purpose

Milestone 11 turns the repository's architecture knowledge into maintained,
reviewable documentation that another developer can use without relying on
oral history.

The milestone documents the system that exists now. It does not redesign the
application, perform the M12 code review, or introduce microservices.

## 2. Outcomes

At completion, a developer should be able to answer:

1. What runs in production and where?
2. Which application owns a feature or API?
3. How do web, mobile, backend, PostgreSQL and external identity interact?
4. Where are authentication, authorization and subscription checks enforced?
5. How are schema and deployment changes released safely?
6. Why were important architectural choices made?
7. Which files must change when a cross-platform feature changes?
8. How is documentation validated and kept current?

## 3. Current-state findings

- The active backend is a Python FastAPI modular monolith, while the previous
  architecture document described a future Node/Express backend.
- Production topology is Vercel (web), Render (FastAPI), Neon (PostgreSQL) and
  Expo/EAS (native builds).
- `apps/mobile` is the active Expo application; `apps/student-native` is a
  historical workspace and must not be presented as the production client.
- Web and native share domain schemas and the API client, but presentation and
  OAuth adapters remain platform-specific.
- FastAPI already provides an OpenAPI schema; duplicating endpoint contracts by
  hand would create drift.
- Deployment and local-development documents exist, but ownership, decision
  history, system boundaries and change-impact guidance are incomplete.

## 4. Documentation stack

### Selected now

| Need | Tool | Reason |
|---|---|---|
| Searchable documentation portal | Material for MkDocs | Reuses Markdown and Python already used by the repository |
| Diagrams | Mermaid | Renders in GitHub and MkDocs with no image-editing workflow |
| Architecture decisions | Markdown ADRs | Reviewable in the same pull request as code |
| API contract | FastAPI OpenAPI | Generated from the actual routes and Pydantic models |
| Link/build validation | `mkdocs build --strict` | Fails CI for broken navigation and invalid documentation |

### Deferred

- **Structurizr DSL:** useful when multiple C4 views need to be generated from
  one model. Adopt after the initial C4 vocabulary is reviewed.
- **Backstage TechDocs:** valuable for many services and teams, but excessive
  for the current modular monolith.
- **Generated Python/TypeScript symbol reference:** add only for stable public
  modules. Source-generated API reference must not replace task-oriented guides.

## 5. Information architecture

```text
docs/
  index.md                    Documentation entry point
  ARCHITECTURE.md             Current architecture overview
  architecture/
    SYSTEM_CONTEXT.md         Users and external systems
    CONTAINERS.md             Deployable/runtime boundaries
    DEPLOYMENT_VIEW.md        Production and local topology
  decisions/
    README.md                 ADR index and rules
    0000-template.md          Decision template
    0001-modular-monolith.md
    0002-platform-client-boundaries.md
    0003-alpha-hosting.md
  OWNERSHIP.md                Change ownership and impact map
  LOCAL_DEVELOPMENT.md
  DEPLOYMENT.md
  DATA_MODEL.md
  DATA_SOURCES.md
  KNOWLEDGE_BASE.md
  PRD.md
  ROADMAP.md
```

## 6. Architecture views

M11 will maintain the smallest useful C4-inspired set:

1. **System context:** students, administrators, developers, Google Identity,
   the DocEdge platform and external evidence sources.
2. **Container view:** Next.js web, Expo mobile, shared TypeScript packages,
   FastAPI backend, PostgreSQL and future optional worker/ML boundaries.
3. **Deployment view:** Vercel, Render, Neon, EAS/App Stores and local Docker.
4. **Dynamic views:** Google sign-in, onboarding, assessment execution and
   question review only where sequence matters.

Diagrams describe responsibilities and trust boundaries, not every class.

## 7. Architecture Decision Records

Create an ADR when a choice:

- changes a runtime or deployment boundary;
- introduces or removes a datastore/provider;
- changes authentication, authorization or medical provenance rules;
- affects both web and native clients;
- is expensive to reverse; or
- deliberately accepts material technical debt.

ADR lifecycle: `Proposed → Accepted → Superseded` or `Rejected`.
Accepted ADRs are immutable except for corrections and links. A changed decision
gets a new ADR that supersedes the old one.

## 8. Ownership and change-impact map

Every major area will document:

- authoritative source directory;
- runtime owner;
- consumers;
- required verification;
- security/data sensitivity;
- deployment target.

Cross-platform authentication is the first worked example: shared types and API
calls live in packages, backend token verification lives in FastAPI, while web
and native acquire Google credentials with platform-specific adapters.

## 9. API documentation

- FastAPI `/openapi.json` remains the canonical machine-readable contract.
- Local Swagger/ReDoc remains the interactive developer reference.
- Production exposure remains controlled by environment policy.
- CI will eventually export and diff OpenAPI to reveal accidental breaking
  changes.
- Handwritten docs explain workflows and authorization; they do not copy every
  request/response field.

## 10. Data documentation

M11 documents:

- PostgreSQL as the system of record;
- Alembic as the schema-change authority;
- canonical taxonomy, curriculum and provenance separation;
- status transitions for questions and reports;
- data retention and backup responsibilities;
- prohibition on invented or unverified medical citations.

Schema refactoring remains M12 or a dedicated migration milestone.

## 11. Multi-developer workflow

Every pull request that changes architecture must include one or more of:

- updated architecture view;
- new/superseding ADR;
- updated ownership/change-impact entry;
- updated deployment or operational runbook;
- explicit statement that no documentation change is required.

Documentation examples must avoid real credentials, patient data and copyrighted
source text.

## 12. Phases

### Phase 11.1 — Correct the current record

- Replace the stale Node backend diagram with the FastAPI modular monolith.
- Record Vercel/Render/Neon/EAS deployment topology.
- normalize active `apps/mobile` naming;
- identify `apps/student-native` as historical pending M12 disposition.

### Phase 11.2 — Documentation portal

- Add MkDocs configuration and pinned documentation requirements.
- Add navigation, Mermaid rendering, search and strict builds.
- Keep all pages readable directly in GitHub.

### Phase 11.3 — C4 and dynamic views

- System context, containers and deployment views.
- Authentication and assessment sequences.
- Trust boundaries and external dependencies.

### Phase 11.4 — ADR system

- Add template, index and initial accepted decisions.
- Link ADRs from affected architecture pages.

### Phase 11.5 — Contracts and ownership

- Add repository ownership/change-impact map.
- Generate/check OpenAPI from FastAPI.
- Document shared-package compatibility rules for web and React Native.

### Phase 11.6 — CI and handoff

- Run `mkdocs build --strict` in CI.
- Check internal links and stale workspace names.
- Add a documentation update checklist to contribution guidance.

## 13. Acceptance criteria

- [ ] Architecture describes actual code and production providers.
- [ ] A new developer can locate the owner of every major feature area.
- [ ] System context, container and deployment views render correctly.
- [ ] Authentication and assessment flows have sequence documentation.
- [ ] Initial architectural choices are captured as ADRs.
- [ ] API reference comes from FastAPI OpenAPI.
- [ ] `mkdocs build --strict` passes locally and in CI.
- [ ] README links directly to M11 and the documentation portal entry point.
- [ ] No documentation contains secrets or invented medical references.
- [ ] Historical `apps/student-native` usage is clearly marked or removed in M12.

## 14. Out of scope

- Python/React/React Native code-quality refactoring (M12).
- A unified cross-platform component library implementation (M12).
- Landing-page CMS/widgets (M13).
- Payment/subscription automation (M50).
- Backstage, a service catalog or a developer portal runtime.
- Splitting the modular monolith into microservices.

## 15. Risks and controls

| Risk | Control |
|---|---|
| Documentation becomes stale | Validate in CI and update in the same PR as code |
| Diagrams become unreadable | Limit each view to one abstraction level |
| Generated docs replace explanation | Separate reference from guides and decisions |
| Tooling becomes another product | MkDocs only; defer Backstage and hosted Structurizr |
| Credentials leak into examples | Use placeholders and secret scanning |
| Architecture docs become aspirational | Label future components explicitly and document current state first |

## 16. First implementation slice

1. Add the MkDocs portal skeleton.
2. Replace `docs/ARCHITECTURE.md` with the current system overview.
3. Add C4 context/container/deployment pages.
4. Add ADR conventions and the first three decisions.
5. Add ownership/change-impact documentation.
6. Validate navigation and Mermaid rendering.
