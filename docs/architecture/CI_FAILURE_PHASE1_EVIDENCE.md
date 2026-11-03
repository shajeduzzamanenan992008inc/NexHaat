# CI Failure Investigation — Phase 1 Baseline and Evidence

**Date:** 2026-11-03
**Repository:** `D:\FTP\NexHaat`
**Branch / HEAD:** `main` / `cc0f7fc48d19d38066dcc8b644daa7242bf9ef02`
**Scope:** Evidence-only inspection. No file was edited in Phase 1.

## 1. Git baseline

| Check | Command | Observed |
|---|---|---|
| Branch | `git rev-parse --abbrev-ref HEAD` | `main` |
| HEAD | `git rev-parse HEAD` | `cc0f7fc48d19d38066dcc8b644daa7242bf9ef02` (matches the reported failing commit) |
| Worktree | `git status --short --branch` | `## main...origin/main`, no modified/staged/untracked entries |
| Ignored entries | `git status --short --ignored` | `.freebuff/` only |

The worktree was clean, so nothing of the user's local work had to be stashed,
merged, or discarded. No reset, clean, checkout-over, or restore command was
used at any point.

## 2. Node package-manager inventory

| Artifact | State at HEAD |
|---|---|
| `package.json` | Present. `name: nexhaat-marketplace`, `version: 1.0.0`, `type: module`, 11 `dependencies` + 14 `devDependencies` (25 declared, all caret ranges) |
| `package-lock.json` | **Absent** (deleted before HEAD — see §3) |
| `npm-shrinkwrap.json` | Absent |
| `yarn.lock` | Absent |
| `pnpm-lock.yaml` | Absent |
| `bun.lock` / `bun.lockb` | Absent (deleted in the same commit as the npm lockfile) |
| `.npmrc` | Absent — no registry override, no `package-lock=false`, no `legacy-peer-deps` |
| Nested lockfiles | None; `glob` over `**/package-lock.json`, `**/yarn.lock`, `**/pnpm-lock.yaml` returned zero matches |

`git check-ignore -v package-lock.json` reported **NOT IGNORED**: the lockfile is
a trackable file by policy, not an intentionally untracked artifact.

## 3. When the lockfile disappeared, and what it contained

```
$ git log --oneline --all -- package-lock.json
2b11a2c Update
a46ca25 Update
27df586 Updated a file
959aa49 Agent host session ... - turn 9
```

`git show --name-status 2b11a2c` reports:

```
D	package-lock.json
D	bun.lock
```

Commit `2b11a2c` ("Update", 2026-11-02) deleted **both** lockfiles while adding
feature code (`src/lib/priceIntelligence.ts`, `src/components/PriceTrendChart.tsx`,
`index.html`, `server.ts` changes). The deletion was collateral to a feature
commit, not a deliberate package-manager migration: no `.npmrc`, `bunfig.toml`,
`pnpm-workspace.yaml`, or `"packageManager"` field was added, and no documentation
was updated to name a different tool.

`git diff a46ca25 HEAD -- package.json` produced **no output**: the manifest is
byte-identical to the revision that still had a lockfile, so the manifest never
demanded a different dependency set.

### The historical lockfile is not a valid restoration source

The last committed lockfile (`a46ca25:package-lock.json`) was inspected:

| Property | Value |
|---|---|
| `lockfileVersion` | 3 |
| Root name/version | `nexhaat-marketplace` / `1.0.0` (matches manifest) |
| Root dependency map vs manifest | Identical (25/25) |
| Locked package nodes | 619 |
| Nodes with `resolved` | **0** |
| Nodes with `integrity` | **0** |

That file carries no registry URLs and no integrity hashes for any of its 619
packages. Restoring it would satisfy a presence check while leaving `npm ci`
without the tamper-evident data it requires — i.e. a fake, non-reproducible
lockfile. It was therefore rejected as a fix and is recorded as historical
evidence only.

## 4. Intended package manager: npm

Confirmed by convergent, independent evidence:

| Source | Evidence |
|---|---|
| `.github/workflows/ci.yml` (`web-build`) | `cache: npm`, `cache-dependency-path: package-lock.json`, `run: npm ci` |
| `.github/dependabot.yml` | `package-ecosystem: "npm"`, `directory: "/"`, comment: "npm uses `npm ci` at repository root" |
| `README.md` | `package-lock.json` listed in the Node app tree (line 721); "Use `npm ci` for repeatable installation from `package-lock.json`" (line 911) |
| `AGENTS.md` | Frontend verification entry point: "`npm ci` then `npm run build`" (line 286); lockfiles must be preserved (line 309) |
| `docs/architecture/DEVELOPMENT_CONVENTIONS.md` | Baseline gate `npm run lint` / `npm run build` |
| `.github/copilot-instructions.md` | "`npm ci` requires a compatible lockfile" |

No document, workflow, or configuration in the repository names yarn, pnpm, or
bun as authoritative. npm + `package-lock.json` is the approved contract.

## 5. Exact failure mechanisms

### 5.1 Repository structure validation

`scripts/validate_repository_structure.py`:

```python
REQUIRED_CONFIG = (
    ROOT / "package.json",
    ROOT / "package-lock.json",
    ...
)

def validate_required_config(failures: list[str]) -> int:
    for path in REQUIRED_CONFIG:
        if not path.exists():
            failures.append(f"missing required configuration: {path.relative_to(ROOT)}")
```

Reproduced locally before any edit:

```
missing_required_config=1
FAILURES:
- missing required configuration: package-lock.json
exit=1
```

Root cause: the lockfile deleted by `2b11a2c` was never regenerated, so the
validator's (correct) contract check failed. The validator was not wrong to
require it; the repository had genuinely lost a required file.

### 5.2 Python lint (Ruff)

Configuration in `pyproject.toml`: `select = [... "I" ...]` (isort ordering),
`line-length = 120`, `target-version = "py311"`. CI installs `ruff==0.17.0`.

Reproduced locally before any edit:

```
$ python -m ruff check .
Found 1 error.
help: Organize imports
9  | from flask import Blueprint, current_app, request, session
   - from werkzeug.security import generate_password_hash
10 | from flask_login import logout_user
11 | from flask_wtf.csrf import generate_csrf
12 | from sqlalchemy import select
13 + from werkzeug.security import generate_password_hash
```

`app/api/routes/auth.py` declared `werkzeug` (third-party group) before
`flask_login`, `flask_wtf`, and `sqlalchemy`. `I001` is purely ordering: the
imported names, the import set, and the runtime behaviour are unaffected.

### 5.3 React and Express checks

`.github/workflows/ci.yml`:

```yaml
- name: Set up Node.js
  uses: actions/setup-node@... # v7.1.0
  with:
    node-version: "22"
    cache: npm
    cache-dependency-path: package-lock.json

- name: Install locked Node dependencies
  run: npm ci
```

With no `package-lock.json` present, `actions/setup-node` cannot resolve the
cache key and fails before any install, and `npm ci` would fail by design
("requires an existing lock file"). One absent file explains both symptoms of
this job.

## 6. Findings classification

| Finding | Classification |
|---|---|
| `package-lock.json` absent from HEAD | **Confirmed** (file system + git history) |
| Deletion introduced by `2b11a2c` alongside `bun.lock` | **Confirmed** (`git show --name-status`) |
| Historical lockfile lacks `resolved`/`integrity` for all 619 nodes | **Confirmed** (JSON inspection) |
| npm is the authoritative package manager | **Confirmed** (workflow + docs + dependabot agreement) |
| `package.json` unchanged since the lockfile existed | **Confirmed** (empty `git diff`) |
| Ruff `I001` in `app/api/routes/auth.py` | **Confirmed** (reproduced, exit 1) |
| Validator fails solely on the missing lockfile | **Confirmed** (reproduced, exit 1) |
| Registry reachability needed to generate a real lockfile | **Confirmed** — `npm ping` → `PONG 441ms` |
| CI's actual remote run logs | **Unknown / not accessed** — no CI log fetch was attempted; the three failures are taken as given and each was independently reproduced locally |

## 7. Environment used for local evidence

| Tool | Local version | CI target |
|---|---|---|
| Node.js | `v26.13.0` | `22` |
| npm | `11.20.0` | bundled with Node 22 (npm 10.x) |
| Python | `3.15.2` (Windows x64) | `3.11`–`3.14` matrix; `3.14` for lint/structure |
| Ruff | `0.17.1` (installed) | pinned `0.17.0` |

Lockfile-format compatibility: npm writes `lockfileVersion: 3`, which is the
format npm 10 (Node 22) reads and writes, so the generated lockfile is valid for
the CI runner despite the newer local npm. This is format-level reasoning; the
lockfile has **not** been exercised on Node 22 itself (see Phase 3 limitations).

## 8. Phase 1 conclusion

The three failures are not three independent defects. Two of them share a single
root cause — a lockfile deleted by a feature commit and never regenerated — and
the third is a one-line import-ordering regression in a file that was edited
after that ordering had been established. No security control, dependency
declaration, workflow permission, or application behaviour is implicated.

Phase 1 made no repository changes other than adding this report.
