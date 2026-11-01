# Phase 21 — Protection System Test Report

**Date:** 2026-11-01  
**Status:** PASS for tested local protections; PARTIAL for language coverage

## Scope and preservation

Phase 19 and Phase 20 reports were read before this verification. The
validator, CI workflow, agent guidance, AI Studio guides, structure guide, and
feature registry were inspected before testing.

All failure scenarios used disposable temporary Git repositories. No NexHaat
application, test, migration, Android, or production file was deleted or
renamed to simulate a failure. No commit, push, merge, deployment, reset,
clean, production configuration change, database change, or service mutation
was performed.

## Protection test evidence

| Scenario | Evidence | Result |
|---|---|---|
| Unexpected source deletion | Disposable repository deleted `src/present.ts`; strict validator exited `1` and emitted `source deletions require human review` | **PASS** |
| Source rename within source tree | Disposable `git mv src/present.ts src/renamed.ts`; strict validator exited `1` | **PASS** |
| Source rename from source tree to documentation | Disposable `git mv src/present.ts docs/present.ts`; strict validator exited `1` after the additive fix | **PASS** |
| Missing side-effect TypeScript import | Disposable `import './missing'`; validator exited `1` and emitted `missing relative import target` | **PASS** |
| Missing normal TypeScript import | Disposable `import x from './missing'`; validator exited `1` and emitted `missing relative import target` | **PASS** |
| Duplicate registry ID | Disposable registry contained duplicate `fixture` IDs; validator exited `1` | **PASS** |
| Missing required documentation/configuration | Disposable repository removed `AGENTS.md` and `package-lock.json`; validator exited `1` with both missing-file classes | **PASS** |
| `--fail-on-review` behavior | Deletion and both rename cases failed strictly; a normal source edit exited `0` with `repository_structure=PASS` | **PASS** |
| Legitimate reviewable change | A source content edit without deletion/rename produced no review failure | **PASS** |

The fixture harness copied the validator into each temporary repository and
created only synthetic files required by its declared contracts. Temporary
repositories were removed after each case.

## Additive validator fix

`scripts/validate_repository_structure.py` was minimally extended to:

1. detect side-effect TypeScript imports such as `import './module'`; and
2. treat a rename as reviewable when either the old or new path is under a
   protected source prefix, including source-to-documentation moves.

The existing advisory mode remains non-blocking and prints `REVIEW_REQUIRED`;
`--fail-on-review` remains the explicit strict gate.

## Current repository validation

Observed locally after the fix:

```text
python scripts/validate_repository_structure.py
required_docs=6/6
registry_paths_checked=58
missing_relative_import_targets=0
missing_required_config=0
source_deletions_for_review=0
source_renames_for_review=0
repository_structure=PASS

python scripts/validate_repository_structure.py --fail-on-review
repository_structure=PASS
```

The worktree contains pre-existing user changes, so the validator reported
`worktree_entries_for_review=75` and `source_entries_for_review=13`; these are
review inventory counts, not deletion or rename failures.

## CI workflow verification

`.github/workflows/ci.yml` was inspected directly.

- Triggers: `push`, `pull_request`, and `workflow_dispatch`.
- Permissions: workflow and jobs use read-only `contents: read`.
- Checkout: pinned full SHA and `persist-credentials: false`.
- Python setup: pinned `actions/setup-python` SHA; Python 3.11–3.14 matrix
  for tests and Python 3.14 for lint/structure validation.
- Structure command: `python scripts/validate_repository_structure.py --fail-on-review`.
- Failure propagation: commands run without `continue-on-error`; non-zero
  validator/test/build/lint results fail their job.
- Safety: the CI workflow has no deployment step, write token, secret
  reference, database target, or production service call. The checked-out
  repository is therefore not granted a path to modify the production
  repository through this job.
- Job boundaries: Python tests, Python lint, web build, and structure
  validation are separate bounded jobs with timeouts and cancellation
  concurrency.

The workflow definition is locally verified. A GitHub-hosted run status was
not available in this unauthenticated session.

## Language and contract limitations

The validator does not provide complete compiler or runtime verification:

- Relative import checks cover `.ts` and `.tsx` files under `src/` only.
- JavaScript/JSX, Python, Kotlin, SQL, CSS/assets, package aliases,
  `tsconfig` path mappings, non-relative imports, and dynamic/runtime loading
  are not resolved.
- Registry checks verify JSON shape, duplicate IDs, and referenced path
  existence; they do not prove implementation behavior or test quality.
- Required-document/config checks verify presence, not content completeness.
- Source deletion/rename review is prefix-based and Git-diff-based; it is not
  a semantic dependency or feature-loss detector.
- The validator does not replace human review, CI, branch protection, CodeQL,
  dependency review, staging tests, or production checks.

**Phase 21 conclusion:** local protection behavior and strict enforcement are
verified for the declared contracts. Coverage is intentionally partial for
languages and runtime behavior, and those limitations are recorded rather
than presented as complete protection.
