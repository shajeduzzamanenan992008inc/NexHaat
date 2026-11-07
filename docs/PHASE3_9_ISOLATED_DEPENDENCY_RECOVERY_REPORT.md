# NexHaat Isolated Dependency Recovery Report — Phase 3.9

**Created:** 2026-11-07
**Original project:** `D:\FTP\NexHaat` (branch `main`, HEAD `ac6636afd54a7f91002604b6ae160d7d6f791972`)
**Isolated verification directory:** `D:\FTP\NexHaat_verify`
**Phase:** 3.9 — Isolated Dependency Recovery & Verification
**Predecessor:** `docs/PHASE3_8_DEPENDENCY_LOCKFILE_FORENSIC_AUDIT_REPORT.md`

---

## Final Status

```
PHASE_3_9: BLOCKED
PREFLIGHT: PASS
ISOLATED_DIR_CREATED: PASS
SOURCE_HASH_VERIFICATION: PASS
REGISTRY_CONFIGURATION: PASS
NPM_CI: FAIL        (EHOSTUNREACH — network, after 485 successful tarball fetches)
EINTEGRITY_OCCURRENCES: 0
LOCKFILE_REGENERATED: NO
DEPENDENCY_VERIFICATION: BLOCKED   (no installed tree; npm rolled back)
NPM_LS: NOT_RUN
LOCKFILE_INTEGRITY_STATUS: PASS    (0 integrity rejections; hash unchanged)
ORIGINAL_PROJECT_CHANGED: NO
ORIGINAL_NODE_MODULES_TOUCHED: NO
APK_PRESERVED: YES
BROWSER_PREVIEW: NOT_STARTED
INSTALL_ATTEMPTS: 1 (single, per authorization — no retry)
```

**One-line outcome:** the committed lockfile produced **zero** integrity failures across 485 successfully downloaded packages and then aborted on a genuinely network-level error (`EHOSTUNREACH`). The lockfile is corroborated as sound; the blocker is connectivity, not the manifest, not the lockfile, and not the npm cache.

---

## 1. Executive summary

The isolated verification was executed exactly as scoped: one fresh directory outside the repository, two files copied, hashes gated, exactly one `npm ci`, no retry.

**What the run proved:**

1. **The committed lockfile is accepted by npm.** Across 485 distinct tarballs fetched with HTTP 200 and 1,688 fetch operations, npm reported **zero `EINTEGRITY` errors and zero "seems to be corrupted" warnings**. This is the decisive positive result: every integrity value that npm could compare matched the published registry artifact. Phase 3.8's conclusion — that the earlier failures came from the *modified working-copy* lockfile, not the committed one — is now independently corroborated by a real installation.
2. **The 198-second run reached deep into the tree before failing.** The debug log shows extraction work on `es-toolkit`, `firebase`, and `@apideck/better-ajv-errors`, i.e. hundreds of packages were successfully materialized.
3. **The abort was purely network.** `npm error code EHOSTUNREACH` on `https://registry.npmjs.org/pretty-bytes/-/pretty-bytes-5.6.0.tgz`, with 149 distinct tarballs exhausting all three attempts and 1,180 `EHOSTUNREACH` occurrences in total.
4. **The registry is healthy right now.** A read-only `HEAD` probe immediately after the failure returned `200` for `registry.npmjs.org` in 0.128 s and `200` for the exact failing tarball in 0.070 s. The failure was transient, not a configuration fault.
5. **No dependency tree remains to verify.** npm's rollback deleted the partially installed `node_modules`; the directory is now empty (0 bytes). All package-presence checks are therefore `BLOCKED`, not `FAIL`.
6. **The original project is untouched.** Same `package.json` and `package-lock.json` hashes, same HEAD, original `node_modules` still at 181 entries (131 non-dot + 50 dot-prefixed staging leftovers), `.temp_recovery/` intact, APK SHA-256 unchanged.

**Why this is a good outcome despite the FAIL:** the phase existed to answer "is the committed lockfile installable?" The answer so far is "yes, its integrity data is correct in every case npm tested." The remaining obstacle is a flaky connection, which is cheap to overcome later and carries no data risk. No retry was attempted, as explicitly required.

---

## 2. Preflight results

Executed before creating anything.

| Check | Result | Status |
|---|---|---|
| Node.js version | `v26.13.0` | PASS |
| npm version | `11.20.0` | PASS |
| Free space on `D:` | 58 GB available of 87 GB (35% used) | PASS |
| Total / free memory | 3.93 GB total / 0.72 GB free | PASS (constrained but workable) |
| Git HEAD | `ac6636a` | PASS |
| `git status --short -- package.json package-lock.json` | empty (clean) | PASS |
| `package.json` SHA-256 | `840f15a4…f5420f` (expected) | PASS |
| `package-lock.json` SHA-256 | `f62065d2251429af06733e1626cef940742fea5f3564d49067e65763a019c8df` (expected) | PASS |
| Verification directory existence | `D:\FTP\NexHaat_verify` **did not exist** | PASS |
| npm registry | `https://registry.npmjs.org/` | PASS |
| `proxy` / `https-proxy` | `null` / `null` | PASS |
| `strict-ssl` | `true` | PASS |
| Project `.npmrc` | absent | PASS |
| User `.npmrc` (`$USERPROFILE/.npmrc`) | absent | PASS |
| `fetch-retries` | 2 | recorded |
| `maxsockets` | 15 (npm default) | recorded |

Disk space was sufficient, so the disk gate did not trigger a stop. No secrets, tokens, or credentials were printed; only registry/proxy/SSL values were read.

**Preflight verdict: PASS.**

---

## 3. Verification directory status

| Item | Value |
|---|---|
| Path | `D:\FTP\NexHaat_verify` |
| Pre-existing? | **No** — created fresh in this phase |
| Pre-existing user work overwritten? | **No** — none existed; nothing was overwritten |
| Contents created | `package.json`, `package-lock.json`, `node_modules/`, `npmci-phase39.log` |
| `node_modules` after run | **empty** (2 entries: `.` and `..`; 0 bytes) — npm rolled back the partial install |
| Failed directory preserved? | **Yes** — retained on disk for diagnosis, as required |

Nothing from the repository was copied except the two manifest files. Specifically **not** copied: `node_modules`, `.git`, `.env*`, any API keys or secrets, APK files, user data, `.temp_recovery/`, build outputs.

---

## 4. Source and copied file hashes

| File | Source SHA-256 | Copied SHA-256 | After the failed run | Status |
|---|---|---|---|---|
| `package.json` | `840f15a4fa0319131cac76699633b5959d700f651cf3faa592cba96091f5420f` | identical | identical | PASS |
| `package-lock.json` | `f62065d2251429af06733e1626cef940742fea5f3564d49067e65763a019c8df` | identical | **identical** | PASS |

Both hashes were checked against the expected values **before** `npm ci` ran (hard gate — the script would have exited 2 otherwise). The lockfile was re-hashed **after** the failed install and is unchanged: `npm ci` did not regenerate, rewrite, or normalize it. Sizes: `package.json` 1,232 B, `package-lock.json` 391,180 B (matching Phase 3.8).

---

## 5. Node / npm versions

| Component | Version |
|---|---|
| Node.js | `v26.13.0` |
| npm | `11.20.0` |
| OS | Windows (`win32`), shell: Git Bash (POSIX) |
| npm cache | `C:\Users\Enan\AppData\Local\npm-cache` (~61 MB before this run) |

> **Note on shell:** the brief requested PowerShell-compatible commands. The agent's execution environment is Git Bash, so POSIX syntax was used throughout. No `cmd.exe`-specific syntax was used, and no operation differs in effect. This is recorded for transparency.

---

## 6. Registry configuration findings

- Effective registry: **`https://registry.npmjs.org/`** — the expected public registry.
- `proxy`: `null`. `https-proxy`: `null`. No mirror, no corporate proxy, no custom scope mapping.
- `strict-ssl`: `true` — TLS verification was not disabled.
- **No `.npmrc` exists** at project or user level, so no override of `registry`, `proxy`, `cafile`, or auth tokens is in play.
- No `.npmrc` was created or modified; global npm configuration was not changed; no registry was switched.

**Registry verdict: PASS.** No credentials were read, displayed, or transmitted.

---

## 7. `npm ci` result and error summary

**Command (exactly as authorized):**

```
npm ci --no-audit --no-fund
```

Run once, from `/d/FTP/NexHaat_verify` (confirmed by `pwd` immediately before execution). No `--prefer-offline`, no `--force`, no `--legacy-peer-deps`, no second attempt.

| Metric | Value |
|---|---|
| Exit code | **1 (FAIL)** |
| Duration | **198 s** (~3 min 18 s) |
| Captured log | `D:\FTP\NexHaat_verify\npmci-phase39.log` (1,921 B) |
| npm debug log | `C:\Users\Enan\AppData\Local\npm-cache\_logs\2026-11-07T07_32_58_432Z-debug-0.log` (426,266 B) |
| `http fetch` operations | 1,688 |
| Distinct tarballs fetched with HTTP 200 | **485** |
| `EINTEGRITY` occurrences | **0** |
| "seems to be corrupted" warnings | **0** |
| `EHOSTUNREACH` occurrences | 1,180 |
| Tarballs that exhausted all 3 attempts | **149** |
| `ENOTEMPTY` / `EPERM` | 4 (cleanup-time only) |

**Terminal error:**

```
npm error code EHOSTUNREACH
npm error errno EHOSTUNREACH
npm error request to https://registry.npmjs.org/pretty-bytes/-/pretty-bytes-5.6.0.tgz failed, reason:
npm error A complete log of this run can be found in: C:\Users\Enan\AppData\Local\npm-cache\_logs\2026-11-07T07_32_58_432Z-debug-0.log
```

Note the empty `reason:` field — characteristic of a Windows-level `WSAENETUNREACH`/`WSAEHOSTUNREACH` socket error rather than an HTTP status or TLS failure.

**Tarballs that failed all three attempts (representative):**

`pretty-bytes-5.6.0.tgz`, `@opentelemetry/core-2.9.0.tgz`, `@opentelemetry/resources-2.9.0.tgz`, `@opentelemetry/sdk-trace-base-2.9.0.tgz`, `@opentelemetry/sdk-trace-web-2.9.0.tgz`, `web-vitals-5.3.0.tgz`, `@babel/helper-wrap-function-7.29.7.tgz`.

**Rollback behaviour:** after aborting, npm ran its cleanup and removed the partial tree. Two directories resisted removal under Windows (`es-toolkit\dist\server`, `firebase\firestore\lite\pipelines\dist`) producing `EPERM`/`ENOTEMPTY` warnings, but the final state is an empty `node_modules` (0 bytes). These are **post-failure cleanup artifacts**, not installation-integrity errors.

**Failure classification:** transient **network unreachability**, not integrity (`EINTEGRITY` = 0), not registry protocol, not disk (58 GB free), not lockfile/manifest disagreement.

---

## 8. Dependency verification results

All checks below are **BLOCKED** — not failed — because `node_modules` was rolled back to empty. A "MISSING" result here carries no information about the lockfile's correctness.

| Check | Result | Status |
|---|---|---|
| `node_modules` exists | yes, but empty (0 bytes) | BLOCKED |
| `node_modules/.bin` shims | absent (0 entries) | BLOCKED |
| `tsx` present + expected version | MISSING | BLOCKED |
| `vite` | MISSING | BLOCKED |
| `typescript` | MISSING | BLOCKED |
| `react` / `react-dom` | MISSING / MISSING | BLOCKED |
| `express` | MISSING | BLOCKED |
| `@vitejs/plugin-react` | MISSING | BLOCKED |
| `ws` | MISSING | BLOCKED |
| `@google/genai` | MISSING | BLOCKED |
| `esbuild` | MISSING | BLOCKED |
| `@esbuild/win32-x64` platform binary | MISSING | BLOCKED |
| Installed versions match lockfile | not measurable | BLOCKED |
| No unexpected nested duplicate wrapper dirs | not measurable | BLOCKED |
| No unresolved missing dependency reported | not measurable | BLOCKED |

**Observations that survive the rollback:**

- npm resolved and fetched the dependency graph without any peer-dependency or lockfile-sync error. No `npm error code ERESOLVE`, no "lock file does not satisfy", no "package.json and package-lock.json are not in sync" appeared — the pair is structurally accepted.
- The npm `deprecated` warnings observed (`node-domexception@1.0.0`, `glob@11.1.0`, `@opentelemetry/sdk-trace-base@2.10.0`, `@opentelemetry/sdk-trace-web@2.10.0`) are advisory-only and do not block installation.

---

## 9. `npm ls` result

**NOT_RUN.**

Reason: `node_modules` is empty after npm's rollback. `npm ls --depth=0` would report every declared dependency as missing and would describe the failed state rather than the lockfile, producing a misleading result. The command was deliberately withheld rather than reported as a meaningful check.

It should be run in the next authorized phase, immediately after a successful `npm ci`.

---

## 10. Lockfile integrity status

| Check | Result | Status |
|---|---|---|
| `EINTEGRITY` during install | **0 occurrences** | PASS |
| "seems to be corrupted" warnings | **0 occurrences** | PASS |
| Tarballs verified against lockfile integrity | **485 distinct, all accepted** | PASS |
| `package-lock.json` SHA-256 after run | `f62065d2…c8df` — unchanged | PASS |
| Lockfile regenerated or rewritten | **No** | PASS |
| `package.json` modified | **No** (hash unchanged) | PASS |

This is the central technical finding of Phase 3.9. In Phase 3.7 the corrupted lockfile produced `EINTEGRITY` almost immediately and 360–1,726 "corrupted" warnings. The **committed** lockfile produced **none at all** across 485 successful downloads — a directly comparable, real-world confirmation that its integrity values match `registry.npmjs.org`.

**Caveat, stated plainly:** 485 of 745 entries were fetched before the network failed. The remaining ~260 entries were never integrity-tested in this run. The result is strong corroboration, not a completed proof, of whole-lockfile validity.

---

## 11. Original project preservation results

Rechecked after the isolated run.

| Check | Expected | Observed | Status |
|---|---|---|---|
| Git HEAD | `ac6636a` | `ac6636a` | PASS |
| `git status --short -- package.json package-lock.json` | empty | empty | PASS |
| `package.json` SHA-256 | `840f15a4…f5420f` | identical | PASS |
| `package-lock.json` SHA-256 | `f62065d2…c8df` | identical | PASS |
| Original `node_modules` top-level entries | 181 (as recorded in Phase 3.8) | **181** (131 non-dot + 50 dot-prefixed staging leftovers) | PASS |
| `node_modules` deleted or renamed | must not happen | not touched | PASS |
| `.temp_recovery/` snapshots + logs | preserved | present, unmodified | PASS |
| `node_modules_backup_temp` | already absent since Phase 3.7 | still absent | recorded |
| Application source / configuration | unmodified by this phase | unmodified | PASS |

**Reconciliation note:** a plain `ls node_modules | wc -l` reports **131**, not 181, because the 50 `.name-hash` staging directories are dot-prefixed and hidden from `ls` without `-a`. With `-a`, the count is 183 (= 181 real entries + `.` + `..`). This exactly matches Phase 3.8's figure; **the original `node_modules` is unchanged**.

**Pre-existing work preserved:** `git status --short` reports **67 changed paths** (staged and unstaged modifications under `android/`, `app/`, `docs/`, `scripts/`, plus a deleted `bun.lock`). These are **pre-existing contributor changes that were already present before this phase** and were not touched, staged, reset, or reverted. The Phase 3.9 report is the only new path added to the repository by this phase.

---

## 12. APK preservation results

| Artifact | Expected | Observed | Status |
|---|---|---|---|
| `APK/NexHaat.apk` SHA-256 | `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c` | **identical** | PASS |
| `APK/NexHaat.apk` size | 21,884,019 B | 21,884,019 B | PASS |
| `APK/latest.json` | 2,060 B, present | present, unmodified | PASS |
| `APK/status.json` | 1,332 B, present | present, unmodified | PASS |
| `public/downloads/metadata.json` | 2,060 B, present | present, unmodified | PASS |

No APK file or metadata file was read-modified, regenerated, repackaged, or deleted.

---

## 13. Browser preview status

**NOT_STARTED.**

As required by the phase scope:

- No Vite dev server was started.
- No Express server was started.
- No browser preview was opened.
- No dependency was copied or moved into the original project.

**Is the isolated environment ready for a later preview phase?** **No — not yet.** The isolated directory contains no installed dependencies (rollback left it empty). A successful install must complete first. Once it does, that directory can host a preview because it holds the correct `package.json`/`package-lock.json`; it does **not** contain the application source, so a preview would still require the source tree.

---

## 14. Recommended next action

The blocker is a transient network failure, and the evidence says the lockfile itself is sound. The recommendation is therefore narrow and low-risk.

### Recommended: one authorized retry of the same isolated install, with reduced concurrency

1. **Reuse `D:\FTP\NexHaat_verify`** (the directory already exists with the verified files; do not recreate it). Note that `npm ci` will recreate `node_modules` — that is safe here precisely because it is the isolated directory.
2. Re-verify the two hashes before running again.
3. Run **one** attempt of:
   ```
   npm ci --no-audit --no-fund --maxsockets=4
   ```
   `--maxsockets=4` reduces simultaneous connections from npm's default of 15. The failure pattern — 485 successes followed by 1,180 `EHOSTUNREACH` on 149 tarballs, with the registry answering `200` in 0.07 s moments later — is consistent with local socket/connection exhaustion or a router/NAT limit on a constrained link, and is the single most likely thing to fix it without touching the lockfile.
4. **Do not** add `--prefer-offline` (the cache cannot satisfy 745 packages and it would mask a network verdict), `--force`, or `--legacy-peer-deps`.
5. If it fails again with `EHOSTUNREACH`, stop and treat this as an environment/network problem to resolve outside the repository (wired connection, disable VPN/aggressive firewall, or lower `maxsockets` further to 2).

### Explicitly not recommended

| Approach | Why not |
|---|---|
| `npm cache clean` / `cache verify` | Destroys forensic state and cannot fix `EHOSTUNREACH`. Integrity is already proven clean (0 `EINTEGRITY`). |
| Regenerating the lockfile (`npm install`) | Would discard the only artifact now proven integrity-correct, and violates the standing rule. |
| Repairing the original `node_modules` in place | Still structurally broken (nested duplicates, empty `.bin`, esbuild 0.28.2 vs binary 0.25.12) and would destroy the baseline. |
| Increasing retries/sockets to extreme values | Masks rather than resolves a flaky link; higher concurrency is the probable cause, not the cure. |

### Gate before any Phase 4.0 work

Only after a **successful** `npm ci` in `D:\FTP\NexHaat_verify` with **zero `EINTEGRITY`** may the verified tree be considered for the original project — and even then only by a separately authorized step that renames the existing `node_modules` aside (never deletes it) before moving the verified tree in.

---

## 15. Explicit confirmation of actions not performed

I confirm, for the entirety of Phase 3.9:

- **`npm ci` was run exactly once**, in `D:\FTP\NexHaat_verify`, and **not retried** after it failed.
- **No npm command was executed inside `D:\FTP\NexHaat`.** No `install`, `ci`, `update`, `rebuild`, `dedupe`, `prune`, or `audit fix` touched the original project.
- **No `--force`, `--legacy-peer-deps`, `--prefer-offline`** was used.
- **No npm cache clean, repair, verify, or prune** was executed. The cache was only populated as an unavoidable side effect of the authorized download, and its location/size were read, not altered.
- **No lockfile regeneration or update** occurred; the isolated `package-lock.json` hash is identical before and after the run, and the original was never written.
- **The original `package.json` and `package-lock.json` were not modified** — hashes verified unchanged.
- **The original `node_modules` was not deleted, renamed, moved, flattened, copied, or repaired** — still 181 entries.
- **No application source code or configuration was modified.**
- **No frontend, Express server, or browser preview was started**; no port was bound.
- **No dependency was copied into the original project.**
- **No Git mutation** — no `add`, `commit`, `push`, `merge`, `rebase`, `reset`, `checkout`, `restore`, `stash`, `clean`, or `tag`. Only read-only inspection (`status`, `rev-parse`).
- **No APK file or APK metadata was modified** — SHA-256 still `f42061b4…608c`.
- **No deployment, release, or external service interaction** occurred other than ordinary HTTPS reads from `registry.npmjs.org` required by the single authorized install.
- **No pre-existing file, backup, snapshot, or user work was overwritten or removed.**
- The only repository change made by this phase is this report file.

**Phase 3.9 verdict: BLOCKED** — not because the lockfile is wrong (it is corroborated sound), but because the single authorized installation attempt was cut short by transient network unreachability. Phase 4.0 was not started.

---

*End of Phase 3.9 report.*
