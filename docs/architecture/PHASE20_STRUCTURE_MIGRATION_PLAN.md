# Phase 20 — Structure Migration Plan

**Status:** PLAN ONLY / NO FILE MOVES PERFORMED  
**Date:** 2026-11-01

## Decision

The current monorepo layout is already aligned with the actual Flask, React,
Express, Android, and Alembic runtimes. A bulk move to a generic
`frontend/`, `server/`, or `shared/` structure would create unnecessary import,
deployment, Android, and user-change risk. Phase 20 therefore standardizes
placement rules and creates a staged migration plan without moving files.

## Proposed batches

| Current path | Proposed path | Reason | References/impact | Risk | Decision |
|---|---|---|---|---|---|
| `src/lib/*` | Keep `src/lib/*` | Existing typed Flask, marketplace, Firebase, and utility adapters are the correct browser boundary | Imported by `src/context`, pages, and components; Vite build depends on current paths | Low | Keep |
| `src/pages/*` | Keep `src/pages/*` | `src/App.tsx` lazy route/view imports and UI navigation depend on these stable paths | Route imports, tests, and dynamic chunks | Low | Keep |
| `app/routes/*` | Keep `app/routes/*` | Flask blueprint names and `app/__init__.py` registrations are established contracts | Blueprint registration, templates, URL endpoints | High | Keep |
| `app/api/*` | Keep `app/api/*` | `/api/v1` registration and Android/React clients depend on the boundary | API imports, response envelopes, deployment checks | High | Keep |
| `app/services/*` | Keep `app/services/*` | Services own transaction, media, backup, AI, and integration rules | Routes, CLI, tests, migrations | High | Keep |
| `server.ts` | Keep root entrypoint; optionally extract internal modules later | `package.json`, Vite fallback, Express routes, WebSocket setup, and local commands use it | Start/build scripts and route behavior | Medium | No move in Phase 20 |
| `android/app/src/main/...` | Keep Gradle package tree | Android package names, manifests, tests, and Retrofit imports require stability | Kotlin imports, Gradle, runtime manifest | High | Keep |
| `tests/*` | Keep root Python suite; add feature subfolders only with test-discovery proof | CI invokes root `tests/` and current fixtures are shared | Pytest discovery and imports | Medium | No move |
| `docs/*` | Add documented subdirectories only | Existing roadmap/report links are stable; new templates/registry fit current docs | Markdown links and operator handoff | Low | Additive docs only |

## Safe future moves

Any future move must be one small batch and include:

1. a complete reference search for Python, TypeScript, templates, workflows,
   Gradle, packaging, dynamic imports, and documentation;
2. compatibility re-exports or import shims where external paths are known;
3. one focused test/build cycle before the next batch;
4. an exact old-to-new path table and rollback patch;
5. no simultaneous schema, dependency, workflow, or production changes.

No move is approved merely because the target layout looks cleaner.

## Compatibility verification checklist

- [x] Flask blueprint registration remains centralized in `app/__init__.py`.
- [x] Versioned API registration remains centralized in `app/api/__init__.py`.
- [x] React lazy imports remain under `src/pages`.
- [x] Flask and marketplace adapters remain under `src/lib`.
- [x] Express entrypoint remains `server.ts` and package scripts remain valid.
- [x] Android Retrofit/DTO/interceptor package paths remain unchanged.
- [x] Alembic revisions remain under `migrations`.
- [x] Python tests remain under `tests`; TypeScript tests remain under `src`.
- [x] CI/deployment references were not changed by Phase 20.

## Rollback

Because no file move was performed, rollback is documentation-only: remove the
Phase 20 plan and standards documents if explicitly requested. If a future
batch moves files, restore the original path and compatibility exports from
that batch's recorded patch; do not use `git reset`, `git clean`, or bulk
restore.

