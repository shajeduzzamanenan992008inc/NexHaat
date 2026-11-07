# NexHaat — APK Release System Recovery: Status & Verification

**Date:** 2026-11-06
**Baseline commit:** `ac6636afd54a7f91002604b6ae160d7d6f791972` (`main`)
**Source of findings:** `docs/FINAL_APK_RELEASE_VERIFICATION.md` (independent audit, FAIL)
**Release status: `BLOCKED`.** No APK was built, signed, published or enabled for download.

This document records what was repaired, what was proven, and what is still
required before the release may be called READY. Nothing here is committed,
pushed, deployed, or published.

---

## 1. Root causes that were fixed

| # | Defect | Where | Fix |
|---|---|---|---|
| 1 | A ZIP built from source files was accepted as an APK | `run_gate_5_package_apk()` fallback | Fallback deleted; gate now requires a real `assembleRelease` output |
| 2 | Validity was "three entry names exist + CRCs are intact" | Gate 5 | Replaced by `scripts/validate_apk.py` (binary manifest, DEX integrity, signing block, `apksigner` verification, checksum) |
| 3 | A debug APK was published as `buildType: release` | Gate 5 | Only `app/build/outputs/apk/release/app-release.apk` is accepted; signing env is mandatory |
| 4 | Smoke gate only checked `PK\x03\x04` | Gate 6 | Now requires `adb install`, launcher start, live process and no `AndroidRuntime` fatal exception |
| 5 | Reports were hard-coded PASS tables (23 "VERIFIED" screens, 24/24, 8/8, 12 ms) | `generate_reports()` | Reports are generated from observed gate results only; unexecuted work is `NOT RUN` |
| 6 | Publication was a sequence of independent copies | `promote_release()` | All files staged, journalled, then swapped with `os.replace`; automatic restore on failure |
| 7 | Rollback copied files without verification and never updated checksums | `rollback_to()` | Target must re-validate (and optionally install) before it is allowed to become `latest.apk`; metadata and `checksums.txt` are updated |
| 8 | `/api/download/apk/info` reported `verified` from stale metadata | `server.ts` | `verified` is computed: artifact must exist **and** its SHA-256 must match metadata |
| 9 | The download route served any file present on disk | `server.ts` | Unverified artifacts return `503 APK_NOT_VERIFIED`; only a verified artifact is served |
| 10 | "Get App" showed "Verified Release" and an enabled download with no artifact | `PWAInstallButton.tsx` | Download is disabled, verified badge removed and direct links hidden unless `exists && verified` |
| 11 | `latest.json` claimed a 33,762-byte verified APK that does not exist | `APK/`, `public/downloads/` | Claim withdrawn (`verified: false`, `sha256: null`); original claim preserved in `reports/failures/` |
| 12 | `android/gradlew` was committed without the executable bit | git index | Index mode changed to `100755` (staged, not committed) |
| 13 | CI used mutable action tags and asserted fake success | workflow | All actions pinned to commit SHAs; missing signing/secrets fail the job; no fallback path |
| 14 | A fake-APK generator shipped in the repo | `scripts/generate_apk_package.py` | Disabled: it now refuses to run and points at the real pipeline |

## 2. How the release decision is made now

`scripts/nexhaat_qa_release_orchestrator.py` runs six mandatory gates. Any gate
that does not return `PASS` — including `BLOCKED` (cannot execute) — aborts the
run, writes diagnostics, sets `APK/status.json` to `BLOCKED`, and leaves
`APK/latest.apk` untouched.

| Gate | Name | What it actually executes |
|---|---|---|
| 1 | Repository integrity & manifest | `validate_repository_structure.py --fail-on-review`, conflict-marker scan, `git diff --check`, manifest/`applicationId` identity |
| 2 | Security test suite | `npm test` |
| 3 | Marketplace API suite | `node tests-node/marketplace-api.test.mjs` |
| 4 | TypeScript compilation | `node_modules/typescript/bin/tsc --noEmit` |
| 5 | Release build & APK validation | `:app:assembleRelease` (signing + release origin required) → `scripts/validate_apk.py` |
| 6 | Device install & launch | `adb install`, `am start`, `pidof`, crash-buffer check |

Publication happens only after all six pass, and is followed by
`verify_publication()`: re-validation of `APK/latest.apk` against its metadata,
mirror byte-equality, and an HTTP download from the real Express server whose
bytes must hash to the validated checksum. A failure there writes `BLOCKED` and
does not leave the site advertising a release.

## 3. Verification performed (this host, 2026-11-06)

| Check | Result | Evidence |
|---|---|---|
| `python tests/test_apk_validator.py` | **PASS** (9/9) | Placeholder ZIP, zero-filled DEX, old orchestrator fallback, wrong package, unsigned APK, checksum/metadata mismatch all rejected; binary manifest fields parsed correctly |
| Validator never returns PASS without crypto verification | **PASS** | A structurally perfect, signature-file-bearing APK returns `BLOCKED` when `apksigner` is absent |
| `validate_repository_structure.py --fail-on-review` | **PASS** (exit 0) | `repository_structure=PASS` |
| Gate 3 — marketplace API suite | **PASS** (exit 0) | 20/20 tests pass |
| Gate 1 — full pipeline run | **FAIL** (exit 1) | 102 committed conflict markers at `HEAD` in 2FA/auth files |
| Fail rule on the real tree | **PASS** | `APK/latest.json`, `APK/checksums.txt`, `public/downloads/metadata.json` SHA-256 identical before/after; `status.json` set to `BLOCKED` |
| Fail rule on an isolated release fixture | **PASS (fixture only)** | Sentinel `APK/latest.apk` SHA-256 `e32222c7…bdc0` identical before/after; exit 1; `status.json` `BLOCKED` |
| `--rollback-to` with no archive | **PASS (refuses)** | Exit 1, `APK/releases` missing; live files untouched |
| `--verify-release` | **FAIL (correct)** | `APK/latest.apk` does not exist → status must stay `BLOCKED` |
| Gate 2 — `npm test` | **NOT RUN (environment)** | `npm ci` never completed: the registry repeatedly returned corrupted tarballs, leaving `node_modules` incomplete (`Cannot find module 'ms'`). Not a code result |
| Gate 4 — `tsc --noEmit` | **NOT RUN (environment)** | Same incomplete install (`TS2688` for missing `@types/*`) |
| TS syntax of edited files | **PASS** | TypeScript parser over `server.ts`, `PWAInstallButton.tsx`, `apkDownloadService.ts`: 0 syntax diagnostics. This is a syntax check, **not** a type check |
| Gate 5 — Android release build | **BLOCKED** | No JDK 17 (no `java` on PATH), no `ANDROID_HOME`/`ANDROID_SDK_ROOT`, no signing credentials, release origin unset |
| Gate 6 — emulator install/launch | **BLOCKED** | No `adb`, no emulator, no system image |
| CI workflow execution | **NOT RUN** | Workflow file is untracked; running it requires a commit/push, which was not authorised |

## 4. Remaining blockers (all must clear before RELEASE READY)

1. **Committed conflict markers.** 102 markers in `AuthRepository.kt`,
   `app/api/routes/auth.py`, `app/models/security.py`, `app/routes/auth.py`,
   `app/services/two_factor.py`, `app/services/two_factor_crypto.py`,
   `docs/architecture/WEBSITE_ANDROID_FEATURE_PARITY.md`,
   `tests/test_auth_two_factor.py` (+1 EOF blank line in
   `app/api/serializers.py`). They are **pre-existing**: `git grep` at `HEAD`
   finds them in `ac6636a "Fix"`, and commit `1fc9dcc` is marker-free. They belong
   to the in-progress 2FA work and each needs an owner decision, so they were not
   auto-resolved. Until they are resolved, Python import and Kotlin compilation
   fail and Gate 1 blocks.
2. **Release signing.** No keystore and none of `NEXHAAT_KEYSTORE_PATH`,
   `NEXHAAT_KEYSTORE_STORE_PASSWORD`, `NEXHAAT_KEYSTORE_KEY_ALIAS`,
   `NEXHAAT_KEYSTORE_KEY_PASSWORD`. Gradle silently produces an *unsigned*
   release without them, which Gate 5 refuses.
3. **Release origins.** `NEXHAAT_RELEASE_BASE_URL` and `NEXHAAT_MEDIA_BASE_URL`
   are unset; the release default remains `RELEASE_BASE_URL_REPLACE_ME`.
4. **Android toolchain on the release runner.** JDK 17, Android SDK
   (`cmdline-tools`, platform 36, build-tools with `apksigner`) and an emulator
   with a system image. None exist on this host.
5. **Gates 2 and 4 must be re-run** after a clean `npm ci` on a working network or
   in CI; they were not verified here.
6. **No instrumented UI journeys exist.** There are no `androidTest` sources, so
   authentication/OTP/catalog/cart/checkout remain `NOT RUN` by definition. The
   workflow verifies install, launch and absence of a startup crash only.
7. **Hosted-distribution proof outstanding.** `verify_publication()` exercises the
   Express download endpoint locally. Whether the deployed Flask/Gunicorn host
   serves `/api/download/apk` at all is unverified, and must not be claimed.

## 5. Path to RELEASE READY

1. Owner resolves the 2FA conflict markers and commits the repair.
2. Configure the four signing secrets and both base URLs; run a clean `npm ci`.
3. Run `python scripts/nexhaat_qa_release_orchestrator.py` on a machine (or CI
   runner) with JDK 17, the Android SDK and a booted emulator.
4. All six gates must be `PASS` on the same artifact, `verify_publication()` must
   succeed, and `APK/status.json` must read `PASS`.
5. Only then flip the website download; confirm from the deployed host that the
   downloaded bytes hash to `APK/latest.json`'s `sha256`.

Until every item above is satisfied, `APK/status.json` stays `BLOCKED` and the
Get App download stays disabled.
