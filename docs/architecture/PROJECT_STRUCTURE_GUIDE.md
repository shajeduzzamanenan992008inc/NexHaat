# NexHaat Project Structure Guide

## Current verified structure

NexHaat is a single repository with several deliberate runtime boundaries:

| Area | Current location | Responsibility |
|---|---|---|
| Flask application | `app/` | Application factory, blueprints, models, services, repositories, templates, static assets, translations |
| Versioned API | `app/api/` | `/api/v1` blueprints, envelopes, errors, serializers |
| Flask AI | `app/ai/` and `app/routes/ai.py` | Scoped tools, providers, guardrails, permissions, marketplace assistants |
| React/Vite UI | `src/` | Google AI Studio-style pages, shared components, context, adapters, types, fallback mock data |
| Express AI service | `server.ts` | Gemini/science HTTP routes, WebSocket upgrade, local Vite/SPA serving |
| Android | `android/app/` | Retrofit client, DTOs, cookie/CSRF interceptors, Compose screens and tests |
| Database history | `migrations/` | Flask-Migrate/Alembic revisions |
| Python tests | `tests/` | Flask/service/API/security/AI regression coverage |
| Frontend tests | `src/**/*.test.ts` | Dependency-free TypeScript utility tests |
| Android tests | `android/app/src/test/` | DTO and remote utility unit tests |
| Documentation | root docs plus `docs/architecture`, `docs/plans`, `docs/operations` | API, database, architecture, phase evidence, runbooks |
| CI/release | `.github/workflows/` | CI, deployment, CodeQL, dependency review, config validation, SBOM |

This is the current structure, not a claim that every target capability is
live or staging-verified.

## Target architecture

The safe target is feature-oriented organization inside the existing runtime
boundaries, not a framework migration:

```text
NexHaat/
  app/
    api/                 # versioned Flask API boundary
    ai/                  # scoped AI core and tools
    models/              # SQLAlchemy ownership
    repositories/        # bounded query builders
    routes/              # HTML and feature route adapters
    services/            # business rules and integrations
    templates/ static/   # Flask UI and assets
  src/
    components/          # reusable React UI
    pages/               # existing route/view surfaces
    context/             # existing UI/session orchestration
    lib/                 # typed Flask, marketplace, Firebase, AI adapters
    types/ data/         # UI contracts and preserved preview data
  android/app/src/main/  # Retrofit/Compose client
  migrations/            # additive Alembic revisions
  tests/                 # Python integration/security/unit coverage
  docs/
    architecture/        # decisions, inventories, phase reports, registry
    templates/            # reusable contribution templates
    plans/                # canonical roadmap
  .github/               # instructions, runbooks, workflows, agent profiles
```

Do not create empty `frontend/`, `server/`, or `shared/` folders solely to
match a generic template. Existing roots are the compatibility contract.

## Feature placement rules

1. Keep Flask business rules in `app/services`; keep handlers thin.
2. Keep SQLAlchemy models in `app/models` and query composition in
   `app/repositories`; schema changes belong in `migrations`.
3. Keep versioned JSON contracts in `app/api`; do not duplicate them in
   Express or the browser.
4. Keep React reusable UI in `src/components`, view composition in `src/pages`,
   orchestration in `src/context`, and server adapters in `src/lib`.
5. Keep AI provider/tool policy in server-side `app/ai` or `server.ts`; browser
   code may present results but cannot grant permissions.
6. Keep Android network contracts under `android/app/src/main/.../data/remote`.
7. Put new tests beside the established suite that owns the contract.
8. Add documentation under the closest existing `docs` area; do not create
   competing roadmap or architecture sources.

## Change safety validation

Run `python scripts\validate_repository_structure.py` for registry, required
file, simple import-path, and boundary checks. Source deletions and renames
are reported as `REVIEW_REQUIRED`, not silently restored. A reviewer must
compare them with the planned change and approve or reject them. CI may use
`--fail-on-review` for protected branches after the policy is intentionally
configured; this checker is not a substitute for branch protection or review.
