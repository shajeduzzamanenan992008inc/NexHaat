# Phase 19 — Repository Structure Audit and Safe Fixes

**Date:** 2026-11-01  
**Status:** PASS for confirmed safe fixes; PARTIAL for unresolved integration
gates

## Scope and dependency

Phase 17 and Phase 18 were reviewed before this audit. They remain
**PARTIAL/BLOCKED** because approved staging React→Flask browser integration
and a disposable restore target are unavailable. This phase therefore changes
only repository guidance, documentation, and a read-only structural checker.
No production, database, dependency, route, or runtime behavior was changed.

## Actual repository inventory

| Boundary | Verified paths | Responsibility |
|---|---|---|
| Flask | `app/__init__.py`, `app/api`, `app/routes`, `app/services`, `app/repositories`, `app/models`, `app/templates`, `app/static` | Authoritative marketplace, session/CSRF/OTP, HTML/API, business rules, database access |
| React/Vite | `src/App.tsx`, `src/pages`, `src/components`, `src/context`, `src/lib`, `src/types`, `src/data` | AI Studio-style UI, state, adapters, shared types, preserved preview data |
| Express/Node | `server.ts`, `package.json`, `vite.config.ts` | Gemini/science routes, WebSocket, local SPA serving |
| Android | `android/app/src/main` and `android/app/src/test` | Retrofit/Compose client, DTOs, cookie/CSRF, unit tests |
| Database | `migrations`, `app/models`, `DATABASE.md` | Alembic revisions and SQLAlchemy schema |
| Tests | `tests`, `src/**/*.test.ts`, `android/app/src/test` | Python, frontend utility, Android verification |
| CI/release | `.github/workflows` | CI, deployment, CodeQL, dependency, config, SBOM/provenance |
| Docs | root docs, `docs/architecture`, `docs/plans`, `docs/operations`, `docs/templates` | Canonical roadmap, contracts, reports, runbooks, contribution standards |

## Confirmed structural findings

| Finding | Evidence/dependencies | Risk | Safe correction | Validation |
|---|---|---:|---|---|
| AI contribution rules were not present in `AGENTS.md` | Existing file had roadmap/preservation guidance but no universal intake, reuse, test, or no-deploy rules | Medium | Added concise repository-wide AI contribution rules without changing existing guidance | Read file; full checks |
| Google AI Studio had no dedicated repository integration standard | Existing Phase 5–20 material described boundaries, but no direct reusable workflow existed | Medium | Added `docs/GOOGLE_AI_STUDIO_INTEGRATION.md` | Required-doc checker |
| Registry/path checks were manual and not repeatable | `FEATURE_REGISTRY.json` existed but no maintained checker existed | Medium | Added dependency-free `scripts/validate_repository_structure.py` | Checker PASS |
| Marketplace and Express AI calls are separate but easy for generated code to confuse | `src/lib/*` uses Flask `/api/v1`; `AIAssistantDrawer.tsx` uses Express `/api/gemini` and `/api/science` | Medium | Documented explicit authority/adapter boundaries; no behavior change | Boundary checker, lint/build |
| Structure documentation needed to name the real roots | Actual repo has root `src/`, `app/`, `server.ts`, and `android/`, not generic `frontend/`/`server/` trees | Low | Updated standards to preserve current roots and prohibit speculative bulk moves | Inventory review |

## Investigated but intentionally not changed

- `src/lib/flaskAuth.ts` and `src/lib/marketplaceApi.ts` are the established
  Flask/session and marketplace adapters; no duplicate browser marketplace
  client was found.
- `src/components/AIAssistantDrawer.tsx` directly calls the existing Express
  AI routes by design. It is not a duplicate Flask marketplace client and was
  left intact to preserve Google AI Studio functionality.
- Firebase code and `AppContext` local/mock fallback are preserved compatibility
  surfaces, not safe deletion candidates; Phase 5–18 explicitly require them to
  remain until an approved migration.
- Flask server-rendered routes and `/api/v1` routes intentionally overlap in
  domain capability but use separate presentation boundaries. They were not
  merged or renamed.
- Legacy names, generated Android state, Playwright artifacts, and untracked
  user/project files were not cleaned because ownership and removal were not
  authorized.
- No objectively broken import, route registration, Vite alias, or Android
  package reference was found in the inspected paths.

## Safe fixes made

- Extended `AGENTS.md` with permanent AI contribution rules.
- Added `docs/GOOGLE_AI_STUDIO_INTEGRATION.md`.
- Added `scripts/validate_repository_structure.py`.
- Added this audit report.
- Kept existing `docs/PROJECT_STRUCTURE_GUIDE.md` and registry, while using
  the checker to validate their actual paths.

## File moves

**None.** No file was moved. A move would not be safe without changing
imports, blueprint references, Vite/build paths, Gradle packages, CI, or
documentation and would provide no measured benefit here.

## Rollback

Remove only the additive AI rules, Google guide, checker, and this report if a
reviewed rollback is requested. Do not revert pre-existing source, workflow,
Android, reports, or user files. No schema or runtime rollback is needed.

