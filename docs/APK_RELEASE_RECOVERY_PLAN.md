# NexHaat — APK Release System Recovery Plan

**Date:** 2026-11-05
**Baseline:** `main` @ `ac6636afd54a7f91002604b6ae160d7d6f791972`
**Source of findings:** `docs/FINAL_APK_RELEASE_VERIFICATION.md` (independent audit, status FAIL)
**Current release status:** **BLOCKED** — no verified APK exists and none may be published.

This plan is written before any code change. It records the investigation results,
the root causes, the recovery work, and the explicit non-goals. It does not
authorize a commit, push, deployment, or production download.

---

## 1. Working-tree state at start of recovery

The recovery started with pre-existing user work present (unchanged by this work):

- Staged + unstaged modifications: `.env.example`, `AuthRepository.kt`,
  `app/api/routes/auth.py`, `app/api/serializers.py`, `app/models/security.py`,
  `app/routes/auth.py`, `app/services/two_factor.py`,
  `app/services/two_factor_crypto.py`,
  `docs/architecture/WEBSITE_ANDROID_FEATURE_PARITY.md`,
  `src/components/FlaskAuthPanel.tsx`, `tests/test_auth_two_factor.py`.
- Unstaged only: `docs/architecture/FEATURE_REGISTRY.json`, `package-lock.json`,
  `server.ts`, `src/components/PWAInstallButton.tsx`,
  `src/services/apkDownloadService.ts`, `vite.config.ts`.
- Deleted (staged): `bun.lock`.
- Untracked: `.github/workflows/android-qa-release.yml`, `APK/`,
  `docs/APK_RELEASE_ARCHITECTURE.md`, `docs/AUTOMATED_TESTING_AUDIT.md`,
  `docs/FINAL_APK_RELEASE_VERIFICATION.md`, `docs/TEST_COVERAGE_MATRIX.md`,
  `public/downloads/`, `reports/`,
  `scripts/nexhaat_qa_release_orchestrator.py`, `serverMarketplace.ts`,
  `.aistudio/artifacts/...`.

None of these files is reverted, cleaned, checked out over, or reformatted by this
recovery.

## 2. Conflict markers (102 findings from `git diff --check`)

`git diff --check` reports 103 findings: 102 leftover conflict markers and 1
end-of-file blank line in `app/api/serializers.py`.

Marker locations, by file:

| File | Markers |
|---|---|
| `app/api/routes/auth.py` | 27 |
| `app/services/two_factor_crypto.py` | 24 |
| `tests/test_auth_two_factor.py` | 21 |
| `app/services/two_factor.py` | 15 |
| `app/routes/auth.py` | 6 |
| `app/models/security.py`, `docs/architecture/WEBSITE_ANDROID_FEATURE_PARITY.md`, `AuthRepository.kt` | 3 each |
| `app/api/serializers.py` | 1 (EOF blank line, not a marker) |

**Ownership:** pre-existing and **not** introduced by the release system. All of
these files were already modified in the index and working tree when the audit
began, and `git grep '^<<<<<<< ' HEAD` shows the markers were **committed in
`ac6636a "Fix"`** (real merge conflict text from `d5fb7ab`). The commit before it,
`1fc9dcc`, is marker-free.

**Decision:** not resolved in this recovery. They belong to the in-progress 2FA
work, and each marker requires a product decision (for example, whether
`UserBackupCode` stays imported, or whether a second CSRF refresh guard is kept).
Resolving them without authorization would rewrite user work. They are instead
treated as a **hard release blocker**: they break `git diff --check`, Python import,
and Kotlin compilation, so no genuine APK can be built from this tree until the
owner resolves them.

The release pipeline is changed to detect markers and fail Gate 1, so a tree in
this state can never be released by accident.

## 3. Root causes of the failed release

### 3.1 The orchestrator manufactured an APK

`run_gate_5_package_apk()` builds a ZIP from source when no Gradle output exists:
plain-text `AndroidManifest.xml`, `assets/app-info.json`, `classes.dex` consisting
of `b"dex\n039\x00" + 1024 zero bytes`, and `META-INF/CERT.RSA` filled with `0xFF`.
It then validates only that three expected entry names exist and that ZIP CRCs are
intact.

An APK is a ZIP **plus** a compiled binary manifest, valid DEX containers, and a
real signing block. None of those is checked, so an arbitrary ZIP passes.

### 3.2 The build path was never a release path

The only Gradle invocation was `:app:assembleDebug`; on success the **debug** APK
was copied and published as `buildType: "release"`. Production signing, production
API/media origin, and `assembleRelease` were never exercised.

### 3.3 Gate 6 asserted the container format

`run_gate_6_smoke_verification()` checked four magic bytes (`PK\x03\x04`) and
reported "valid magic bytes and structural consistency confirmed". No HTTP request,
no APK parse, no install, no launch.

### 3.4 Reports were fabricated

`generate_reports()` writes hard-coded PASS/VERIFIED rows: 23 "VERIFIED" UI
modules, 24/24 marketplace tests, 8/8 security tests, 12 ms API latency, "~22MB"
memory. These are constants in the source, not measurements. `test-summary.json`
therefore cannot be used as release evidence.

### 3.5 The artifacts never existed in this checkout

`APK/latest.apk`, `public/downloads/nexhaat.apk`, and `APK/releases/` are all
absent, while `APK/latest.json` claims 33,762 bytes, SHA-256
`68ce8ad8…9e3e22`, and six PASS gates. The three `checksums.txt` entries name
archives that are not present. The claimed artifact's own bytes are unavailable, so
its manifest, package, DEX and signature cannot be verified at all.

### 3.6 Build environment defects

- `npm ci` fails: `package-lock.json` is missing required optional platform
  packages (`fsevents@2.3.3`, `@esbuild/*@0.28.2`, `@rollup/rollup-*`). The
  lockfile was produced with those entries dropped, not with conflicting versions.
- `android/gradlew` is committed as mode `100644`; `./gradlew` on Linux/Ubuntu
  fails with permission denied.
- The workflow `.github/workflows/android-qa-release.yml` is untracked, so GitHub
  cannot run it; it also uses mutable action tags for the Java, Gradle and emulator
  actions.
- Local toolchain: PATH `java` is 1.8, while the project requires 17. The SDK
  exists at `%LOCALAPPDATA%\Android\Sdk` but `ANDROID_HOME`/`ANDROID_SDK_ROOT` are
  set to the malformed literal `:LOCALAPPDATA\Android\Sdk`. No emulator binary and
  no system image are installed. `adb` exists.
- Production signing is unconfigured (no keystore, no four signing variables), and
  `NEXHAAT_RELEASE_BASE_URL` still falls back to `RELEASE_BASE_URL_REPLACE_ME`.

### 3.7 Promotion and rollback are not atomic

`promote_release()` copies into the archive, `latest.apk`, the public mirror, two
metadata files and an appended checksum file as separate operations; a crash leaves
them inconsistent. `rollback_to()` uses plain `shutil.copy2()` into the live
locations, writes metadata directly, never re-validates the target, and never
touches `checksums.txt`.

### 3.8 Get App overstates availability

`/api/download/apk/info` returns `verified: metadata.verified ?? exists`, so a
stale metadata file can advertise a verified release while the APK is missing.
`PWAInstallButton` always renders "Verified Release" and an enabled download
button without checking `exists`/`verified`.

## 4. Recovery work (ordered)

| # | Work | Acceptance |
|---|---|---|
| 1 | `scripts/validate_apk.py` strict validator | Rejects plain ZIPs, text manifests, zero/invalid DEX, missing or malformed signatures, checksum and metadata mismatches; requires `apksigner` for a verified verdict; detects package `com.nexhaat.app`, version, SDK levels |
| 2 | Orchestrator gates | Six real, fail-closed gates; no synthetic APK fallback; real `assembleRelease`; strict validation; install check; failure writes BLOCKED diagnostics and never touches `latest.apk` |
| 3 | Reports | Generated only from observed facts; not-run checks labelled `NOT RUN`; no hard-coded PASS tables |
| 4 | Release storage | Staged, validated, ordered publication; atomic `os.replace` per file; checksum maintenance; journal/backups; rollback that re-validates and restores matching metadata |
| 5 | Build environment | Lockfile synced without version drift; `gradlew` executable mode; workflow pinned to the SHAs already used in this repository, real emulator install/launch, no fallback success |
| 6 | Get App | Download disabled unless the artifact exists and passed validation; server no longer reports `verified` for a missing or mismatched file |
| 7 | Verification | Run the real pipeline, classify PASS/FAIL/NOT RUN/BLOCKED, and publish a final report |

## 5. Non-goals

- No resolution of the 2FA merge conflicts.
- No production keystore generation, no signing secret handling, no secret exposure.
- No change to authentication, payment, order, or seller business logic.
- No commit, push, merge, deployment, workflow dispatch, or production download.
- No claim that a localhost test proves the hosted site works.

## 6. Release policy during recovery

`APK/latest.apk` is not created until a genuine, signed, validated APK exists.
Until then:

- `APK/status.json` carries `BLOCKED` with the failing gate and reason.
- Stale `APK/latest.json` / `public/downloads/metadata.json` claims are downgraded
  to unverified so the website cannot present a missing artifact as verified.
- The Get App download action stays disabled when no verified artifact exists.

**Completion rule:** RELEASE READY only when a genuine Gradle-built, release-signed
APK passes strict structural validation, installs and launches in an Android
emulator, all six gates pass on the same artifact, and the download endpoint serves
byte-identical content. Otherwise the status remains **BLOCKED**.
