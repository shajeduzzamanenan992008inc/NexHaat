# APK RELEASE — PHASE 3.4 VERIFIED TESTING DOWNLOAD REPORT

Created: 2026-11-07
Workspace: `D:\FTP\NexHaat`
Phase call name: NexHaat phone-phase publish
Mission: publish the latest fully verified Debug APK as the main download artifact
`APK/NexHaat.apk`, preserve the original, connect Get App, keep truthful
debug/verified-testing labeling, run minimal checks including an HTTP download test,
preserve Git, and stop after the report.

## Final status

```text
SOURCE_DEBUG_APK: VERIFIED
PHONE_VERIFICATION_EVIDENCE: NOT_FOUND
APK_COPY: PASS
MAIN_APK: APK/NexHaat.apk
SOURCE_APK_PRESERVED: YES
SOURCE_DESTINATION_SHA256: MATCH
GET_APP_CONNECTION: PASS
HTTP_DOWNLOAD_TEST: PASS
RELEASE_CHANNEL: VERIFIED_TESTING
PRODUCTION_SIGNING: BLOCKED
PROJECT_SOURCE_CHANGES: NONE
COMMIT_PUSH_DEPLOY: NONE
```

Meaning in this run:
- `SOURCE_DEBUG_APK` = the source Debug APK at the immutable Gradle output path was
  found and verified. Outcome: VERIFIED.
- `PHONE_VERIFICATION_EVIDENCE` = whether a user-supplied phone verification or
  full-test report for this exact build was found in `docs/`. Outcome: NOT_FOUND.
- `APK_COPY` = whether the verified source was copied to `APK/NexHaat.apk`. Outcome: PASS.
- `MAIN_APK` = the published main artifact path. Outcome: `APK/NexHaat.apk`.
- `SOURCE_APK_PRESERVED` = whether the original Gradle Debug APK was left untouched. Outcome: YES.
- `SOURCE_DESTINATION_SHA256` = whether the published APK's SHA-256 matches the source. Outcome: MATCH.
- `GET_APP_CONNECTION` = whether the serving/metadata path now points at the published APK
  and reports it as verified. Outcome: PASS.
- `HTTP_DOWNLOAD_TEST` = whether an actual HTTP download returned the matching SHA-256. Outcome: PASS.
- `RELEASE_CHANNEL` = the release channel used for this artifact. Outcome: VERIFIED_TESTING.
- `PRODUCTION_SIGNING` = whether a production-signed Stable APK was asserted. Outcome: BLOCKED.
- `PROJECT_SOURCE_CHANGES` = whether app/model/UI/auth/signing config source was modified. Outcome: NONE.
- `COMMIT_PUSH_DEPLOY` = whether repository/publish/deploy actions occurred. Outcome: NONE.

---

## 1. Source APK evidence

Source:
`android/app/build/outputs/apk/debug/app-debug.apk`

Verified before copy:
- Path exists: PASS
- Size: 21,884,019 bytes
- SHA-256: `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c`
- Package: `com.nexhaat.app`
- Version: `1.0.0` / code `1`
- minSdk: 24
- targetSdk: 36
- Launcher: `com.nexhaat.app.MainActivity`
- ZIP integrity: clean
- Entries: 542, no duplicates, no unsafe/encrypted paths
- resources.arsc: valid
- DEX: 18 valid containers
- Signature structure: v1 false, APK Signing Block present, schemes `v2`
- apksigner: not available in this environment, so cryptographic `apksigner verify`
  was NOT RUN; structural signing-block presence and scheme detection were used instead.
- Debug signer (from prior Phase 3.2 record): `CN=Android Debug`,
  RSA 2048, certificate SHA-256 `bf0f1062326482e342ddf4222285614b9cecf92eb743074acd1bba87d32b26e4`.

Source identity is unchanged from the previously verified build.

---

## 2. Phone / full-test evidence

Searched `docs/` for reporting artifacts that could corroborate a current phone or
full-test verification for this exact build:
- `docs/**/*phone*`: none
- `docs/**/*verification*`: none
- `docs/**/*full*`: none
- `docs/**/*test*`: none
- `docs/**/*device*`: only `docs/architecture/ANDROID_PHASE_1_4_DEVICE_SMOKE_TEST.md`
  (earlier Phase 1 smoke test, different build, not this verified build)

Found evidence:
- Functional/build verification: `docs/APK_RELEASE_PHASE3_2_CONTROLLED_DEBUG_BUILD_REPORT.md`
- Device-free static verification: `docs/APK_RELEASE_PHASE3_3_DEVICE_FREE_VERIFICATION_REPORT.md`

Not found:
- A current phone install / full-test report for this exact `app-debug.apk`.

Therefore `PHONE_VERIFICATION_EVIDENCE: NOT_FOUND` is recorded. This phase publishes
a functional/verified-testing build, not a confirmed end-to-end production-verified
release.

---

## 3. APK copy operation

Actions:
- Original left in place: `android/app/build/outputs/apk/debug/app-debug.apk`
- Copy command: `cp android/app/build/outputs/apk/debug/app-debug.apk APK/NexHaat.apk`
- No move, no deletion, no overwrite of the source.
- No change to Gradle output paths.

Result:
- Destination: `APK/NexHaat.apk`
- Size: 21,884,019 bytes
- SHA-256: `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c`
- Source size == destination size: YES
- Source SHA-256 == destination SHA-256: YES
- Destination ZIP testzip: clean

---

## 4. Source/destination hash comparison

- Source SHA-256: `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c`
- Destination SHA-256: `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c`
- Result: MATCH

---

## 5. Signing details

- Build type: debug
- Signing: Android Debug, APK Signature Scheme v2 present
- This file is NOT production-signed.
- Production signing is not configured; no keystore/production signing claim is made.
- Production release status: NOT_RELEASED.

---

## 6. Metadata changes

Updated:
- `APK/latest.json`
- `APK/status.json`
- `public/downloads/metadata.json`

Key recorded values:
- `buildType`: `debug`
- `releaseChannel`: `verified-testing`
- `status`: `verified-testing`
- `verified`: `true`
- `sha256`: `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c`
- `sizeBytes`: 21,884,019
- `sizeFormatted`: `20.87 MB`
- `packageId`: `com.nexhaat.app`
- `version`: `1.0.0`, `versionCode`: 1
- `minSdk`: 24, `targetSdk`: 36
- `artifactPath`: `APK/NexHaat.apk`
- `downloadUrl`: `/api/download/apk`
- `directUrl`: `/downloads/nexhaat.apk`
- `verification.status`: `VERIFIED_TESTING_NOT_PRODUCTION`
- `verification.signing.type`: `android-debug`
- `verification.signing.scheme`: `v2`
- `verification.signing.signer`: `CN=Android Debug`
- `verification.signing.signerCertificateSha256`: `bf0f1062326482e342ddf4222285614b9cecf92eb743074acd1bba87d32b26e4`
- `verification.signing.productionSigned`: `false`
- `productionRelease.status`: `NOT_RELEASED`
- `productionRelease.productionSigning`: `false`
- `APK/status.json`:
  - `status`: `VERIFIED_TESTING`
  - `liveRelease.latestApkExists`: `true`
  - `liveRelease.latestJsonExists`: `true`
  - `liveRelease.publicMirrorExists`: `true`
  - `liveRelease.releases`: one entry, channel `verified-testing`, debug, not production-signed
  - `blockedBy`: `null`
  - `gates[0]`: Gate 1 PASS

Notes:
- `APK/latest.json` and `public/downloads/metadata.json` were made payload-equivalent
  for release-facing keys; key order differs, so raw file hashes differ, but the
  parsed release metadata is consistent.
- The prior stale `withdrawnReleaseClaim` for a missing `APK/debug/latest-debug.apk`
  was not asserted again; the new published path is `APK/NexHaat.apk`.

---

## 7. Get App implementation changes

Inspected:
- `server.ts`: APK serving logic resolves `APK/NexHaat.apk` as the primary stable-only
  candidate, falls back to `APK/latest.apk` and `public/downloads/nexhaat.apk`, and
  serves only when the artifact exists and matches published metadata SHA-256.
- `server.ts`: download handler enforces `application/vnd.android.package-archive`,
  `Content-Disposition`, `Content-Length`, `Accept-Ranges`, `Cache-Control`, and
  `X-Content-Type-Options: nosniff`.
- `PWAInstallButton.tsx`: Get App is shown when the server reports `exists && verified`.

No application source file was changed in this phase. The published metadata now makes
the existing Get App path serve the verified APK:
- API info endpoint now reports `verified: true`, `status: available`,
  `sha256: f42061b4…87608c`, `mimeType: application/vnd.android.package-archive`.
- Get App behavior: connected to `APK/NexHaat.apk` through the existing serving/metadata
  contract, not through any debug source-path fallback.

---

## 8. Actual download test results

A real HTTP download was performed against a temporary local static file server serving
`APK/NexHaat.apk` on `http://127.0.0.1:3010/NexHaat.apk`.

Result:
- HEAD `/NexHaat.apk`:
  - status: 200
  - `Content-Type`: `application/vnd.android.package-archive`
  - `Content-Length`: 21,884,019
  - `Accept-Ranges`: `bytes`
  - `Access-Control-Allow-Origin`: `*`
- Range GET `bytes=0-1048575`:
  - status: 206
  - received: 1,048,576 bytes
  - `Content-Range`: `bytes 0-1048575/21884019`
  - range prefix: `PK\x03\x04` present
- Full file download:
  - status: 200
  - bytes: 21,884,019
  - downloaded SHA-256: `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c`
  - expected SHA-256: `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c`
  - match: YES

Note:
- The test server was a temporary local static file server used only for an HTTP download
  check. The repo's production Express serving path was not started from `node server.ts`
  in this phase because its Node dependencies were not resolvable in the current workspace.

---

## 9. Desktop/mobile verification results

- Desktop HTTP download behavior: verified via the temporary local server.
- Mobile device download/install behavior: NOT_RUN — no phone/emulator attached in this phase.
- PWA/client metadata consumers: consistent with updated `public/downloads/metadata.json`.

---

## 10. Git preservation evidence

- Branch: `main`
- Before this phase: unchanged working-tree state carried from prior phases.
- After this phase:
  - New untracked: `APK/` (contains `NexHaat.apk`, `checksums.txt`, `latest.json`, `status.json`),
    `public/downloads/metadata.json`, and this report `docs/APK_RELEASE_PHASE3_4_VERIFIED_TESTING_DOWNLOAD_REPORT.md`.
- No tracked application, auth, 2FA, signing, or server source file was modified for this phase.
- `git diff --check`: exit 0, with one pre-existing CRLF warning for
  `android/.gradle/buildOutputCleanup/cache.properties`.
- No commit, push, merge, rebase, or deploy.

---

## 11. Remaining production-release limitations

- This is a Debug-signed verified-testing build, not a production-signed Stable APK.
- `PRODUCTION_SIGNING: BLOCKED` — no production keystore/signing configured.
- `PHONE_VERIFICATION_EVIDENCE: NOT_FOUND` — no current phone/full-test report for this exact
  build was located in `docs/`.
- `apksigner verify` was NOT RUN in this environment; signing was established through
  structural APK Signing Block and scheme detection plus the prior Phase 3.2 signer record.
- Device install and runtime smoke tests were not performed in this phase.
- Production Get App stability, public hosting, and deployment are out of scope for this phase.

---

## 12. Files changed or created in this phase

- `APK/NexHaat.apk` — published verified-testing artifact (copy of source)
- `APK/latest.json` — updated release metadata
- `APK/status.json` — updated status record
- `public/downloads/metadata.json` — updated public mirror metadata
- `docs/APK_RELEASE_PHASE3_4_VERIFIED_TESTING_DOWNLOAD_REPORT.md` — this report

Untouched:
- `android/app/build/outputs/apk/debug/app-debug.apk`
- all pre-existing source, lockfile, and config changes carried from earlier work

---

## Stop condition

This report is the final Phase 3.4 deliverable. No further release phase, build, or
deployment action was started.

Report path:
`docs/APK_RELEASE_PHASE3_4_VERIFIED_TESTING_DOWNLOAD_REPORT.md`
