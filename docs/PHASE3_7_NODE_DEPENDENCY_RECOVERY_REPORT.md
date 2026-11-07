# NexHaat Node Dependency Recovery Report — Phase 3.7

**Created:** 2026-11-07
**Workspace:** `D:\FTP\NexHaat`
**Phase:** 3.7 — Safe Node Dependency Recovery & Browser Startup
**Mission:** Safely restore existing Node dependencies from the project's lockfile and prepare NexHaat for local browser preview.

---

## Final Status

```
DEPENDENCY_PREFLIGHT: PASS
DEPENDENCY_INSTALL: FAIL
LOCKFILE_PRESERVED: YES  (restored to committed version; modified working copy backed up)
NODE_MODULES: INCOMPLETE
FRONTEND: NOT_STARTED
BACKEND: NOT_STARTED
BROWSER_URL: UNAVAILABLE
APK_PRESERVED: YES
PROJECT_SOURCE_CHANGES: NONE
COMMIT_PUSH_DEPLOY: NONE
```

**Outcome:** Browser preview is BLOCKED. The lockfile was found modified in the working tree and was restored to the committed version. One lockfile-based install attempt (`npm ci`) had already failed in this session with integrity/tarball errors. The best-available partial backup of `node_modules` was restored, but it is incomplete and not runnable. The missing dependency tree cannot be safely completed within the Phase 3.7 constraints (no lockfile modification, no upgrades, no repeated install retries, no `--force`/`--legacy-peer-deps` without justification).

---

## 1. Preflight

### Inspected artifacts
- `package.json` — reviewed. Named package `nexhaat-marketplace`, `type: "module"`. Declares 15 `dependencies` + 12 `devDependencies`.
- `package-lock.json` — reviewed. npm lockfile v3 layout under `packages`.
- Existing `node_modules` — inspected (state below).
- npm `11.20.0`, Node `v26.13.0`.
- Disk and memory below.
- Previous Phase 3.6 diagnostic report reviewed.

### Dependency count reconciliation (against committed lockfile)

| Metric | Value | Notes |
|---|---|---|
| Lockfile total package entries (excl. root) | **745** | `packages` keys minus the root `""` entry |
| Lockfile top-level package names | **655** | Unique top-level `node_modules/<name>` entries |
| `package.json` declared deps (deps+devDeps) | **27** | Direct declarations |
| Lockfile top-level declared deps | **18** | Of the 655 top-level names, 18 are direct declarations present in lockfile |
| Lockfile top-level transitive-only names | **637** | Remaining top-level names are transitive |
| Currently installed top-level dirs (restored backup) | **181** | After restoring best-available backup into `node_modules` |
| Missing top-level dep names (current tree vs committed lockfile) | **536** | Declared+transitive top-level names not present at top level in restored tree |

These numbers correct the Phase 3.6 figures (682 / 131 / 563), which were computed against a different snapshot and an already-modified lockfile.

### Disk and memory

- Disk: ~58 GB available on `D:` (35% used of 87 GB). Sufficient for a lockfile-based install in principle.
- Memory: ~4.1 GB total, ~0.4 GB free at time of inspection. Constrained. This is a real risk factor for a full `npm ci` of 745 packages and likely contributed to earlier partial/failed installs.

### Lockfile/pacakge.json compatibility
- `package.json` and committed `package-lock.json` are compatible npm lockfile v3 pair.
- One attempted installation had already been made earlier in this session (`npm ci --no-audit --no-fund --prefer-offline`) and had failed.

---

## 2. Lockfile protection

### Pre-install recorded hash (Phase 3.7 preflight)
- Working-tree `package-lock.json` SHA-256 (at preflight time): `e4a5a7ec0d0c7bf2721c90dfb579c3a7535aa589684ece806503d33831cc1870`
- `package.json` SHA-256 (preflight, unchanged): `840f15a4fa0319131cac76699633b5959d700f651cf3faa592cba96091f5420f`

### Integrity finding — lockfile was modified in working tree
During preflight reconciliation I discovered that `git status` reported `package-lock.json` as **modified**, and `git diff` showed material changes versus the committed blob (changed `version`/`resolved`/`integrity` values; e.g. `@babel/core` 7.29.7 → 7.29.13). This violates the Phase 3.7 no-upgrade / no-lockfile-modification rule and is inconsistent with the repo's lockfile discipline.

### Action taken (justified, mission-scoped)
1. Snapshotted the modified working copy to `.temp_recovery/lockfile_snapshot/package-lock.json.modified.workingtree.bak` (389,647 bytes) — no data destroyed.
2. Restored the committed `package-lock.json` with `git checkout -- package-lock.json`.
3. Verified post-checkout working file SHA-256 now equals the committed blob SHA-256: `f62065d2251429af06733e1626cef940742fea5f3564d49067e65763a019c8df`.

### Post-restoration lockfile state
- Working-tree `package-lock.json` SHA-256: `f62065d2251429af06733e1626cef940742fea5f3564d49067e65763a019c8df`
- Committed blob SHA-256: `f62065d2251429af06733e1626cef940742fea5f3564d49067e65763a019c8df`
- Match: **YES**
- `git status -- package-lock.json`: clean (no longer modified)

### Note on preflight hash discrepancy
The preflight recorded hash `e4a5a7ec...` was computed against the already-modified working copy at that time, so it matched the preflight "before install" expectation but did **not** match the committed lockfile. The true preserved lockfile is the committed version `f62065d...`. The modified copy is retained only as a non-destructive backup in `.temp_recovery/lockfile_snapshot/` and is not used for any install.

---

## 3. Protect existing dependencies

### Pre-install state of `node_modules`
- Before any action this phase: `node_modules` existed.
- After the earlier failed `npm ci` (this session), the current `node_modules` was damaged: only `firebase` and `@opentelemetry` remained as top-level directories.
- A partial backup `node_modules_backup_temp` existed from an earlier attempt (created via `cp -r` after a `mv` permission failure); it is incomplete.

### Best-available backup inspection
- `node_modules_backup_temp` top-level dirs: **181**.
- Critical package presence in that backup (top-level scan): `vite`, `typescript`, `tsx`, `tailwindcss`, `cors`, `firebase`, `esbuild` present; `express`, `react`, `react-dom`, `@vitejs/plugin-react`, `ws`, `@google/genai`, `@esbuild/win32-x64` **missing**.
- No `.bin` directory existed in the backup at all; no `tsx` executable was present anywhere in the backup tree.
- Package layout in backup was malformed/duplicated namespace form (e.g. `node_modules/tsx/tsx/package.json`, `node_modules/esbuild/esbuild/package.json`), indicating a corrupted/flattened partial tree rather than a usable install.

### Decision
Because the current `node_modules` was effectively destroyed by the earlier failed `npm ci` cleanup, and the backup is more complete (though still incomplete), I restored the backup into `node_modules` as the least-bad recoverable tree, after removing the damaged current tree. This is not a usable install, but it preserves more of the prior partial state than leaving the post-failure tree.

- Removed damaged `node_modules`.
- Renamed/ relocated `node_modules_backup_temp` → `node_modules`.
- Did not delete the backup until a usable tree existed — because a usable tree did **not** result, the backup is now the current `node_modules` (see limitations).

Disk space was sufficient to keep the backup; no deletion of the only recoverable tree was required.

---

## 4. Controlled dependency recovery

### One permitted installation attempt
- Earlier in this session, one `npm ci` attempt was made:
  - Command: `npm ci --no-audit --no-fund --prefer-offline`
  - Observed behavior: many `"tarball data ... seems to be corrupted. Trying again."` warnings, then an `EINTEGRITY` sha512 mismatch failure and `ENOTEMPTY`/`EPERM` cleanup errors.
  - Result: unusable install; critical packages missing afterward; `npm ls` reported errors.
  - This attempt satisfies the "one installation attempt only" rule.

### No further install attempt
I did **not** run another install because:
- The one permitted attempt already failed.
- The modified lockfile issue required restoration before any further install could be considered, and re-running after restoration would be a second install attempt.
- No `--force` / `--legacy-peer-deps` justification is present; lockfile modification is prohibited by the mission.
- The resource-constrained machine (low free RAM) is a genuine risk for a full 745-package install.

---

## 5. Dependency verification

### Resolved / unresolved critical packages (restored backup tree)
| Package | Declared | In committed lockfile | Present in restored tree | Usable |
|---|---|---|---|---|
| express | yes | yes | **missing** | no |
| vite | yes (dev) | yes | present (malformed path) | no |
| typescript | yes (dev) | yes | present (malformed path) | no |
| tsx | yes (dev) | yes | present (`tsx/tsx/...`) | no |
| react | yes | yes | **missing** | no |
| react-dom | yes | yes | **missing** | no |
| @vitejs/plugin-react | yes (dev) | yes | **missing** | no |
| tailwindcss | yes (dev) | yes | present | no (peer/toolchain incomplete) |
| ws | yes | yes | **missing** | no |
| cors | yes | yes | present | no (whole tree incomplete) |
| firebase | yes | yes | present | no (whole tree incomplete) |
| @google/genai | yes | yes | **missing** | no |
| esbuild | yes (transitive) | yes | present (`esbuild/esbuild/...`) | no |
| @esbuild/win32-x64 | required by esbuild | yes | **missing** | no |

Versions observed in restored backup (malformed paths):
- `tsx`: 4.23.15
- `esbuild` package: 0.28.2
- `vite` package: 6.4.5 (note: this is the backup's recorded version, not necessarily the committed lockfile's resolved version)
- `@esbuild/win32-x64` nested under vite in backup: 0.25.12 (version mismatch vs root esbuild 0.28.2 — unusable even where present)

### `.bin` and executables
- No `.bin` directory exists in the restored tree.
- No `tsx` executable exists anywhere in the restored tree.
- Result: `npm run dev` (`tsx server.ts`) cannot run; `node --import tsx` cannot resolve tsx binary/loader correctly from this tree.

### `npm ls`
Not run as a truth oracle this phase because the tree is incomplete by construction; `npm ls` would be expected to report errors/missing. The dependency tree is not in a state that can pass verification.

### esbuild platform package version match
- Root esbuild package (where present in backup) reports 0.28.2.
- The only `@esbuild/win32-x64` present in the backup is nested under vite at 0.25.12 — a mismatch. The matching 0.28.2 binary is **absent**.
- Conclusion: esbuild cannot run from this tree.

### Lockfile hash after all actions
- Working `package-lock.json` SHA-256: `f62065d2251429af06733e1626cef940742fea5f3564d49067e65763a019c8df`
- Committed blob SHA-256: same.
- `package.json` unchanged from preflight.
- Lockfile preserved (restored to committed content); modified working copy backed up but not used.

---

## 6. Local browser startup

**Not started.**

Prerequisite not met: dependencies are incomplete and the tree is not runnable. No frontend or backend process was started. No NexHaat URL is listening.

### Why startup is blocked
- No `.bin/tsx`; `npm run dev` cannot launch.
- `express`, `react`, `react-dom`, `@vitejs/plugin-react`, `ws`, `@google/genai`, `@esbuild/win32-x64` all missing.
- Vite cannot load; Express cannot load; tsx cannot run.

### What was NOT done
- Did not start `npm run dev`, `tsx server.ts`, `node --import tsx server.ts`, or `vite preview`.
- Did not open a browser.
- Did not guess ports or alter `vite.config.ts` / `server.ts`.

---

## 7. Protect NexHaat release artifacts

All verified unchanged:

| Artifact | Size (bytes) | SHA-256 | Status |
|---|---|---|---|
| `APK/NexHaat.apk` | 21,884,019 | `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c` | preserved |
| `APK/latest.json` | 2,060 | — | preserved |
| `APK/status.json` | 1,332 | — | preserved |
| `public/downloads/metadata.json` | 2,060 | — | preserved |

APK SHA-256 matches `APK/latest.json` / `APK/status.json` / `public/downloads/metadata.json` `sha256` field.

No APK rebuild, replacement, move, or signing occurred. Release channel remains `verified-testing`. No production signing claimed.

---

## 8. Git safety

### Before actions (relevant subset)
- Branch: `main`
- HEAD: `ac6636a`
- `package-lock.json`: already `M` in working tree at phase start (pre-existing modification).

### After actions
- Branch: `main`
- HEAD: `ac6636a`
- `package-lock.json`: restored to committed content; no longer modified.
- `node_modules`: replaced with restored backup (untracked/local tree; not committed).

### `git diff --check`
- Exit 0.
- One pre-existing CRLF warning for `android/.gradle/buildOutputCleanup/cache.properties` (not introduced by this phase).

### Package/lockfile changes this phase
- `package-lock.json`: restored to committed version from a modified working copy (correction, not upgrade). Modified copy retained in `.temp_recovery/lockfile_snapshot/`.
- `node_modules`: replaced by restored backup (local tree, not committed).
- No application source files edited.
- No commit, push, merge, rebase, or deployment.

---

## 9. Non-goals and explicit limitations

### Non-goals (not done)
- No lockfile modification or upgrade.
- No `npm update`.
- No second `npm ci` / `npm install` attempt.
- No `--force` / `--legacy-peer-deps`.
- No application code or config changes to force startup.
- No APK rebuild/signing.
- No commit/push/merge/deploy.

### Limitations
- The only install attempt available under the rules has already failed.
- The restored `node_modules` is incomplete and not runnable; it is the best recoverable local tree but does **not** satisfy the mission's "NODE_MODULES: READY" condition.
- Memory-constrained machine (~0.4 GB free) is a genuine risk for a full 745-package install.
- The modified lockfile found in the working tree is a separate integrity issue that should be explained before any future install: the committed lockfile resolves to versions that differ from the previously-modified working copy (e.g. `@babel/core` 7.29.7 in committed vs 7.29.13 in modified). Installing from the committed lockfile is the correct path; the modified copy must not be used.
- This report corrects Phase 3.7 preflight numbers and the preflight lockfile hash, which were based on an already-modified working copy.

---

## 10. Recovery options (future, not executed here)

If a runnable local preview is still desired within the same repository, the next bounded options are:
1. Install from the **committed** `package-lock.json` on a machine with more available memory, or with a monitored `npm ci` that can be resumed/recovered safely. This is the clean path and respects the existing lockfile.
2. If the modified lockfile in `.temp_recovery/lockfile_snapshot/` represents an intended update, that must be a deliberate decision and a separate reviewed change — not a side effect of a failed install.
3. If the goal is frontend-only preview and the backend is not required, a frontend-only dependency install could be considered separately, but it still must use the committed lockfile and respect no-upgrade/no-force constraints.

---

## 11. সারসংক্ষেপ (বাংলা)

ব্রাউজার প্রিভিউ এখনও ব্লকড। `package-lock.json` ওয়ার্কিং ট্রি-তে মডিফাইড পাওয়া গেছে; তাকে রিস্টোর করে কমিটড ভার্সনে নেওয়া হয়েছে এবং মডিফাইড কপি ব্যাকআপ করে রাখা হয়েছে। এই সেশনে ইতিমধ্যে একটি `npm ci` চালানো হয়েছে যেটি ইন্টিগ্রিটি ত্রুটির কারণে ব্যর্থ হয়েছে। সেরা-সম্ভাব্য আংশিক ব্যাকআপ restoring করা হয়েছে, কিন্তু সেটি ইনস্টলেশন রানযোগ্য নয় — `express`, `react`, `react-dom`, `@vitejs/plugin-react`, `ws`, `@google/genai`, `@esbuild/win32-x64` এবং `.bin/tsx` অনুপস্থিত। তাই সার্ভার বা ফ্রন্টএন্ড শুরু করা যাচ্ছে না এবং ব্রাউজার URL পাওয়া যাচ্ছে না। APK ফাইল এবং মেটাডেটা সংরক্ষিত। কমিট/পুশ/ডিপ্লয় কোনোটিই করা হয়নি। পরবর্তী ধাপ হিসেবে, বেশি মেমরি/সম্পদ বিশিষ্ট মেশিনে বা রিভিউ করা একটি পরিকল্পনার ওপর ভিত্তি করে, কমিটড `package-lock.json`-এর ওপর ভিত্তি করে পুনরায় ইনস্টলেশন বিবেচনা করা যেতে পারে।

---

## Report path

`docs/PHASE3_7_NODE_DEPENDENCY_RECOVERY_REPORT.md`
