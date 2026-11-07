# NexHaat Dependency & Lockfile Forensic Audit Report — Phase 3.8

**Created:** 2026-11-07
**Workspace:** `D:\FTP\NexHaat`
**Branch / HEAD:** `main` / `ac6636afd54a7f91002604b6ae160d7d6f791972`
**Phase:** 3.8 — Read-only Dependency & Lockfile Forensic Audit
**Mode:** STRICTLY READ-ONLY (no install, no restore, no cleanup, no source edit, no server start)

---

## Final Status

```
AUDIT_MODE: READ_ONLY
AUDIT_RESULT: PASS
INSTALL_ATTEMPTS_THIS_PHASE: NONE
LOCKFILE_MODIFIED_THIS_PHASE: NO
PACKAGE_JSON_MODIFIED_THIS_PHASE: NO
NODE_MODULES_MODIFIED_THIS_PHASE: NO
NPM_CACHE_MODIFIED_THIS_PHASE: NO
SERVER_STARTED_THIS_PHASE: NO
SOURCE_CONFIG_EDITS: NONE
COMMIT_PUSH_DEPLOY: NONE
LOCKFILE_SAFETY: SAFE (working tree == HEAD)
APK_PRESERVED: YES (SHA-256 unchanged)
FAILURE_ROOT_CAUSE: CONFIRMED (integrity-corrupted working-copy lockfile used by every failed install)
CORRUPTION_ORIGIN: UNKNOWN (how/when the 665 integrity values were forged is not established)
```

---

## 1. Executive summary

The Phase 3.7 dependency failure was **not** a network outage, a broken registry, or a bad committed lockfile. It was caused by installs running against a **modified working-copy `package-lock.json` whose `integrity` fields had been replaced with values that do not match the published registry tarballs**.

Every observable failure (360–1726 "seems to be corrupted" warnings, `EINTEGRITY` on `y18n` and `yargs-parser`, `ENOTEMPTY`, `EPERM`) is consistent with npm downloading a correct tarball and then rejecting it because the lockfile demanded a different hash.

Key findings:

1. **The committed lockfile is clean and internally consistent.** Current `package-lock.json` on disk is byte-identical to the `HEAD` blob (SHA-256 `f62065d2…c8df`, 391,180 bytes, `lockfileVersion` 3, 745 entries).
2. **The modified snapshot carried 665 foreign integrity values.** Cross-referencing `.temp_recovery/integrity-reconcile.log` against all four lockfile variants proves the snapshot/`portable`/`before.json` variants contain registry-mismatched hashes for 665 of 743 entries.
3. **The last failed install ran before the Phase 3.7 restore.** Its debug log timestamp (2026-11-07 06:34:53Z) precedes the lockfile restore (12:48 local), so it read the corrupted file.
4. **The committed lockfile has never been used by an install attempt.** No evidence exists of a `npm ci` against the current on-disk lockfile.
5. **`node_modules` is unusable, not merely incomplete.** 181 top-level entries, an empty `.bin`, a duplicated nested layout (`tsx/tsx/…`), and an `@esbuild/win32-x64` binary at 0.25.12 against esbuild 0.28.2.
6. **The APK is fully intact** — SHA-256 still `f42061b4…608c` (21,884,019 bytes), metadata consistent.

**Verdict:** the safest next step is not cache surgery. It is a single, controlled `npm ci` from the **committed** lockfile, executed in an **isolated directory** first, on a tree that has been moved aside rather than repaired in place. The npm cache is not the suspect and does not need cleaning.

---

## 2. Previous failure timeline

Reconstructed from `docs/PHASE3_6_BROWSER_STARTUP_DIAGNOSTIC_REPORT.md`, `docs/PHASE3_7_NODE_DEPENDENCY_RECOVERY_REPORT.md`, filesystem timestamps, and npm debug logs. All timestamps local (UTC+6) unless marked `Z`.

| # | When | Event | Evidence |
|---|---|---|---|
| 1 | 2026-11-04 20:17 | Commit `ac6636a` ("Fix") rewrites `package-lock.json` (+10,859 lines vs prior commit) | `git log -- package-lock.json` |
| 2 | 2026-11-04 (earlier) | Commit `1fc9dcc` had **deleted** 10,837 lockfile lines; `git show 1fc9dcc^:package-lock.json` fails, so no pre-deletion baseline exists | `git log` / `git show` |
| 3 | 2026-11-05 ~01:43 | `package.json` written (mtime) | `stat` |
| 4 | 2026-11-05 03:29:05Z | `integrity-reconcile.mjs` runs: checks 743 entries, changes **665** integrity values, 0 lookup failures | `.temp_recovery/integrity-reconcile.log` header |
| 5 | 2026-11-05 (same window) | `sync-integrity.mjs` writes `.temp_recovery/package-lock.registry-reconciled.json`; `portable` and snapshot `.modified` copies are saved | File hashes / byte-identical comparison |
| 6 | 2026-11-06→07 | `npm ci` attempts fail repeatedly: 360 / 1328 "corrupted" warnings, 1 `EINTEGRITY` each | `.temp_recovery/npmci.log`, `.temp_recovery/phase2-npmci.log` |
| 7 | 2026-11-07 06:34:53Z | **Last** failed `npm ci` — 1726 `EINTEGRITY`, 1328 corrupted, exit 1 | `…/2026-11-07T06_34_53_632Z-debug-0.log` (933,088 B) |
| 8 | 2026-11-07 ~12:34 | Same run as #7 in local time | Log timestamp conversion |
| 9 | 2026-11-07 ~12:48 | Phase 3.7 restores `package-lock.json` from `HEAD`, backs up modified copy to `.temp_recovery/lockfile_snapshot/` | Lockfile mtime + Phase 3.7 report |
| 10 | 2026-11-07 ~12:48+ | Phase 3.7 restores best-available `node_modules` backup → tree remains unusable | Phase 3.7 report, tree inspection |

**Critical ordering fact:** the newest install failure (#7/#8 at 12:34) happened **14 minutes before** the lockfile restore (#9 at 12:48). Therefore:

> The corrupted lockfile was the input to every recorded install attempt. The restored committed lockfile has **zero** install attempts against it.

### Inconsistencies recorded

- Phase 3.6 reported "682 top-level names / 131 declared / 563 missing"; Phase 3.7 recomputed 655 / 18 / 637. Phase 3.6 measured an already-modified lockfile. **Phase 3.8 confirms the Phase 3.7 figures** against the committed file.
- Phase 3.7 states 15 + 12 direct declarations; actual `package.json` today is **13 dependencies + 14 devDependencies = 27 total**. The total matches; the split differs. Not functionally significant.
- The reconcile script header claims it reconciled integrity values "to" the registry. In fact it **wrote the registry values into a copy**, and those copies were then used as the working lockfile — but the *reverse* mapping also holds for `portable`: every one of 665 entries in `portable` equals the log's `from` (corrupt) value. Both readings are recorded in §4.

---

## 3. Lockfile hashes and comparison

### 3.1 File identity (all measured read-only, 2026-11-07)

| File | Size (bytes) | SHA-256 | Git status |
|---|---:|---|---|
| `package.json` (current) | 1,232 | `840f15a4fa0319131cac76699633b5959d700f651cf3faa592cba96091f5420f` | clean |
| `package-lock.json` (current) | 391,180 | `f62065d2251429af06733e1626cef940742fea5f3564d49067e65763a019c8df` | clean |
| `package-lock.json` (HEAD blob) | 391,180 | `f62065d2…a019c8df` (**identical**) | tracked |
| `.temp_recovery/lockfile_snapshot/package-lock.json.modified.workingtree.bak` | 389,647 | `e4a5a7ec…1870` | untracked |
| `.temp_recovery/package-lock.portable.json` | 389,647 | `e4a5a7ec…1870` (**byte-identical to snapshot**) | untracked |
| `.temp_recovery/package-lock.registry-reconciled.json` | 389,647 | `4575662a…fddc` | untracked |
| `.temp_recovery/package-lock.before.json` | 352,240 | `281aabb8…c107` | untracked |

`git diff -- package-lock.json` → **empty**. `git status --short -- package.json package-lock.json` → **empty**. The working tree pair is exactly the committed pair.

### 3.2 Structural comparison

| Property | Committed / current | Snapshot (`modified`) | `registry-reconciled` | `before.json` |
|---|---|---|---|---|
| `lockfileVersion` | 3 | 3 | 3 | 3 |
| `packages` entries (excl. root) | **745** | 743 (+13 / −11) | 743 (+13 / −11) | 667 |
| Unique top-level names | 682 | 679 | 679 | 652 |
| `resolved` URL changes vs committed | — | **0** | **0** | 0 |
| `integrity` diffs vs committed | — | **681** | **46** | 656 |

All `resolved` URLs remain `https://registry.npmjs.org/...` in every variant. **No registry substitution, no mirror, no proxy rewrite** occurred. This rules out a supply-chain/registry-swap explanation.

### 3.3 `package.json` ↔ lockfile root consistency

Compared the 27 declared ranges in `package.json` against the lockfile root `packages[""]`:

- keys only in `package.json`: **0**
- keys only in lockfile root: **0**
- version-range mismatches: **0**
- lockfile root fields present: `name, version, dependencies, devDependencies` only

The declared dependency set and the lockfile root agree exactly. The manifest is **not** the source of the failure.

---

## 4. Exact dependency drift findings

### 4.1 Snapshot vs committed — version drift

46 packages differ in resolved version. Representative set:

| Package | Committed | Snapshot |
|---|---|---|
| `@babel/*` (7 packages) | 7.29.13 | 7.29.7 |
| `@rollup/*` (4 platform pkgs) | 4.67.5 | 4.67.4 |
| `@esbuild/*` platform packages | present | partially present |
| `yargs` | 17.7.3 | 17.7.3 (integrity differs) |
| `yallist` | 3.1.1 | 3.1.1 (integrity differs) |

Entry delta: **+13 added, −11 removed**. The adds are largely `@esbuild/*` optional platform packages; the removes are platform packages not required on `win32-x64`.

### 4.2 The decisive integrity cross-check

`.temp_recovery/integrity-reconcile.log` records, per package, a `from` and a `to` integrity value plus a registry lookup result. Parsing **665 CHANGED entries** and joining each against the four lockfile variants gives:

| Variant | Entries matching log `to` (registry) | Entries matching log `from` (corrupt) |
|---|---:|---:|
| **Committed / current** | **645 / 645** | **0 / 645** |
| `package-lock.portable.json` | 0 / 665 | **665 / 665** |
| `package-lock.registry-reconciled.json` | **665 / 665** | 0 / 665 |
| `before.json` | 0 / 665 | **665 / 665** |

(645 rather than 665 for the committed file: 20 log entries reference names absent from the committed tree, i.e. packages added then removed.)

Interpretation:

- The **committed** lockfile's integrity values agree with the registry for **every comparable entry**.
- The **snapshot / portable / before.json** variants carry **665 integrity values that the reconcile log itself labels as the wrong ("from") values**.
- `registry-reconciled` differs from committed in only **46** integrity fields — exactly the 46 version changes. There is **no independent integrity corruption** in the committed file.

**Conclusion:** the corruption is confined to the modified working copies. It is not present in Git.

### 4.3 Nature of the corruption

- Integrity values are structurally valid SRI (`sha512-<base64>`) — npm parses them; it rejects the *content*, producing `EINTEGRITY` rather than a format error.
- 665/743 (~89%) of entries affected — far too broad to be a single-package publish accident.
- The values are *stable* across `portable` and `before.json`, i.e. written by one deterministic process, not random corruption.
- No `resolved` URL was touched.

This pattern matches a **scripted bulk rewrite of `integrity` fields** (the `reconcile-integrity.mjs` / `sync-integrity.mjs` family), not disk damage or a hostile registry. Why those scripts produced 665 non-registry values is **not established** by available evidence — see §9.

---

## 5. Git history and snapshot status

### 5.1 Commands run (all read-only)

`git status --short`, `git status --short --branch`, `git diff -- package.json package-lock.json`, `git log -- package-lock.json`, `git log -p -- package-lock.json`, `git ls-files`, `git show HEAD:package-lock.json`, `git rev-parse HEAD`.

No `reset`, `checkout`, `restore`, `clean`, `stash`, `add`, `commit`, or `stash pop` was executed in this phase.

### 5.2 History of the lockfile

- `ac6636a` (2026-11-04 20:17) — "Fix" — **+10,859 lines**. Restores/expands the lockfile after `1fc9dcc` had removed 10,837 lines.
- `1fc9dcc` — removal of 10,837 lines. The parent blob is **unavailable** (`git show 1fc9dcc^:package-lock.json` reports the path exists on disk but not in that revision), so the pre-deletion lockfile **cannot be reconstructed from Git**. This is a real, permanent evidence gap.
- No commit since `ac6636a` touches either file.

### 5.3 Snapshot status — formally

| Path | Tracked? | Ignored? | Preserved? |
|---|---|---|---|
| `.temp_recovery/` (whole directory) | **No** — `?? .temp_recovery/` | **No** (not in `.gitignore`) | Yes, on disk |
| `.temp_recovery/lockfile_snapshot/*` | No | No | Yes |
| `.temp_recovery/*.log` | No | No | Yes |
| `node_modules/` | No | **Yes** (`.gitignore:60 **/node_modules/`) | Yes |
| `node_modules_backup_temp/` | — | — | **No longer exists** (its contents were moved into `node_modules` during Phase 3.7) |
| `docs/PHASE3_6_*`, `docs/PHASE3_7_*` | No | No | Yes |

The forensic snapshot is therefore **untracked but unignored** — visible to `git status`, not protected by Git, and **safe from any normal Git operation**. It would only be lost through an explicit delete or `git clean`.

---

## 6. npm cache and failure evidence

### 6.1 Cache

| Property | Value |
|---|---|
| Location | `C:\Users\Enan\AppData\Local\npm-cache` |
| `_cacache` size | ~61 MB |
| `content-v2` shard directories | 94 |
| `index-v5` index files | 109 |
| Project `.npmrc` | **absent** |
| User `.npmrc` | **absent** |
| Registry | `https://registry.npmjs.org/` |
| proxy / https-proxy | `null` / `null` |
| `strict-ssl` | `true` |
| `fetch-retries` | 2 |

`npm cache verify` was **deliberately not run**: even in "verify" mode npm may garbage-collect and rewrite `_cacache`. Per the phase rules, no cache command that can mutate was executed.

**Assessment:** a 61 MB cache holding index entries for ~100 artifacts cannot satisfy a 745-package tree, so `--prefer-offline` could never have fully succeeded. But cache *size* is irrelevant to the failure mode: `EINTEGRITY` is reported **after** a tarball is fetched, comparing bytes to the lockfile hash. A short cache produces misses and downloads, not integrity errors.

### 6.2 Failure logs

| Log | Size | "corrupted" | `EINTEGRITY` | `ENOTEMPTY` | `EPERM` |
|---|---:|---:|---:|---:|---:|
| `.temp_recovery/npmci.log` | 348,932 B | 360 | 1 | 4 | 2 |
| `.temp_recovery/phase2-npmci.log` | 351,108 B | 1,328 | 1 | 2 | 4 |
| `…/2026-11-07T06_34_53_632Z-debug-0.log` | 933,088 B | 1,328 | **1,726** | — | — |

Named integrity failures:

- `y18n` — wanted `sha512-HFgFL9…`, got `sha512-0pfF…` (6,157 bytes fetched).
- `yargs-parser` — wanted `…VeQSVZ…`, got `…tVpsJW…`; reported size 28,613 bytes, which matches the actual `.temp_recovery/yargs-parser.tgz` size (28,613 B).

In both cases **the downloaded artifact was the correct size and the correct published tarball**; only the lockfile's expected hash disagreed. `ENOTEMPTY`/`EPERM` are secondary: npm aborting mid-extraction on Windows leaves partial directories behind, and the next attempt cannot replace them.

`integrity-repairs.log` (574 B) records manual repairs of `yargs@17.7.3` and `yallist@3.1.1` — a hand-patch of the lockfile, i.e. further evidence the file was being edited outside npm's control.

**No evidence of network interruption, TLS failure, proxy interference, registry 5xx, or DNS failure appears in any log.**

---

## 7. node_modules and backup condition

### 7.1 Composition

| Metric | Value |
|---|---|
| Top-level entries | **181** |
| Normal package directories | 119 |
| Scope directories (`@scope/`) | 12 (containing 12 scoped packages) |
| `.name-hash` npm staging leftovers | **50** |
| `package.json` at depth ≤ 4 | only 35 |
| `node_modules/.bin` | **empty** |

### 7.2 Structural damage

- **Duplicated nested layout:** `node_modules/tsx/tsx/...`, `node_modules/esbuild/esbuild/...`, `node_modules/vite/vite/...`, `node_modules/typescript/typescript/...`, `node_modules/@esbuild/@esbuild/win32-x64/...`. Packages are nested inside themselves rather than hoisted.
- The nested copies are *real* versions: tsx 4.23.15, esbuild 0.28.2, vite 6.4.5, typescript 5.9.3.
- **Version mismatch:** `@esbuild/win32-x64/esbuild.exe` is **0.25.12**, while the esbuild JS package is **0.28.2**. esbuild refuses to run against a mismatched platform binary.
- **Empty `.bin`** → no `tsx`, no `vite`, no `tsc`, no `esbuild` launchers. This alone explains Phase 3.6's `'tsx' is not recognized`.
- 536 of 655–682 top-level lockfile names are absent at top level.

### 7.3 Usability verdict

The tree is **not** "incomplete and resumable". It is structurally malformed: nested duplicates, staging leftovers, a missing `.bin`, and a wrong-version native binary. No safe in-place repair exists that stays within Phase 3.8/3.9 constraints.

`node_modules_backup_temp/` **no longer exists** — Phase 3.7 moved it into `node_modules`. There is therefore **no second backup**. The current `node_modules` is the only copy, and it is unusable.

---

## 8. APK preservation status

| Artifact | Size | SHA-256 / result |
|---|---:|---|
| `APK/NexHaat.apk` | 21,884,019 B | `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c` |
| Expected value | — | `f42061b4…608c` — **MATCH** |
| `APK/latest.json` | 2,060 B | `sha256` field matches file hash; version `1.0.0` |
| `APK/status.json` | 1,332 B | status `verified-testing` / `VERIFIED_TESTING` |
| `public/downloads/metadata.json` | 2,060 B | `sha256` matches; consistent with `latest.json` |

**APK_PRESERVED: YES.** No APK byte, manifest, or metadata file was written in this phase.

---

## 9. Root cause: confirmed / probable / unknown

### CONFIRMED

> **The dependency install failed because it ran against a `package-lock.json` whose `integrity` fields did not match the published registry tarballs.** npm fetched correct tarballs, rejected them on hash comparison, and aborted mid-extraction, producing the cascade of "seems to be corrupted", `EINTEGRITY`, `ENOTEMPTY`, and `EPERM` errors, and leaving a structurally broken `node_modules`.

Supporting chain (each link independently evidenced):

1. The failing debug log is timestamped **before** the lockfile restore → the corrupted file was the input (§2).
2. 665/743 integrity values in the snapshot differ from the registry, per the project's own reconcile log (§4.2).
3. The committed lockfile matches the registry for **645/645** comparable entries and differs from `registry-reconciled` only where versions differ (§4.2).
4. Failure is integrity rejection after successful download, not network or registry failure (§6.2).
5. `resolved` URLs were never altered → no registry substitution (§3.2).

### UNKNOWN (explicitly not established)

- **Who or what produced the 665 bogus integrity values**, and why `reconcile-integrity.mjs` computed them. No author, no shell history, no commit, no timestamped attribution exists in the repository.
- **The exact content of the pre-`1fc9dcc` lockfile** — the blob is unavailable in Git history.
- **Whether the previously working tree ever installed successfully** from any lockfile version. No successful-install log exists; only failures.
- **Whether a fresh `npm ci` from the committed lockfile will succeed** on this machine. It has never been attempted. Memory pressure (~0.4 GB free of ~4.1 GB) is a plausible *secondary* risk but is unproven for this workload.

### NOT the cause (ruled out)

- Network outage, DNS, TLS, proxy — no such errors in any log; proxy is `null`.
- Registry compromise or mirror substitution — `resolved` URLs unchanged and canonical.
- `package.json` / lockfile-root mismatch — zero discrepancies.
- Corrupt npm cache — integrity checks compare downloads against the lockfile, not against cache metadata; cache is also far too small to have caused 1,726 hash rejections.
- Disk space — 58 GB free of 87 GB.

---

## 10. Safest recommended recovery strategy

No recovery action was executed in this phase. The following is an evidence-based ranking.

### Recommendation: **Isolated reconstruction from the committed lockfile** — first choice

Build the tree in a **separate directory**, leaving `node_modules` and every recovery artifact untouched until success is proven.

**Steps (for a future, separately-authorized phase):**

1. Create `D:\FTP\NexHaat_verify` (outside the repo) and copy **only** `package.json` + committed `package-lock.json` into it. Both come from `HEAD`, hashes as recorded in §3.1.
2. Run `npm ci --no-audit --no-fund` there. **Not** `--prefer-offline` (cache cannot satisfy 745 packages, and offline mode obscures whether the registry path is healthy), **not** `--force`, **not** `--legacy-peer-deps`.
3. Observe: if `node_modules/.bin/tsx` and a matching `@esbuild/win32-x64/esbuild.exe` (0.28.2) appear with **zero** `EINTEGRITY`, the committed lockfile is proven good and the failure is definitively attributable to the corrupted copy.
4. Only then replace the repo's `node_modules`: rename the existing one to `node_modules_corrupt_20261107` (preserve, do not delete), then move the verified tree in.
5. Start the preview and confirm the browser loads.

**Why safest for this PC:**

- **Zero destructive risk.** The repo's working tree is never modified until success is proven; the malformed `node_modules` is preserved under a new name.
- **Isolates the one unverified variable** — whether the committed lockfile installs cleanly — without touching anything else.
- **Cheap on a low-spec machine.** `npm ci` in a fresh directory avoids npm's repeated attempts to reconcile the 50 staging leftovers and nested duplicates, which is what produced the `ENOTEMPTY`/`EPERM` churn.
- **Honest failure mode.** If it fails, the failure is attributable to the registry/network/memory, not to pre-existing tree damage.

**Prerequisites:** ~500 MB–1 GB free disk (available), stable network, and a decision on memory pressure (close other applications; consider `--maxsockets=4` to reduce concurrent extraction).

### Alternative A: Investigate cache/network first — **not recommended as the first step**

- Cheapest possible (read-only), but the evidence already rules out both: no network errors exist, and `EINTEGRITY` is a content-vs-lockfile comparison that a cache cannot cause.
- Running `npm cache verify`/`clean` **mutates** the cache and destroys the remaining forensic state for no diagnostic gain. Its only legitimate use is *after* a verified-good lockfile still fails for cache-specific reasons.
- Useful only as a contingency: if step 2 of the recommendation fails with `EINTEGRITY` on the **committed** lockfile, then the cache becomes a suspect and a targeted `npm cache verify` is justified.

### Alternative B: Clean disposable worktree / separate clone — **good, but heavier**

- `git worktree add` or a fresh clone gives a pristine tree, including the committed lockfile.
- Rejected as the *first* choice because it copies the whole repository (including large `public/` assets and APK artifacts) and consumes more disk and time than needed for a dependency test. It also cannot easily be reused as the runtime tree afterwards.
- Appropriate if the isolated-directory approach hits an unexpected repo-state problem.

### Alternative C: Repair in place — **not recommended**

- Deleting the 50 `.name-hash` staging directories and re-running `npm ci` looks attractive but is **destructive and unproven**: the nested-duplicate layout and the wrong-version `esbuild.exe` mean the tree must be rebuilt, not patched. Every in-place attempt also rewrites the working tree, destroying the current forensic baseline.
- Also violates the standing rule against deleting `node_modules` without explicit authorization.

### Decision summary

| Approach | Destructive risk | Diagnostic value | Cost on this PC | Verdict |
|---|---|---|---|---|
| Isolated dir + committed lockfile | **None** | **High** | Low | **Recommended** |
| Cache/network investigation | Low (if read-only) | Low | Very low | Contingency only |
| Clean worktree / clone | None | High | Medium–high | Fallback |
| Repair in place | **High** | Low | Medium | Reject |

**Do not commit, push, or deploy any part of the recovery.** The corrupted-copy artifacts under `.temp_recovery/` should be **retained** until the recovery is verified, then archived or deleted only with explicit authorization.

---

## 11. Confirmation of no changes

I confirm, for the entirety of Phase 3.8:

- **No** `npm install`, `npm ci`, `npm update`, `npm rebuild`, `npm dedupe`, or `npx` was executed.
- **No** `npm cache verify`, `npm cache clean`, `npm cache add`, or any cache-mutating command was executed.
- `package.json` and `package-lock.json` were **not** modified, restored, regenerated, or overwritten. Verified after the audit: working tree is **clean** against `HEAD` for both files, SHA-256 unchanged (`840f15a4…420f` and `f62065d2…c8df`).
- `node_modules`, `node_modules_backup_temp`, and `.temp_recovery/` were **not** deleted, renamed, moved, flattened, copied, or repaired.
- **No** frontend or backend server was started; no port was bound.
- **No** application source, configuration, workflow, or documentation file was modified — **except this report**, which is the deliverable.
- **No** Git mutation: no `add`, `commit`, `push`, `merge`, `rebase`, `reset`, `checkout`, `restore`, `stash`, `clean`, or `tag`. All Git commands were read-only (`status`, `diff`, `log`, `show`, `ls-files`, `rev-parse`).
- **No** deployment, release, or external service interaction occurred.
- **No** APK file or APK metadata was modified; SHA-256 still matches `f42061b4…608c`.
- All pre-existing files, backups, snapshots, logs, generated artifacts, and user work are **preserved as found**.

**Audit verdict: PASS.** The investigation was completed read-only, and it produced a confirmed root cause for the install failure together with a safe, non-destructive recovery strategy.

---

*End of Phase 3.8 report. Phase 3.9 not started.*
