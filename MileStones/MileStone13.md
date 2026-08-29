# Milestone 13 — Landing Page Widget CMS

Implementation status: Core end-to-end slice implemented. Typed content,
JSON-driven widgets, admin editing/preview/import/export, RBAC validation,
GitHub SHA-safe publishing and audit logging are available. Media management,
history/rollback UI and scheduled visibility remain follow-up phases.

## 1. Purpose

Milestone 13 builds a lightweight, Git-backed landing-page CMS for DocEdge AI.
It adapts the proven editor and publishing workflow from the owner's
[`RaghulXander/irg-space`](https://github.com/RaghulXander/irg-space) repository
to the medical-learning platform instead of introducing a hosted CMS dependency.

An authorized administrator should be able to:

- edit landing-page text and calls to action;
- show, hide and reorder sections;
- add supported widget types;
- manage repeatable items such as feature cards, statistics and testimonials;
- upload or select media;
- preview changes safely;
- save validated JSON;
- commit content changes to GitHub; and
- trigger or observe the Vercel deployment that publishes the content.

The CMS manages marketing content only. It must not manage questions, medical
evidence, users, entitlements or application configuration.

## 2. Reference implementation audit

The `irg-space` repository already implements several useful capabilities:

| Existing capability | Adaptation for DocEdge AI |
|---|---|
| `public/text-content.json` | Versioned `apps/web/content/landing-page.json` |
| `TabbedContentEditor` | Widget/section navigation with status and item counts |
| `RecursiveForm` | Schema-driven widget fields and repeatable item editor |
| Nested path updates | Typed immutable content updates |
| Enabled section switches | Widget visibility and scheduling controls |
| Change detection and reset | Draft dirty state, reset and unsaved-change warning |
| JSON export | Export plus validated import for disaster recovery |
| GitHub Contents API save | Server-side GitHub publisher with optimistic SHA checks |
| Commit SHA result | Publication record, audit trail and deployment link |
| Netlify build hook | Vercel deploy hook or Git-triggered Vercel build |
| Cloudinary media upload | Configurable media provider adapter |
| Content context/cache | Version-aware landing content loader with safe fallback |

The useful workflow is reused conceptually and, where compatible, through
adapted components. Space/product-specific content and styling are not copied.

## 3. Required security corrections

The following `irg-space` implementation details must not be carried forward:

1. No hardcoded admin hash in a URL.
2. No admin secret embedded in client JavaScript.
3. No secret transmitted in query parameters or request bodies.
4. No placeholder secret fallback.
5. No arbitrary unvalidated JSON accepted by the save endpoint.
6. No unrestricted file path, repository or branch supplied by the client.
7. No direct Cloudinary or GitHub credentials exposed to the browser.
8. No reliance on security-scanner evasion through constructed environment names.

The existing application JWT and RBAC system protects the CMS. Add explicit
permissions:

- `CONTENT_READ`
- `CONTENT_EDIT`
- `CONTENT_PUBLISH`
- `MEDIA_MANAGE`

`SUPER_ADMIN` receives all permissions. `ADMIN` may edit and publish. A future
content-editor role may edit drafts without publishing.

## 4. Content architecture

The CMS uses a typed widget registry rather than an unrestricted recursive JSON
editor.

```text
LandingPageDocument
  schemaVersion
  documentVersion
  site metadata
  sections[]
    id
    type
    enabled
    order
    audience
    schedule
    props
```

### Document example

```json
{
  "schemaVersion": 1,
  "documentVersion": "2026-08-29T10:00:00Z",
  "site": {
    "title": "DocEdge AI",
    "description": "Medical exam preparation with reviewed evidence"
  },
  "sections": [
    {
      "id": "home-hero",
      "type": "hero",
      "enabled": true,
      "order": 10,
      "audience": "ALL",
      "props": {
        "eyebrow": "Next-Gen Medical Exam Intelligence",
        "title": "Master Medical Exams",
        "highlight": "with Precision Intelligence",
        "description": "Pathology-focused learning and assessments",
        "primaryAction": {
          "label": "Try 5-Question Diagnostic",
          "action": "START_DIAGNOSTIC"
        }
      }
    }
  ]
}
```

The editor never accepts arbitrary executable component names, JavaScript,
HTML or URLs. Actions and widget types come from allow-listed registries.

## 5. Initial widget registry

Milestone 13 supports the current landing page first:

### `hero`

- eyebrow/badge
- title and highlighted text
- description
- primary and secondary actions
- optional background media

### `diagnostic_cta`

- title, description and badge
- question count and duration display
- `START_DIAGNOSTIC` action
- guest/authenticated visibility

### `stats`

- repeatable label/value cards
- optional verified/live-data flag

Static marketing statistics must not claim values that cannot be supported.
Later, selected statistics may come from server metrics instead of CMS text.

### `feature_grid`

- section badge, title and description
- repeatable feature cards
- approved icon key
- title, description and tag

### `content_block`

- title, body and optional image
- safe Markdown subset, sanitized during rendering

### `testimonial_grid`

- optional for later use
- name, role, quote and approved media

### `contact_cta`

- title and description
- contact email label
- allow-listed internal or `mailto:` action

No generic arbitrary-code widget is included.

## 6. Widget registry contract

Each widget type provides one definition shared by rendering and editing:

```ts
interface WidgetDefinition<T> {
  type: WidgetType;
  label: string;
  description: string;
  schema: ZodSchema<T>;
  defaults: T;
  editorFields: EditorFieldDefinition[];
  render: React.ComponentType<WidgetRenderProps<T>>;
}
```

This replaces the reference repository's field-name heuristics such as treating
any key containing `image` as an upload. Form controls are determined by schema
metadata and remain type safe.

## 7. Storage and source of truth

The published source of truth is:

```text
apps/web/content/landing-page.json
```

The JSON file is:

- committed to GitHub;
- validated during save and CI;
- imported during the Next.js build;
- bundled with a safe default document; and
- responsible only for public marketing content.

Git history provides content history and disaster recovery. The database stores
publication/audit metadata, not a competing published copy of the document.

## 8. Draft and publish modes

The reference repository commits on every save. DocEdge AI preserves that option
but separates its semantics explicitly.

### Target workflow

```text
Edit
  -> Validate
  -> Preview
  -> Save Draft
  -> Commit to configured CMS branch
  -> Publish
  -> Commit/merge published JSON
  -> Vercel deployment
```

### Current save-and-publish mode

The implemented alpha uses an explicit **Save & publish** action. An authorized
publish-capable administrator commits directly to the configured CMS branch;
the normal Vercel Git integration then deploys that commit. Editing and preview
remain local in the browser until the administrator chooses this action.

Save-and-publish includes:

- schema validation;
- authorization;
- current-file SHA/ETag comparison;
- a human-readable diff summary;
- audit record;
- commit SHA and URL; and
- explicit conflict handling.

## 9. GitHub publishing service

Publishing occurs server-side. The browser sends only validated content and its
expected base revision.

Required environment configuration:

```text
CMS_GITHUB_OWNER=RaghulXander
CMS_GITHUB_REPOSITORY=Medical-learning-intelligence
CMS_GITHUB_BRANCH=main
CMS_GITHUB_CONTENT_PATH=apps/web/content/landing-page.json
CMS_GITHUB_TOKEN=server-only credential
```

Prefer a repository-scoped GitHub App or fine-grained token restricted to the
target repository and contents permission. Never use the user's broad personal
token in client code.

### Concurrency behavior

1. Load content and current SHA.
2. Editor submits `baseSha` with the document.
3. Server reloads the current SHA.
4. A mismatch returns `409 CONTENT_CONFLICT` with no commit.
5. The editor reloads, compares and intentionally reapplies changes.

The service must never overwrite a newer commit silently.

## 10. Backend APIs

Suggested endpoints:

```text
GET  /api/cms/landing-page
POST /api/cms/landing-page/validate
PUT  /api/cms/landing-page/draft
POST /api/cms/landing-page/publish
GET  /api/cms/landing-page/history
POST /api/cms/landing-page/rollback/{commit_sha}
POST /api/cms/media
DELETE /api/cms/media/{media_id}
```

The backend owns RBAC, validation, GitHub interaction and publication audit.
The web application owns editing, preview and rendering.

## 11. Publication audit

Record each operation with:

- actor user ID;
- operation (`DRAFT_SAVE`, `PUBLISH`, `ROLLBACK`);
- base and resulting commit SHA;
- repository, branch and fixed content path;
- changed widget IDs;
- schema/document version;
- deployment trigger/result;
- timestamp and failure details.

Do not store GitHub tokens, full authorization headers or deploy-hook URLs.

## 12. Media management

The `irg-space` Cloudinary workflow is adapted behind a provider interface:

```ts
interface CmsMediaProvider {
  upload(file: ValidatedMediaFile, folder: string): Promise<CmsMedia>;
  delete(mediaId: string): Promise<void>;
}
```

Initial Cloudinary support may reuse the same general approach:

- server-side credentials;
- JPEG, PNG and WebP allow-list;
- size and dimension limits;
- normalized filenames;
- dedicated `docedge/cms` folder;
- generated provider ID and secure URL;
- deletion audit.

SVG, scripts and arbitrary remote URLs are excluded initially.

## 13. Editor experience

Reuse and adapt the strongest reference-repository behaviors:

- section tabs with icons, descriptions and counts;
- enabled/disabled state indicator;
- unsaved-change indicator;
- schema-aware nested forms;
- repeatable item add/remove;
- reorder by drag/drop plus keyboard-accessible controls;
- reset to loaded revision;
- JSON export;
- validated JSON import;
- desktop/mobile landing-page preview;
- detailed save/deploy progress;
- commit SHA and publication link;
- conflict and validation error presentation.

Improvements over the reference implementation:

- no `any` at content boundaries;
- no render-time state update for initial tab selection;
- no JSON-stringification keys to force component remounts;
- no guessed product-specific templates;
- accessible labels and keyboard ordering;
- error details safe for users and server logs.

## 14. Runtime rendering

The landing page stops defining marketing arrays inline in `page.tsx`.

```text
validated landing-page.json
  -> widget registry
  -> enabled/scheduled/audience filter
  -> stable order
  -> platform landing components
```

Business actions remain implemented in code. For example,
`START_DIAGNOSTIC` invokes the existing assessment workflow; the CMS can change
its label and visibility but cannot replace it with arbitrary JavaScript.

If content fails validation at build time, CI fails. If a runtime refresh option
is later enabled, invalid remote content is rejected and the last known valid
document remains visible.

## 15. CI/CD integration

Add CI checks for:

- JSON syntax and schema validation;
- duplicate widget IDs;
- duplicate or invalid order values;
- unsupported widget/action/icon types;
- unsafe URLs or Markdown;
- inaccessible required labels;
- landing-page render smoke test;
- secrets absent from the content file.

Git-based publishing normally triggers the existing Vercel integration. A deploy
hook is optional and must be idempotent. The UI should distinguish commit success
from deployment success.

## 16. Implementation phases

### Phase 13.1 — Port and harden the content contract

- Inventory current landing-page content.
- Create Zod schemas and shared TypeScript types.
- Create the initial JSON document and widget registry.
- Add schema validation tests and CI command.

### Phase 13.2 — Registry-based landing rendering

- Extract current Hero, Diagnostic CTA, Stats and Features into widgets.
- Render the ordered document through the registry.
- Preserve existing diagnostic behavior and responsive design.

### Phase 13.3 — CMS authorization and read APIs

- Add content permissions to central RBAC.
- Build authenticated content read and validation endpoints.
- Create publication audit storage.

### Phase 13.4 — Adapt the editor

- Port the tabbed editor, change tracking, reset and export behaviors.
- Replace `RecursiveForm` heuristics with schema field definitions.
- Add reorder, visibility and responsive preview.

### Phase 13.5 — GitHub commit workflow

- Implement server-side GitHub Contents API adapter.
- Enforce fixed repository/branch/path configuration.
- Add SHA conflict handling, commit summaries and audit records.
- Add an optional draft-branch workflow without changing the explicit
  save-and-publish default.

### Phase 13.6 — Media and deployment

- Add provider-based media upload.
- Connect Git-triggered Vercel deployment or optional deploy hook.
- Display commit and deployment state independently.

### Phase 13.7 — Rollback and production hardening

- Show commit history and changed widgets.
- Add authorized rollback to a previous valid document.
- Add rate limits, monitoring and failure alerts.
- Test simultaneous editors and deployment failures.

## 17. Deliverables

- `landing-page.json` and versioned schema.
- Shared typed CMS content package/module.
- Widget registry and extracted landing components.
- Authenticated CMS editor.
- Backend GitHub publishing adapter.
- Publication audit and history.
- Optional Cloudinary media adapter.
- Vercel deployment integration.
- CI validation and render tests.
- Operator setup and rollback documentation.

## 18. Acceptance criteria

Milestone 13 is complete when:

1. all current landing sections render from validated JSON;
2. administrators can edit, hide, show, add and reorder supported widgets;
3. invalid documents cannot be saved or built;
4. no CMS credential or admin secret reaches browser code;
5. existing JWT/RBAC determines editor and publisher access;
6. saving creates a Git commit with the expected SHA and audit record;
7. concurrent edits return a conflict rather than overwriting content;
8. save-and-publish is clearly identified as a deployment action;
9. Vercel publication status is visible independently from commit success;
10. rollback restores a previously valid content revision;
11. the diagnostic CTA still invokes code-owned assessment behavior; and
12. tests cover schema, authorization, conflicts, rendering and rollback.

## 19. Out of scope

- Editing medical questions or ontology content.
- Arbitrary React/HTML/JavaScript widgets.
- Full visual page-builder positioning.
- Multi-language content in the first release.
- User-authored scripts, CSS or tracking tags.
- Replacing GitHub with a third-party CMS.
