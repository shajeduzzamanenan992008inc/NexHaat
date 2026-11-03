# CI Failure Remediation — Phase 2 Minimal Safe Fixes

**Date:** 2026-11-03
**Branch / baseline HEAD:** `main` / `cc0f7fc48d19d38066dcc8b644daa7242bf9ef02`
**Evidence source:** [`CI_FAILURE_PHASE1_EVIDENCE.md`](CI_FAILURE_PHASE1_EVIDENCE.md)
**Scope:** Three narrow fixes. No feature, dependency, workflow, migration, or
authentication behaviour was changed.

## Summary of changes

| # | File | Change | Failure addressed |
|---|---|---|---|
| 1 | `package-lock.json` *(new, tracked)* | Complete npm lockfile generated from the unchanged `package.json` | Structure validation + `actions/setup-node` cache + `npm ci` |
| 2 | `scripts/validate_repository_structure.py` | Missing **pair** check replaced with real manifest↔lockfile **contract** validation | Structure validation (kept meaningful, not removed) |
| 3 | `app/api/routes/auth.py` | One import line moved inside the third-party import block | Ruff `I001` |

`.github/workflows/ci.yml` was **not** modified. Its assumptions (`cache: npm`,
`cache-dependency-path: package-lock.json`, `npm ci`) were already correct for
npm; they only needed the file they reference to exist.

## 1. Lockfile (`package-lock.json`)

### Decision: regenerate, do not restore

Phase 1 established that the last committed lockfile (`a46ca25:package-lock.json`)
contains 619 package nodes with **zero** `resolved` URLs and **zero** `integrity`
hashes. Restoring it would have satisfied the presence check while leaving
`npm ci` without the tamper-evident data a lockfile exists to provide — a fake
lockfile, explicitly forbidden by the zero-loss rules.

`npm install --package-lock-only` was also rejected: it resolves a graph without
ever installing it, so a resolution defect would not surface until CI. The
lockfile was instead produced by a real `npm install` against the reachable
public registry (`npm ping` → `PONG 441ms`), which both resolves and materialises
the tree.

### What was run

```
npm install --no-audit --no-fund
→ added 667 packages in 4m   (exit 0)
```

`--no-audit`/`--no-fund` suppress network advisory and funding chatter only; they
do not alter resolution, the dependency graph, or the written lockfile. No
`--legacy-peer-deps`, `--force`, or `--package-lock-only` flag was used.

### Result

| Property | Value |
|---|---|
| `lockfileVersion` | 3 (npm 10 compatible — the format Node 22 in CI reads) |
| Root `name`/`version` | `nexhaat-marketplace` / `1.0.0` — matches `package.json` |
| Package nodes | 743 |
| Nodes with `resolved` | **743 / 743** |
| Nodes with `integrity` | **743 / 743** |
| Declared dependencies locked | 25 / 25 |
| Lock root dependency map vs `package.json` | Identical |
| `git diff --stat -- package.json` | empty — manifest untouched |

### Why this is safe

- `package.json` is byte-identical to before the fix: no dependency was added,
  removed, upgraded, or downgraded at the declaration level, and no version
  range was edited. The 25 declared ranges still describe exactly what the
  project asks for.
- Resolved versions satisfy the existing caret ranges (for example
  `vite@6.4.5` for `^6.1.0`, `typescript@5.9.3` for `^5.7.3`,
  `tailwind-merge@3.7.0` for `^3.0.1`). Pinning currently-satisfying versions is
  what a lockfile is for; it does not change the contract.
- The lockfile is additive: it is a new tracked file, not a replacement of
  anything, and `node_modules/`, `dist/`, and unrelated build output remain
  ignored.
- Reproducibility is restored rather than relaxed: CI moves from "cannot install"
  to `npm ci`, which installs the exact locked graph and fails on any drift
  between `package.json` and the lockfile.
- Nothing was pinned to a private registry or local path; all 743 entries resolve
  to the public npm registry with integrity hashes.

## 2. Structure validator (`scripts/validate_repository_structure.py`)

### The problem with both obvious options

- Leaving it as-is keeps CI red forever.
- Deleting `package-lock.json` from `REQUIRED_CONFIG` would remove a genuine
  protection that caught a real regression, and is explicitly disallowed.

### What was implemented instead

`REQUIRED_CONFIG` still lists **both** `package.json` and `package-lock.json`, so
a missing lockfile remains a hard failure. On top of presence, a new
`validate_node_dependency_lock()` enforces the npm contract that the CI job
actually depends on:

| Assertion | Failure message |
|---|---|
| No competing lockfile (`yarn.lock`, `pnpm-lock.yaml`, `bun.lock`, `bun.lockb`, `npm-shrinkwrap.json`) | `conflicting Node lockfile <name>: npm with package-lock.json is the authoritative package-management contract` |
| `package.json` and `package-lock.json` parse as JSON objects | `<file> unreadable: ...` / `<file> must contain a JSON object` |
| `lockfileVersion >= 2` (the `packages` format `npm ci` needs) | `package-lock.json must declare lockfileVersion >= 2 ...` |
| Lockfile has a root `packages[""]` entry | `package-lock.json has no root packages entry; npm ci cannot install it` |
| Lock root `name`/`version` match the manifest | `package-lock.json root <field> is out of sync with package.json ...` |
| Every declared dependency/devDependency appears with the same specifier | `package-lock.json <section> does not match package.json for <name>` |
| Every declared dependency has a locked `node_modules/<name>` entry | `package-lock.json has no locked entry for declared dependency <name>` |
| Every non-link entry has a `resolved` URL | `package-lock.json has N entries without a resolved URL (first: ...)` |
| Every registry entry has an `integrity` hash | `package-lock.json has N entries without an integrity hash (first: ...)` |

New machine-readable output lines (existing lines unchanged in name and order):

```
node_manifest_dependencies_declared=25
node_lockfile_packages=743
node_lockfile_entries_without_resolved_integrity=0
```

### Why this is safe

- Strictly **stronger** than the previous check: every condition that failed
  before still fails, and the "lockfile exists but cannot reproduce the
  dependency graph" class — the exact defect found in the historical file — now
  fails too. A stale lockfile after a future dependency edit will now be caught
  locally instead of only in CI.
- Implemented with the standard library only (`json`), consistent with the
  script's existing dependency-free design.
- No CLI flag, exit-code contract, or existing output line changed:
  `--base` and `--fail-on-review` behave identically, and success still prints
  `repository_structure=PASS` and returns `0`.
- Registry entries reached through `git`/`file:` are exempt from the integrity
  requirement, so a future intentional non-registry dependency is not rejected
  for a legitimate reason.
- No check was weakened, disabled, or made conditional on the environment.

## 3. Ruff import ordering (`app/api/routes/auth.py`)

### Change (single line moved)

```diff
 from flask import Blueprint, current_app, request, session
-from werkzeug.security import generate_password_hash
 from flask_login import logout_user
 from flask_wtf.csrf import generate_csrf
 from sqlalchemy import select
+from werkzeug.security import generate_password_hash
```

`werkzeug` now sorts correctly after `sqlalchemy` within the third-party block,
which is exactly the fix Ruff proposed (`I001`).

### Why this is safe

- The same eight imported names are imported from the same modules; nothing was
  added, removed, or renamed, and no alias, `noqa`, or suppression was used.
- Nothing at all changed below the import block: `csrf_token`, `register`,
  `verify_registration`, `login`, `logout`, `me`, `request_admin_code`,
  `verify_admin_code`, `forgot_password`, `reset_password`, `social_login`,
  `setup_2fa`, and `verify_2fa` are byte-identical. Session handling, CSRF
  token generation, OTP expiry/attempt limits, login throttling, audit
  recording, password hashing, and role checks were not touched.
- Import order has no runtime effect for these modules, and `ruff --fix` was not
  used to rewrite anything else — only the reported violation was corrected, so
  no formatting churn leaked into the file.

## Explicitly not changed

| Area | State |
|---|---|
| `package.json` dependencies, versions, scripts | Byte-identical |
| `.github/workflows/ci.yml` and all other workflows | Unmodified (correct as written) |
| Python runtime/test dependencies, `pyproject.toml` | Unmodified |
| Flask routes, services, models, migrations | Unmodified |
| Authentication, session, CSRF, OTP, throttle logic | Unmodified |
| React/TypeScript/Vite/Express sources, Firebase, Android | Unmodified |
| Repository validator: docs, registry, import-target, boundary, deletion/rename checks | All retained |

## Files changed in Phase 2

- `package-lock.json` — new tracked lockfile (743 nodes, all with integrity).
- `scripts/validate_repository_structure.py` — manifest↔lockfile pair validation.
- `app/api/routes/auth.py` — one import moved (Ruff `I001`).
- `docs/architecture/CI_FAILURE_PHASE1_EVIDENCE.md` — Phase 1 deliverable.
- `docs/architecture/CI_FAILURE_PHASE2_REMEDIATION.md` — this report.

Verification results for these changes are recorded in
[`CI_FAILURE_PHASE3_VERIFICATION.md`](CI_FAILURE_PHASE3_VERIFICATION.md).
