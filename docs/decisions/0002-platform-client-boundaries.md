# ADR 0002 — Share client logic, not platform UI primitives

- Status: Accepted
- Date: 2026-08-27
- Owners: Web and mobile maintainers
- Supersedes: none

## Context

Next.js renders DOM elements with React 18. Expo renders native primitives with
React Native and React 19. Attempting to reuse DOM components directly would
either require a WebView or a migration to a universal rendering system.

## Decision

Share domain schemas, API calls, validation and headless feature behavior through
workspace packages. Keep thin web/native presentation and OAuth credential
acquisition adapters platform-specific.

## Consequences

Business and API changes can be made once, while visual changes may still require
two views. M12 will identify reusable tokens, form models and headless hooks and
remove accidental duplication.

## Alternatives considered

- WebView wrapper: rejected because of OAuth, store-review, navigation and native
  experience limitations.
- Immediate React Native Web migration: rejected as too disruptive during alpha.
- PWA only: remains a valid distribution fallback, not the selected native UX.

## Validation

Measure duplicated feature code during M12. Revisit if platform shells contain
substantial duplicated business logic rather than presentation.
