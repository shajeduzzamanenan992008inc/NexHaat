# Phase 20 — Project Structure Standardization Report

**Date:** 2026-11-01  
**Status:** PASS for audit and standards; PARTIAL for migration because no
file moves were authorized or required

## Existing architecture inventory

| Boundary | Verified locations | Responsibility |
|---|---|---|
| Flask application | `app/__init__.py`, `app/routes`, `app/api`, `app/models`, `app/services`, `app/repositories` | Factory, HTML/API routes, domain data, business rules, bounded queries |
| React/Vite | `src/App.tsx`, `src/pages`, `src/components`, `src/context`, `src/lib`, `src/types`, `src/data` | AI Studio-style UI, state orchestration, typed adapters, preserved preview data |
| Express/Node | `server.ts`, `package.json`, `vite.config.ts` | Gemini/science routes, WebSocket, local SPA serving |
| Android | `android/app/src/main`, `android/app/src/test` | Retrofit/Compose marketplace client and unit tests |
| Database | `app/models`, `migrations`, `DATABASE.md` | SQLAlchemy models and additive Alembic revisions |
| Tests | `tests`, `src/**/*.test.ts`, `android/app/src/test` | Python, frontend utility, Android verification |
| Docs/operations | `README.md`, `API.md`, `ARCHITECTURE.md`, `DATABASE.md`, `docs/architecture`, `.github/runbooks` | Developer, API, data, phase, release, backup, and AI guidance |
| CI/release | `.github/workflows` | CI, deployment, CodeQL, dependency, config, SBOM/provenance checks |

## Target architecture

The target retains these roots and adds feature-oriented rules inside them.
`app/` remains the Flask bounded monolith, `src/` remains the React/Vite
frontend, `server.ts` remains the Express AI entrypoint, and `android/`
remains the Android project. New documentation and templates now have
predictable locations under `docs/`.

The target does **not** introduce empty `frontend`, `server`, `shared`, or
microservice folders. Such a move would not improve current ownership and
would risk breaking imports, route registration, deployment scripts, Android
packages, and user changes.

## Migration result

**Exact file move list: none.** The Phase 20 plan records current-to-proposed
paths, references, risks, compatibility requirements, and rollback procedures.
The safe action for this repository is documentation standardization, not a
bulk folder migration.

## Import and route consistency

- Flask blueprint registration is centralized in `app/__init__.py`; `/api/v1`
  registration is centralized in `app/api/__init__.py`.
- React page imports are preserved in `src/App.tsx`, including the existing
  route-level lazy loading from Phase 15.
- Flask auth and marketplace clients remain `src/lib/flaskAuth.ts` and
  `src/lib/marketplaceApi.ts`; no duplicate client was created.
- Express route registrations remain in `server.ts`; package scripts still
  point at the root entrypoint.
- Android package references, Retrofit service, DTOs, cookie jar, and CSRF
  interceptor remain under their existing Gradle package tree.
- Alembic revisions remain in `migrations`; Python, TypeScript, and Android
  test discovery paths were not moved.

## Deliverables

| Deliverable | Result |
|---|---|
| `docs/PROJECT_STRUCTURE_GUIDE.md` | **PASS** — current inventory, target structure, placement rules |
| `docs/DEVELOPMENT_CONVENTIONS.md` | **PASS** — naming, boundaries, testing, security, documentation |
| `docs/architecture/PHASE20_STRUCTURE_MIGRATION_PLAN.md` | **PASS** — no-move plan with risks and rollback |
| `docs/architecture/PHASE20_STRUCTURE_STANDARDIZATION_REPORT.md` | **PASS** — evidence-based audit and result |

## Validation evidence

| Check | Result |
|---|---|
| `npm run lint` | **PASS** — TypeScript check completed |
| `npm run build` | **PASS with existing large-chunk warning** — production bundle completed |
| `python -m pytest -q` | **PASS** — 305 passed in 443.75s |
| `.\android\gradlew.bat -p android :app:test --no-daemon` | **PASS with existing warnings** — BUILD SUCCESSFUL in 2m 7s |
| `python -m compileall -q app tests migrations run.py wsgi.py` | **PASS** |
| Flask route registration smoke check | **PASS** — 202 registered rules; required routes present |
| Feature registry path validation | **PASS** — 6 features, 0 missing paths |
| `git diff --check` | **PASS** |

## Limitations and rollback

This is an architecture/documentation standardization, not a completed physical
reorganization. Future moves require separate approval, complete reference
search, compatibility shims where needed, focused validation, and an exact
rollback patch. Rollback of this phase removes only the new documentation.

No existing feature was intentionally removed, disabled, replaced, or
downgraded. No production deployment, restart, configuration/database
mutation, commit, push, merge, or destructive Git action occurred.
