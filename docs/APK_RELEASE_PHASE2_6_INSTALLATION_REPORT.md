# APK RELEASE — PHASE 2.6 INSTALLATION & SMOKE TEST REPORT

Created: 2026-11-06
Workspace: `D:\FTP\NexHaat`
APK: `APK/debug/latest-debug.apk`
Package: `com.nexhaat.app`
Mode: CONTROLLED ANDROID VALIDATION

## 1. APK artifact verification

- APK present: YES
- APK size: 21884019 bytes
- APK SHA-256: `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c`
- SHA-256 matches Phase 2.5 report: YES
- Package name: `com.nexhaat.app`
- Version code: 1
- Version name: 1.0.0
- Signature verification: `apksigner verify` ran, but its output was not captured in this phase's artifact verification run; APK identity/SHA-256 was verified directly and matches the Phase 2.5 validated artifact.

Result:
- Artifact verified against Phase 2.5: PASS
- apksigner output capture: NOT RUN in this phase

## 2. ADB device discovery

- ADB present: YES
- ADB version: Android Debug Bridge version 1.0.41, Version 37.0.1-15733141
- Command: `adb devices -l`
- Output: `List of devices attached` with no devices listed

Result:
- Device discovery: FAIL (no devices/emulators detected)
- Device details: NOT RUN (no device available)
- Android version/SDK: NOT RUN
- Architecture: NOT RUN
- Storage: NOT RUN

## 3. Installation test

- Installation attempted: NO
- Installation result: BLOCKED
- Blocker: no Android device or emulator detected by ADB
- Package conflict check: NOT RUN
- Signing conflict check: NOT RUN
- Existing app data affected: NO (no install attempted)

Result:
- Installation: BLOCKED

## 4. Startup test

- Application launch attempted: NO
- Startup result: NOT RUN
- Crash log inspection: NOT RUN
- Main screen verification: NOT RUN

Result:
- Startup test: NOT RUN

## 5. Basic smoke test

- App startup: NOT RUN
- Main navigation: NOT RUN
- Home screen: NOT RUN
- Product listing screen: NOT RUN
- Product details screen: NOT RUN
- Login screen visibility: NOT RUN

Result:
- Smoke test: NOT RUN

## 6. Status summary

| Check | Result |
|---|---|
| APK exists | PASS |
| APK SHA-256 matches Phase 2.5 | PASS |
| Package is `com.nexhaat.app` | PASS |
| Signature verification | NOT RUN (identity verified via SHA-256 match) |
| ADB device discovery | FAIL (no devices) |
| Device model | NOT RUN |
| Android version/SDK | NOT RUN |
| Architecture | NOT RUN |
| Storage | NOT RUN |
| Installation result | BLOCKED |
| Launch result | NOT RUN |
| Crash log findings | NOT RUN |
| App startup smoke | NOT RUN |
| Main navigation smoke | NOT RUN |
| Home screen smoke | NOT RUN |
| Product listing smoke | NOT RUN |
| Product details smoke | NOT RUN |
| Login screen visibility smoke | NOT RUN |
| Production data modified | NO |
| Release APK created | NO |
| `APK/latest.apk` replaced | NO |
| Git state changed | NO |

## Remaining blockers

- No Android device or emulator is currently visible to ADB.
- As a result, installation, launch, crash-log inspection, and smoke tests could not be performed in this phase.
- `APK/debug/latest-debug.apk` is verified and preserved.
- `APK/latest.apk` is still absent.

## Safety

- No production data was modified.
- No release APK was created.
- `APK/latest.apk` was not replaced.
- No user app data was deleted.
- Git state was not changed.
- No commit, push, or deployment was performed.
- No fabricated test evidence was produced.

## Report file

`docs/APK_RELEASE_PHASE2_6_INSTALLATION_REPORT.md`
