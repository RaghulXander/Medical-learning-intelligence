# ADR 0001 — Use a Python FastAPI modular monolith

- Status: Accepted
- Date: 2026-08-27
- Owners: Backend maintainers
- Supersedes: aspirational Node/Express backend documentation

## Context

The MVP needs authentication, question management, assessments and ingestion,
but does not have independent scaling or ownership needs that justify multiple
application services.

## Decision

Use one Python FastAPI deployable with route and service modules. PostgreSQL is
the system of record. ML may become a separately deployed service only when its
runtime or scaling requirements demand isolation.

## Consequences

Transactions, deployment and local development remain simple. Module boundaries
must be enforced through code review rather than network APIs. A slow or failing
module can affect the single API process.

## Alternatives considered

- Node API plus Python ML service: rejected because the implemented backend and
  data pipeline are already Python and a second application runtime adds no MVP
  value.
- Feature microservices: rejected until measured scaling/team boundaries exist.

## Validation

Revisit when a workload needs independent scaling, failure isolation, security
boundary or ownership.
