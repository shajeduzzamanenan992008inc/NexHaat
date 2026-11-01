# Phase 20 — Permanent AI Feature Integration Standard

**Date:** 2026-11-01  
**Status:** PASS for standard/checker establishment; PARTIAL for live
provider/staging verification

## Standards created

| File | Result |
|---|---|
| `docs/PROJECT_STRUCTURE_GUIDE.md` | Real repository placement and boundary rules |
| `docs/GOOGLE_AI_STUDIO_INTEGRATION.md` | Google AI Studio import, mapping, preservation, security, and validation rules |
| `AGENTS.md` | Universal AI coding-agent contribution rules added without replacing prior guidance |
| `docs/AI_FEATURE_INTEGRATION_GUIDE.md` | Cross-tool feature intake, safety, acceptance, and rollback contract |
| `docs/templates/AI_FEATURE_SUBMISSION_TEMPLATE.md` | Reusable submission template |
| `docs/architecture/FEATURE_REGISTRY.json` | Verified six-feature registry with paths and statuses |
| `scripts/validate_repository_structure.py` | Lightweight objective path/boundary/registry checker |

## Permanent placement rules

- React pages remain in `src/pages`; reusable UI in `src/components`; state in
  `src/context`; adapters in `src/lib`; shared UI contracts in `src/types`.
- Flask API endpoints remain in `app/api`; HTML route adapters in `app/routes`;
  business logic in `app/services`; query composition in `app/repositories`;
  models in `app/models`; migrations in `migrations`.
- Express/Gemini/science functionality remains behind `server.ts` and its
  server-side provider boundary.
- Android code remains in its Gradle package tree under `android/app`.
- Tests remain with their actual owners: root Python `tests`, frontend
  `src/**/*.test.ts`, and Android `android/app/src/test`.
- Documentation belongs under the existing `docs` hierarchy; no duplicate
  architecture or roadmap source is introduced.

## Google AI Studio rules

Generated exports must be inspected before copying, mapped to existing
components/types/adapters, and validated for routes, imports, dependencies,
Firebase/mock data, direct provider calls, secrets, accessibility, and
security. Their design and useful behavior should be preserved, but existing
pages/routes must not be silently replaced. Marketplace operations must use
Flask APIs and server authority; Firebase and Express remain explicit
compatibility/auxiliary boundaries; Copilot OTP remains canonical.

## Structural validation

The checker is deliberately dependency-free and non-destructive. It verifies:

- required architecture/contribution documents exist;
- registry JSON parses, feature IDs are unique, and every listed path exists;
- browser source does not add direct `/api/v1` calls outside `src/lib`;
- Express AI call sites are reported separately rather than incorrectly
  rejected;
- worktree/source entries are counted for review without deleting or rejecting
  legitimate user changes.

It does not prove runtime behavior, dependency vulnerability status, provider
health, browser CORS, authorization, or production readiness.

## Validation evidence

| Check | Result |
|---|---|
| `python scripts\validate_repository_structure.py` | **PASS** — required docs present, 58 registry paths checked, 0 direct marketplace calls outside adapters, 1 Express AI call site reported, worktree review counts emitted |
| Registry path validation | **PASS** — 6 features, 0 missing paths |
| `npm run lint` | **PASS** — TypeScript check |
| `npm run build` | **PASS with existing warning** — Vite large chunks remain (`index` 1,017.94 kB; Admin 471.78 kB) |
| `python -m pytest -q` | **PASS** — 305 passed in 432.47s |
| `.\android\gradlew.bat -p android :app:test --no-daemon` | **PASS with existing warnings** — BUILD SUCCESSFUL in 2m 4s |
| `python -m compileall -q app tests migrations run.py wsgi.py` | **PASS** |
| Flask route registration smoke check | **PASS** — 202 rules; required routes present |
| `git diff --check` | **PASS** |

## Remaining risks

Phase 17/18 blockers remain: approved staging browser/API CORS and authenticated
role testing, real provider/OTP/payment checks, Android device E2E, PostgreSQL/
Azure recovery, and disposable restore rehearsal. The checker cannot replace
those environment gates.

No existing feature was intentionally removed, disabled, downgraded, or
replaced. No file was moved. No commit, push, merge, deployment, production
restart, or production configuration/database change occurred.
