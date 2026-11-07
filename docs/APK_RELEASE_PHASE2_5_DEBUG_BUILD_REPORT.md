# APK RELEASE — PHASE 2.5 DEBUG BUILD REPORT

Created: 2026-11-06
Workspace: `D:\FTP\NexHaat`
Android root: `android/`
Gradle module: `:app`
Mode: CONTROLLED BUILD — DEBUG ONLY

## 1. Compatibility findings

- JDK: OpenJDK 17.0.20.1 (Temurin) detected at `C:\Program Files\Eclipse Adoptium\jdk-17.0.20.101-hotspot`
- Android Gradle Plugin declared: 8.9.1
- Kotlin declared: 2.2.20
- Gradle wrapper declared: 9.7.1 (`gradle-wrapper.properties`)
- Local Gradle 9.7.1 distribution: found in `GRADLE_USER_HOME/wrapper/dists/gradle-9.7.1-bin/.../gradle-9.7.1` with `bin/gradle(.bat)` and `lib/` present
- AGP/wrapper compatibility: NOT RUN beyond local metadata presence; build was allowed to proceed because wrapper + AGP metadata existed locally and no incompatible error was confirmed before launch
- Android SDK root: `C:\Android\sdk` (used via `ANDROID_HOME`/`ANDROID_SDK_ROOT` in build environment)
- SDK packages used by build:
  - platforms/android-36: present
  - build-tools 36.0.0: present
  - cmdline-tools/latest: present
  - system-images/android-36/google_apis/x86_64: present (not required for this build)
  - system-images/android-36/google_apis/arm64-v8a: MISSING (not required for this build)

Result:
- Compatibility before build: PASS (local toolchain present); important caveat NOT RUN for formal AGP/wrapper compatibility verification

## 2. Actual build command

- Command: `./gradlew.bat :app:assembleDebug --no-daemon --console=plain`
- Working directory: `android/`
- Build environment:
  - `_JAVA_OPTIONS=-Xmx4g`
  - `JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-17.0.20.101-hotspot`
  - `ANDROID_HOME=C:\Android\sdk`
  - `ANDROID_SDK_ROOT=C:\Android\sdk`
  - `PATH` included JDK bin, platform-tools, and emulator

Result: PASS (command recorded)

## 3. Build exit code

- `BUILD SUCCESSFUL`
- Exit code observed from build log: 0
- Build log: `android/build-debug.log`

Result: PASS

## 4. Build duration

- Reported by Gradle: `BUILD SUCCESSFUL in 1m 1s`
- Task summary: `42 actionable tasks: 42 up-to-date`
- Note: first build attempt was run from cached Gradle distribution and reused UP-TO-DATE outputs; duration reflects that run.

Result: PASS

## 5. Actual APK output path

- Source APK produced by Gradle: `android/app/build/outputs/apk/debug/app-debug.apk`
- Saved debug artifact: `APK/debug/latest-debug.apk`
- The saved artifact was copied from the Gradle-generated source APK after validation.
- `APK/latest.apk` was NOT created or replaced.

Result: PASS

## 6. Package and version

From `aapt2 dump badging` on the real APK:
- package name: `com.nexhaat.app`
- versionCode: `1`
- versionName: `1.0.0`

Result: PASS

## 7. Signature verification

From `apksigner verify --verbose` on the real APK:
- Verifies: true
- Verified using v1 scheme (JAR signing): false
- Verified using v2 scheme (APK Signature Scheme v2): true
- Verified using v3 scheme: false
- Verified using v3.1 scheme: false
- Verified using v4 scheme: false
- Verified for SourceStamp: false
- Number of signers: 1
- Signer #1 certificate DN: `C=US, O=Android, CN=Android Debug`
- Signer #1 certificate SHA-256 digest: `bf0f1062326482e342ddf4222285614b9cecf92eb743074acd1bba87d32b26e4`
- Signer #1 certificate SHA-1 digest: `17a7c8e9972cf7419282a47b54dbd2a9a7f0e17e`
- Signer #1 certificate MD5 digest: `07236e4c7f5b328a1f7f2d665029cb1b`

Result: PASS (debug-signed APK verified by `apksigner`)

Note: this is a debug certificate, not a production release key.

## 8. APK size and SHA-256

- File size: 21884019 bytes
- SHA-256: `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c`
- Size/SHA-256 recorded for both:
  - `android/app/build/outputs/apk/debug/app-debug.apk`
  - `APK/debug/latest-debug.apk`

Result: PASS

## 9. APK structure gates

- Valid ZIP/APK archive: PASS (`unzip -t` succeeded)
- Package name `com.nexhaat.app`: PASS (`aapt2 dump badging`)
- Manifest parseable: PASS (badging and manifest dump succeeded)
- DEX files present: PASS
  - `classes.dex` and `classes2.dex` through `classes18.dex` found
- Debug certificate present: PASS (Android Debug signer)

Result: PASS

## 10. Gate summary

| Gate | Result |
|---|---|
| Pre-build safety (no git mutation, project/module confirmed) | PASS |
| Local toolchain presence | PASS |
| Gradle wrapper + AGP metadata present | PASS |
| Formal AGP/wrapper compatibility check | NOT RUN |
| Build command executed | PASS |
| Build exit code 0 / BUILD SUCCESSFUL | PASS |
| Build duration | PASS (1m 1s reported) |
| Real APK exists and is non-empty | PASS |
| Valid ZIP/APK archive | PASS |
| Package name `com.nexhaat.app` | PASS |
| Manifest parseable | PASS |
| DEX files present | PASS |
| APK signature verifies | PASS |
| Version name/version code extracted | PASS |
| APK size + SHA-256 recorded | PASS |
| Artifact saved to `APK/debug/latest-debug.apk` | PASS |
| `APK/latest.apk` not replaced | PASS |
| Production release signing attempted | NOT RUN (not requested) |
| Emulator launched | NOT RUN (not requested) |

## 11. Error log location

- Build log: `android/build-debug.log`
- Wrapper nohup/stderr capture: `android/build-debug-nohup.out`
- No build failure was recorded; log shows `BUILD SUCCESSFUL`.

Result: PASS

## 12. Remaining blockers

For this debug build:
- None for the debug artifact itself.

For release/publication:
- `APK/latest.apk` still MISSING.
- Release signing credentials not configured; release build path remains unsigned/blocked until `NEXHAAT_KEYSTORE_PATH`, `NEXHAAT_KEYSTORE_STORE_PASSWORD`, `NEXHAAT_KEYSTORE_KEY_ALIAS`, `NEXHAAT_KEYSTORE_KEY_PASSWORD` are provided.
- Emulator installation/launch was NOT RUN in this phase.

## Notes

- This report covers only the controlled debug build and artifact validation requested in Phase 2.5.
- No release build, production signing, commit, push, or deployment was performed.
- All existing files were preserved; only new build outputs and the saved debug artifact were added.

## Report file

`docs/APK_RELEASE_PHASE2_5_DEBUG_BUILD_REPORT.md`
