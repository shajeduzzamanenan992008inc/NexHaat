# APK RELEASE — PHASE 3.0 DEBUG BUILD & TESTING RECOVERY REPORT

Created: 2026-11-07
Workspace: `D:\FTP\NexHaat`
Android root: `android/`
Gradle module: `:app`
Package: `com.nexhaat.app`
Mode: DEBUG BUILD AND VALIDATION ONLY

## Final status

```text
DEBUG_BUILD: PASS
DEBUG_INSTALL: BLOCKED (no Android device or running emulator)
STABLE_APK: NOT_RELEASED
GET_APP_STATUS: UNAVAILABLE
PRODUCTION_SIGNING: BLOCKED (not configured; unchanged)
```

`DEBUG_BUILD: PASS` is based on the required `:app:assembleDebug` invocation exiting 0 and the
resulting Gradle debug artifact passing every integrity gate below. One important caveat is
recorded in Section 4: Gradle considered all 42 tasks up-to-date, and a separate forced
verification rebuild was terminated at the 600-second execution bound, so the validated APK is
the existing Gradle debug output, not a newly packaged artifact from this phase.

---

## 1. Preflight results

### 1.1 Host and JDK

- OS: Windows 10 10.0 amd64 (Git Bash shell)
- `java -version`: OpenJDK `17.0.20.1` (Eclipse Adoptium Temurin-17.0.20.1+1)
- `javac -version`: `17.0.20.1`
- `JAVA_HOME`: not set in the shell; the verified JDK path was supplied explicitly:
  `C:\Program Files\Eclipse Adoptium\jdk-17.0.20.101-hotspot`
- `_JAVA_OPTIONS=-Xmx4g` was supplied to the build (Gradle logged `Picked up _JAVA_OPTIONS: -Xmx4g`).

Result: **PASS**

### 1.2 Android SDK

- `ANDROID_HOME` / `ANDROID_SDK_ROOT`: not set in the shell; supplied explicitly as `C:\Android\sdk`.
- SDK contents relevant to the build:
  - `platforms/android-36`: present
  - `build-tools/36.0.0`: present (`aapt2`, `apksigner`, `zipalign` verified)
  - `build-tools/35.0.0`: present
  - `platform-tools/adb.exe`: present
  - `cmdline-tools/latest`: present
  - `emulator`: present
  - `system-images/android-34`, `system-images/android-36`: present
- `aapt2 version`: Android Asset Packaging Tool 2.20-13193326
- ADB: Android Debug Bridge 1.0.41, Version 37.0.1-15733141

Result: **PASS**

### 1.3 Gradle wrapper and plugin compatibility

- Wrapper distribution: Gradle `9.7.1` (`android/gradle/wrapper/gradle-wrapper.properties`)
- Cached distribution present under `~/.gradle/wrapper/dists/gradle-9.7.1-bin/`
- `./gradlew.bat --version` exit code `0`, wall time `5s`
- Launcher JVM: `17.0.20.1` (Eclipse Adoptium 17.0.20.1+1)
- Android Gradle Plugin: `8.9.1`
- Kotlin: `2.2.20`; Compose plugin `2.2.20`; Hilt `2.57.2`
- Build emitted a Gradle deprecation notice: deprecated features make the build incompatible with
  Gradle 10. This does not affect the current build, but is a future upgrade item.

Result: **PASS (empirically verified by a successful build; no separate formal
AGP-to-Gradle compatibility matrix check was run)**

### 1.4 Android module / debug configuration

- `applicationId`: `com.nexhaat.app`
- `namespace`: `com.nexhaat.app`
- `compileSdk`: 36
- `minSdk`: 24
- `targetSdk`: 36
- `versionCode`: 1
- `versionName`: `1.0.0`
- `debug` build type: no custom signing config; Gradle default debug signing applies
  (`:app:validateSigningDebug` is part of the graph)
- Debug base URL: `NEXHAAT_DEBUG_BASE_URL` falling back to `http://10.0.2.2:5000/`
- Debug media URL: explicit `NEXHAAT_MEDIA_BASE_URL` when valid, otherwise the debug base URL
- Release signing block requires `NEXHAAT_KEYSTORE_PATH`, `NEXHAAT_KEYSTORE_STORE_PASSWORD`,
  `NEXHAAT_KEYSTORE_KEY_ALIAS`, `NEXHAAT_KEYSTORE_KEY_PASSWORD`; none were configured or set.

Preflight finding (not a blocker):

- `android/local.properties` does not exist. The Gradle config reads that file from the root
  project directory, so the newer untracked `android/app/local.properties.debug`
  (`NEXHAAT_DEBUG_BASE_URL=http://10.0.2.2:5000/`) is not consumed by this build. The resulting
  debug base URL is nevertheless the same default value. The file was left untouched.

### 1.5 Existing Debug APK and checksum (pre-build)

- Path: `android/app/build/outputs/apk/debug/app-debug.apk`
- Size: `21,884,019` bytes
- SHA-256: `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c`
- Last modified: `2026-11-06 19:30:37`
- `output-metadata.json` (pre-build): `variantName: "debug"`, `applicationId: "com.nexhaat.app"`,
  `versionCode: 1`, `versionName: "1.0.0"`, `outputFile: "app-debug.apk"`

The missing/absent-artifact condition was not assumed: a valid existing Gradle debug output was
present before the build.

### 1.6 Git working tree (pre-build)

- Branch: `main`
- HEAD: `ac6636afd54a7f91002604b6ae160d7d6f791972`
- `origin/main...HEAD`: `0 0`
- Working tree: dirty, **57** porcelain entries, no unmerged files (`git ls-files -u` empty)
- Existing user modifications included (non-exhaustive):
  - staged: `.env.example`, `AuthRepository.kt`, `gradlew`/`gradlew.bat` mode changes,
    `app/api/routes/auth.py`, `app/api/serializers.py`, `app/models/security.py`,
    `app/routes/auth.py`, `app/services/two_factor.py`, `app/services/two_factor_crypto.py`,
    `tests/test_auth_two_factor.py`, `WEBSITE_ANDROID_FEATURE_PARITY.md`
  - unstaged: `server.ts`, `FlaskAuthPanel.tsx`, `PWAInstallButton.tsx`,
    `apkDownloadService.ts`, `generate_apk_package.py`, `package-lock.json`, Gradle cache files
  - untracked: `APK/`, `.temp_recovery/`, prior Phase 2.x reports, QA scripts/tests,
    `android/app/local.properties.debug`, `android/build-debug-nohup.out`,
    `android/gradlew-build.pid`, `android/system-images;android-36;google_apis;x86_64/`

All pre-existing modifications were preserved. Nothing was reset, cleaned, stashed, or deleted.

Result: **PASS**

---

## 2. Gradle Debug build command and exit status

- Working directory: `android/`
- Command:

```bash
./gradlew.bat :app:assembleDebug --no-daemon --console=plain
```

- Environment:
  - `JAVA_HOME=C:/Program Files/Eclipse Adoptium/jdk-17.0.20.101-hotspot`
  - `ANDROID_HOME=C:/Android/sdk`
  - `ANDROID_SDK_ROOT=C:/Android/sdk`
  - `_JAVA_OPTIONS=-Xmx4g`
- Execution bound: 600 seconds (`timeout 600`)
- **Actual exit code: `0`**
- Gradle result line: `BUILD SUCCESSFUL in 1m 15s`
- Task summary: `42 actionable tasks: 42 up-to-date`
- No dependency/network resolution failure appeared in the log.
- No retry loop was entered.

Build log (outside the repository, Git Bash temporary path):

- `/tmp/nexhaat-phase3-assembleDebug.log`

Result: **PASS**

---

## 3. Build duration

- Wall-clock duration of the successful command: **76 seconds**
- Gradle-reported duration: **1m 15s**
- All 42 tasks were reported up-to-date; the duration is mostly configuration/JVM overhead.

---

## 4. Fresh-build caveat and forced verification attempt

Because the required build reported all tasks up-to-date, one bounded verification rebuild was
attempted with the same task and wrapper:

```bash
./gradlew.bat :app:assembleDebug --rerun-tasks --no-daemon --console=plain
```

Observed result:

- The command exceeded the **600-second** tool execution bound and was terminated.
- Last completed tasks in the log included `:app:kaptDebugKotlin`, `:app:compileDebugKotlin`,
  `:app:compileDebugJavaWithJavac`, `:app:hiltJavaCompileDebug`, `:app:dexBuilderDebug`, and
  `:app:mergeDebugGlobalSynthetics`.
- The log ends with:
  `The message received from the daemon indicates that the daemon has disappeared.`
- No `BUILD SUCCESSFUL` or `BUILD FAILED` line was produced for this forced run.
- No `java.exe` processes remained afterward.
- `:app:packageDebug` did not complete, so the forced run did **not** produce a replacement APK.
- The existing `app-debug.apk` remained present, unchanged in size, mtime, and SHA-256.
- No partially written APK was found in `android/app/build/outputs/`.

Classification: **TIMEOUT / INCONCLUSIVE** — not a build failure and not a rebuild success. Per the
mission's timeout rule, no further Gradle attempt was made. The validated APK is therefore the
existing Gradle debug artifact that the successful `assembleDebug` invocation confirmed as
up-to-date for the current inputs.

Log:

- `/tmp/nexhaat-phase3-assembleDebug-forced.log`

---

## 5. APK verification

### 5.1 Path and existence

- Required path: `android/app/build/outputs/apk/debug/app-debug.apk`
- Absolute path verified from the shell: `D:\FTP\NexHaat\android\app\build\outputs\apk\debug\app-debug.apk`
- Exists: **YES**
- Non-empty: **YES**
- Size: **21,884,019 bytes** (20.87 MiB)
- Last modified: `2026-11-06 19:30:37` (unchanged by this phase)
- SHA-256: **`f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c`**

### 5.2 Structure and identity

- ZIP/APK integrity (`unzip -t`): `No errors detected in compressed data of app-debug.apk`
- Package: **`com.nexhaat.app`**
- Version name: **`1.0.0`**
- Version code: **`1`**
- compileSdk: `36` (platformBuildVersionName `16`, platformBuildVersionCode `36`)
- minSdk: `24`
- targetSdk: `36`
- Manifest `android:debuggable`: `true`
- DEX files: **18** (`classes.dex` through `classes18.dex`)
- `output-metadata.json`: `variantName: "debug"`, `applicationId: "com.nexhaat.app"`,
  `versionCode: 1`, `versionName: "1.0.0"`, `outputFile: "app-debug.apk"`

Note: Section 4 of the request literally says "Package ID equals `com.nexhaat`". The actual and
declared package, consistent with the mission header and Gradle config, is
**`com.nexhaat.app`**. No package change was made.

Result: **PASS**

### 5.3 Debug signature

Command: `apksigner verify --verbose --print-certs app-debug.apk`

```text
Verifies
Verified using v1 scheme (JAR signing): false
Verified using v2 scheme (APK Signature Scheme v2): true
Verified using v3 scheme (APK Signature Scheme v3): false
Verified using v3.1 scheme (APK Signature Scheme v3.1): false
Verified using v4 scheme (APK Signature Scheme v4): false
Verified for SourceStamp: false
Number of signers: 1
Signer #1 certificate DN: C=US, O=Android, CN=Android Debug
Signer #1 certificate SHA-256 digest: bf0f1062326482e342ddf4222285614b9cecf92eb743074acd1bba87d32b26e4
Signer #1 key algorithm: RSA
Signer #1 key size (bits): 2048
```

Result: **PASS (debug certificate only; not a production release signature)**

### 5.4 Verification summary

| Check | Result |
|---|---|
| APK exists and is non-empty | PASS |
| Valid ZIP/APK structure | PASS |
| Package `com.nexhaat.app` | PASS |
| Version name `1.0.0`, version code `1` | PASS |
| DEX files present (18) | PASS |
| Debug signature verifies | PASS |
| SHA-256 computed from actual APK | PASS |
| Exact Gradle debug output path | PASS |
| Debug manifest flag `debuggable=true` | PASS |

---

## 6. Installation readiness

### 6.1 ADB

- ADB found at `C:\Android\sdk\platform-tools\adb.exe`
- Version: 1.0.41 / 37.0.1-15733141
- `adb devices -l` output: `List of devices attached` followed by no devices.

### 6.2 Emulator state

- An AVD definition exists (`~/.android/avd/nexhaat-test-avd.ini`).
- No `emulator.exe` or `qemu-system-x86_64.exe` process was running.
- No emulator was launched, per the restriction against automatic cold boot.

### 6.3 Installation and smoke test

- Installation attempted: **NO**
- Installation result: **BLOCKED — no connected device or running emulator**
- App launch: **NOT RUN**
- Startup/crash-log inspection: **NOT RUN**
- Basic smoke tests (startup, home, catalog, product detail, login): **NOT RUN**
- No application data, package state, or device state was modified.

Result: **DEBUG_INSTALL: BLOCKED**

---

## 7. Stable/Debug separation verification

| Check | Result | Evidence |
|---|---|---|
| `APK/NexHaat.apk` created or replaced | **NO** | Path does not exist |
| `APK/latest.json` remains unavailable/unverified | **PASS** | `buildType: "none"`, `verified: false`, `sha256: ""`, `status: "unavailable"`, `artifactPath: "APK/NexHaat.apk"` |
| `public/downloads/metadata.json` remains unavailable/unverified | **PASS** | Same content as `APK/latest.json` |
| Metadata files unchanged by this phase | **PASS** | Both SHA-256 `e36220e24b6a1e065ef76d877d0cc66753bca48ed6e74e7c6b64b40c5308782f`; mtimes `2026-11-06 21:59` |
| Get App does not select Debug APK | **PASS** | `server.ts` candidates are `APK/NexHaat.apk`, `APK/latest.apk`, `public/downloads/nexhaat.apk` only; no debug path |
| Debug path referenced by serving/packaging code | **NONE** | Grep for `app-debug`, `outputs/apk/debug`, `debug/latest` in `server.ts`, `generate_apk_package.py`, `apkDownloadService.ts`, `PWAInstallButton.tsx` returned no matches |
| Get App availability gate | **PASS** | `PWAInstallButton.tsx`: `apkMetadata?.exists && apkMetadata?.verified` |
| Public downloads directory contains only metadata | **PASS** | `public/downloads/` contains only `metadata.json` |
| Production signing configuration touched | **NO** | `git diff` empty for `android/app/build.gradle.kts`, `android/build.gradle.kts`, `android/gradle.properties`; no signing env vars supplied |
| APK placed in root `APK/` | **NO** | `APK/` contains only `checksums.txt`, `latest.json`, `status.json` |
| APK renamed to `NexHaat.apk` | **NO** | Artifact remains `app-debug.apk` |

Result: **PASS — Stable and Debug remain separated; Get App remains unavailable.**

---

## 8. Git working-tree status at completion

- Branch: `main`
- HEAD: `ac6636afd54a7f91002604b6ae160d7d6f791972`
- `origin/main...HEAD`: `0 0`
- Porcelain entries before this phase: **57**
- Porcelain entries after builds and before adding this report: **57** (no new source/build-output
  changes attributable to this phase; build regenerated ignored/intermediate outputs and touched
  already-modified tracked Gradle cache files)
- Unmerged files: none
- `git diff --check`: exit `0`; one pre-existing CRLF warning on
  `android/.gradle/buildOutputCleanup/cache.properties`
- New file from this phase: `docs/APK_RELEASE_PHASE3_0_DEBUG_RECOVERY_REPORT.md` (untracked)
- `APK/` and `public/downloads/` remain untracked as before
- No commit, push, merge, rebase, reset, clean, stash, or deployment was performed

---

## 9. Errors and remaining blockers

### 9.1 Errors and notable build output

1. **Forced verification rebuild timed out at 600 seconds.**
   - Gradle log ended with daemon disappearance while dexing.
   - No build success/failure verdict was produced for that run.
   - The pre-existing debug APK was not replaced or damaged.
   - No retry was attempted, per the mission's timeout rule.

2. **Gradle deprecation notice:** the build uses deprecated features and will be incompatible with
   Gradle 10. Current Gradle 9.7.1 build succeeds. This was not changed.

3. **Kotlin compiler warnings** (non-fatal), including:
   - annotation-target warnings in `BiometricPromptHelper.kt`, `BiometricStorage.kt`
   - deprecated `KeyGenParameterSpec` API in `BiometricSessionCrypto.kt`
   - deprecated `Locale` constructors in `CartScreen.kt` and `ProductDetailScreen.kt`
   - deprecated auto-mirrored icons in `PortalsScreen.kt`
   - deprecated status/navigation bar colors in `Theme.kt`

4. **ADB path resolution:** plain `adb` was not on the shell PATH; it was invoked from
   `C:\Android\sdk\platform-tools`. This is an environment setup issue, not an application defect.

5. **`android/local.properties` absent:** the debug base URL therefore used its default
   (`http://10.0.2.2:5000/`); the untracked `android/app/local.properties.debug` is not read by the
   current Gradle config.

### 9.2 Remaining blockers

- **Device installation and smoke testing:** BLOCKED — no physical device and no running emulator.
- **Stable release:** `APK/NexHaat.apk` absent; production signing not configured.
- **Get App:** UNAVAILABLE — no verified Stable artifact exists.
- **Fresh rebuild evidence:** the required `assembleDebug` succeeded with all tasks up-to-date; the
  forced `--rerun-tasks` verification did not complete within the 600-second bound.

### 9.3 Checks not run

- Installation, launch, crash-log inspection, and UI smoke tests (no device).
- Emulator cold boot (explicitly prohibited).
- Stable/release build and production signing.
- Live HTTP verification of the Get App download endpoint.
- Full forced rebuild to packaging completion (timed out; not retried).

---

## 10. Required output summary

| Item | Value |
|---|---|
| Build command | `./gradlew.bat :app:assembleDebug --no-daemon --console=plain` |
| Build exit status | `0` |
| Build duration | 76s wall / `BUILD SUCCESSFUL in 1m 15s` |
| APK path | `android/app/build/outputs/apk/debug/app-debug.apk` |
| APK size | `21,884,019` bytes |
| Package | `com.nexhaat.app` |
| Version | `1.0.0` (versionCode `1`) |
| SHA-256 | `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c` |
| Signature | APK Signature Scheme v2; `CN=Android Debug`; verifies |
| DEX | 18 files, `classes.dex`–`classes18.dex` |
| ADB | Available (1.0.41 / 37.0.1) |
| Devices | None |
| Installation | BLOCKED |
| Smoke test | NOT RUN |
| Git commit/push/deploy | None |
| Stable APK | NOT_RELEASED |
| Get App | UNAVAILABLE |

---

## 11. Report file

`docs/APK_RELEASE_PHASE3_0_DEBUG_RECOVERY_REPORT.md`
