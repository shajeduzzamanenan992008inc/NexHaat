# Phase 19 — Repository Baseline, Forensics, and AI-Safe Protection

**Date:** 2026-11-01  
**Status:** PARTIAL — local protections and evidence are complete; GitHub
branch-protection inspection is blocked by unavailable `gh` authentication.

## Baseline

| Item | Evidence |
|---|---|
| Repository | `shajeduzzamanenan992008inc/NexHaat` |
| Branch | `main` |
| `HEAD` | `27df5864516cf6176c7d332818cfc2a9d904c903` (`Updated a file`) |
| Remote relation | `main...origin/main` at inspection time |
| Worktree | 74 status entries, including pre-existing user changes, generated Android state, reports, and untracked configuration/docs |
| Tracked source inventory | 414 files under `app`, `src`, `android`, `tests`, and `migrations` |
| Production mutation | None |

The worktree was inspected before editing and no existing user change was
discarded, reset, cleaned, overwritten, committed, pushed, deployed, or
restarted.

## Historical deletion investigation

Git history contains real deletion events. They are evidence requiring review,
not proof that every deletion was accidental:

| Commit | Historical evidence | Assessment |
|---|---|---|
| `4323da3` — `feat: initialize NexHaat frontend architecture` | 366 deleted paths in the inspected application/Android/test/migration areas; approximately 8,249 additions and 64,652 deletions in the selected numstat scope | **HIGH review interest.** This appears to be a large architecture replacement/transition, including prior Android and Flask trees. Current source, route registration, tests, and Android build remain present, so no automatic restoration was safe. |
| `0517738` — `feat: integrate Firebase auth and expand AI assistant` | 3 deleted `android/.gradle` lock files, with Firebase/Express/React additions | **LOW.** Generated Gradle-state cleanup, not application feature loss based on the paths inspected. |
| `27df586` — `Updated a file` | 1 deleted migration path: `migrations/versions/20261031_01_banners_b.py` | **MEDIUM review interest.** The current repository retains `20261031_01_banners.py`; the `_b` suffix appears to be a duplicate migration candidate, but migration deletion must remain an explicit human-reviewed decision. |

No historical file was restored automatically. Restoring a historical
implementation without a current contract, migration plan, and dependency
review could reintroduce duplicate routes, schemas, or security behavior.

## Confirmed current structural findings

- The repository has deliberate root boundaries: Flask in `app/`, React/Vite
  in `src/`, Express in `server.ts`, Android in `android/`, and tests in
  `tests/`/Android test roots. No safe mass move was found.
- `src/lib/flaskAuth.ts` and `src/lib/marketplaceApi.ts` are the canonical
  browser adapters; no accidental second Flask marketplace client was found.
- Firebase and Express/Gemini are separate preserved capabilities, not a
  replacement for Flask identity or commerce authority.
- Flask route registration is centralized and the required health/auth/catalog
  routes are present. No duplicate registry feature IDs or missing registry
  paths were found.
- The previous process gap was lack of repeatable deletion/import/config
  review. This is now covered by the structural checker and CI job.

## Protections implemented

1. `scripts/validate_repository_structure.py` validates required documents and
   configuration, registry JSON/paths/IDs, simple relative TypeScript imports,
   direct browser marketplace boundaries, and source deletion/rename review.
2. Deletions and renames produce `REVIEW_REQUIRED`; they are never restored
   automatically and are not silently approved by a blanket allowlist.
3. `--fail-on-review` provides an explicit strict gate for CI/release use.
4. `.github/workflows/ci.yml` now runs the checker additively in a read-only
   `structure-validation` job.
5. `AGENTS.md`, the AI integration guides, and the structure guide require
   pre-edit status inspection, search-before-create, planned move/delete review,
   exact validation evidence, and human review of unexpected diffs.

## GitHub controls

Existing workflows include Python tests/lint, web checks, deployment,
configuration validation, CodeQL, dependency review, and SBOM/provenance
definitions. The new structure job is configured but was not run by GitHub in
this local-only task. `gh repo view`/branch-protection inspection could not
run because the local GitHub CLI session is unauthenticated; branch
protection, required checks, environments, and repository secrets are
therefore **NOT VERIFIED**. No secret values were requested or exposed.

## Rollback

Revert only the additive checker, workflow job, instructions, and report after
review. Do not restore or delete historical application files, migrations, or
generated user files as part of rollback. The checker and documentation do not
change runtime or database behavior.

