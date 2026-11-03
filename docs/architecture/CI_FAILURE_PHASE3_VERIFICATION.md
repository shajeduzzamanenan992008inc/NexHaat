# CI Failure Verification — Phase 3 Results

**Date:** 2026-11-03
**Branch / HEAD:** `main` / `cc0f7fc48d19d38066dcc8b644daa7242bf9ef02`
**Environment:** Windows x64, Node `v26.13.0` / npm `11.20.0`, Python `3.15.2`, Ruff `0.17.1`
**Related:** [Phase 1 evidence](CI_FAILURE_PHASE1_EVIDENCE.md) · [Phase 2 remediation](CI_FAILURE_PHASE2_REMEDIATION.md)

## Verification matrix

| # | Check | Command | Status | Observed result |
|---|---|---|---|---|
| 1 | Repository structure validation | `python scripts/validate_repository_structure.py --fail-on-review` | **PASS** | `repository_structure=PASS`, exit `0`; `missing_required_config=0`; `node_manifest_dependencies_declared=25`; `node_lockfile_packages=743`; `node_lockfile_entries_without_resolved_integrity=0` |
| 2 | Python lint | `python -m ruff check .` | **PASS** | `All checks passed!`, exit `0` |
| 3 | npm lockfile consistency | `npm ci` from a removed `node_modules`; lockfile/JSON inspection | **PASS** | `npm ci` exit `0`; `lockfileVersion=3`; 743/743 nodes with `resolved` **and** `integrity`; lock root dependency map identical to `package.json`; 25/25 declared dependencies locked |
| 4 | Clean npm dependency installation | `rm -rf node_modules && npm ci --no-audit --no-fund` | **PASS** | Exit `0` with no `EUSAGE`/lockfile error; `npm ls --depth=0` resolved the full top-level tree (`vite@6.4.5`, `typescript@5.9.3`, `tailwind-merge@3.7.0`, `ws@8.22.1`, …) |
| 5 | React/Express lint and type checks | `npm run lint` (`tsc --noEmit`) | **PASS** | Exit `0`, no diagnostics. CI also invokes `npm run typecheck --if-present`; no `typecheck` script is defined, so `tsc --noEmit` is the effective type check |
| 6 | Frontend build | `npm run build` (`tsc && vite build`) | **PASS** | `✓ built in 33.39s`, exit `0`; PWA `generateSW` emitted 43 precache entries. Pre-existing non-fatal warning: some chunks > 500 kB (recorded in earlier phase reports, not introduced here) |
| 7 | Existing Node tests | `npm test` (`node --import tsx --test tests-node/server-security.test.ts`) | **PASS** | `tests 8`, `pass 8`, `fail 0`, exit `0` |
| 8 | Python test suite | `python -m pytest -q` | **PASS** | `306 passed in 382.13s (0:06:22)`, exit `0` |
| 9 | Whitespace / conflict check | `git diff --check` | **PASS** | No output, exit `0` |
| 10 | No unexpected file changes | `git status --short`, `git check-ignore` | **PASS** | Exactly the intended paths changed; `node_modules/` and `dist/` remain ignored (`.gitignore:53 dist/`) |

All ten checks pass. No check was skipped, weakened, or suppressed to obtain a pass.

## Notes on individual results

### Structure validation (1)

Before remediation the same command reported
`missing_required_config=1` / `- missing required configuration: package-lock.json`
and exit `1`. After the fix it reports `missing_required_config=0` and still runs
every pre-existing check: 6/6 required docs, 190 registry paths, 0 direct
marketplace paths outside adapters, 0 missing relative import targets, 0 source
deletions/renames. The new pair-validation counters are additive output.

`worktree_entries_for_review` / `source_entries_for_review` count the intended
edits themselves (validator, `auth.py`, lockfile, phase documents) and are
informational only — the validator does not fail on modified or untracked files,
only on deletions/renames of source paths.

### Lockfile and installation (3, 4)

`npm ci` is the decisive check: it refuses to run when
`package.json` and `package-lock.json` disagree and installs only the locked
graph, so a successful run from a deleted `node_modules` demonstrates both
consistency and reproducibility. npm also emits a non-fatal
`install-scripts … not yet covered by allowScripts` notice for
`esbuild`, `protobufjs`, `@google/genai`, and `@firebase/util`; the optional
platform binaries these packages depend on are present from the registry, and
both `tsc` and `vite build` succeeded, so the notice has no functional effect
here.

### Python suite (8)

The suite reports **306** passed, while earlier phase reports record **305** for
the same repository code. The difference is not attributable to these changes:
no Python test, fixture, or application source other than an import line in
`app/api/routes/auth.py` was modified, and that line cannot add a test. The most
likely cause is environment-dependent collection (this run used CPython `3.15.2`,
whereas the recorded 305-pass runs used `3.11–3.14.7`). This is recorded as an
observed discrepancy, not explained away. Either count is a clean pass with exit
`0` and zero failures.

## Checks not run / out of scope

| Check | Status | Reason |
|---|---|---|
| Remote GitHub Actions run on the fixed commit | **NOT TESTED** | Out of scope by instruction; requires commit + push + run, which is forbidden here |
| `npm ci` under Node 22 (CI's runtime) | **NOT TESTED** | Only Node `26.13.0` / npm `11.20.0` is installed locally. The lockfile is `lockfileVersion: 3`, the format npm 10 ships with Node 22, but format compatibility is reasoning, not an executed test |
| Python 3.11, 3.12, 3.13 matrix runs | **NOT TESTED** | Only CPython `3.15.2` available locally; no Python source logic changed except import order |
| Ruff `0.17.0` (CI's exact pin) | **PARTIAL** | Verified with the installed `0.17.1`; the `I001` ordering rule result is unchanged between these patch versions |
| Android unit tests, Gradle build | **NOT RUN** | No Android or Gradle file was touched by this remediation |
| Workflow YAML parse / `actionlint` | **NOT TESTED** | No workflow file was modified, so no new YAML was introduced |
| Live Azure / deployment behavior | **NOT TESTED** | No deployment or production action was authorized or performed |

## Files changed (total remediation footprint)

| File | Nature |
|---|---|
| `package-lock.json` | New tracked lockfile — 10,837 lines, 743 nodes, all with `resolved` + `integrity` |
| `scripts/validate_repository_structure.py` | Added manifest↔lockfile pair validation (existing checks retained) |
| `app/api/routes/auth.py` | One import moved (`werkzeug` after `sqlalchemy`) |
| `docs/architecture/CI_FAILURE_PHASE1_EVIDENCE.md` | New — Phase 1 deliverable |
| `docs/architecture/CI_FAILURE_PHASE2_REMEDIATION.md` | New — Phase 2 deliverable |
| `docs/architecture/CI_FAILURE_PHASE3_VERIFICATION.md` | New — this report |
| `docs/plans/nexhaat-master-plan.md` | One dated `Stage history` row appended |

`package.json`, `.github/workflows/ci.yml`, all other workflows, all Python
dependencies, all application logic, React/Express sources, Android sources, and
Firebase configuration are unchanged.

## Expected CI outcome (prediction, not a verified result)

| Job | Previously failing step | Expected after this fix |
|---|---|---|
| `structure-validation` | `missing required configuration: package-lock.json` | Passes — file exists and the pair contract validates locally |
| `lint` | Ruff `I001` in `app/api/routes/auth.py` | Passes — `ruff check .` clean locally |
| `web-build` | `setup-node` cache resolution, then `npm ci` | Passes — cache key file exists and `npm ci` verified locally |

These remain **predictions**. The only authoritative confirmation is a CI run on
a commit containing these changes, which requires authorization not yet given.

## Git state at end of Phase 3

- Branch `main`, HEAD `cc0f7fc48d19d38066dcc8b644daa7242bf9ef02` — unchanged.
- All changes are present only in the working tree (modified + untracked).
- **No commit, push, merge, deployment, restart, or production mutation occurred.**
