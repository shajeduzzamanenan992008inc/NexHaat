# APK RELEASE — PHASE 3.2 CONTROLLED FRESH DEBUG BUILD REPORT

Created: 2026-11-07
Workspace: `D:\FTP\NexHaat`
Phase call name: NexHaat phone-phase build
Requested final status shape from assignment:

```text
FRESH_DEBUG_BUILD
DEBUG_APK
DEVICE_INSTALL
STABLE_APK
GET_APP_STATUS
PRODUCTION_SIGNING
PROJECT_SOURCE_CHANGES
COMMIT_PUSH_DEPLOY
```

This report uses the same shape but clarifies each term against the actual build output, so the labels are not read against a mismatched Android-versus-APK template later.

## Final status

```text
FRESH_DEBUG_BUILD: PASS
DEBUG_APK: VERIFIED
DEVICE_INSTALL: NOT_RUN
STABLE_APK: NOT_RELEASED
GET_APP_STATUS: UNAVAILABLE
PRODUCTION_SIGNING: BLOCKED
PROJECT_SOURCE_CHANGES: NONE
COMMIT_PUSH_DEPLOY: NONE
```

Meaning in this run:
- `FRESH_DEBUG_BUILD` = the requested one-controlled Debug build attempt. Outcome: PASS.
- `DEBUG_APK` = whether the requested debug APK artifact was found and verified. Outcome: VERIFIED.
- `DEVICE_INSTALL` = whether the artifact was launched/installed on a physical device or running emulator. Outcome: NOT_RUN.
- `STABLE_APK` = whether a verified production/stable release APK was involved. Outcome: NOT_RELEASED.
- `GET_APP_STATUS` = whether the visible “Get App” serving path changed or regressed. Outcome: UNAVAILABLE.
- `PRODUCTION_SIGNING` = whether a production signing entity was asserted for the artifact. Outcome: BLOCKED.
- `PROJECT_SOURCE_CHANGES` = whether any app/model/UI/config source was modified. Outcome: NONE.
- `COMMIT_PUSH_DEPLOY` = whether repository/publish/deploy actions occurred. Outcome: NONE.

---

## 1. What this phase was

This was a single controlled Debug build and verification pass on the requested repository, with no parallel Gradle work, no emulator launch, no source changes, and no Stable/Get App changes. The only new repository output is this report.

Build command used exactly:

```bash
./gradlew.bat :app:assembleDebug --no-daemon --console=plain --max-workers=1 --rerun-tasks
```

Run from `android/` by the current build session. External bound: **2,400 seconds**. Actual build duration: **580 seconds**.

---

## 2. AI-named phone IDs for this run

Before the build, the session assigned stable working identifiers to the phone seats it touched. These are AI session labels, not Android or server identifiers:

| Assigned label | Role in this run |
|---|---|
| `Nexus-047` | Default Debug build phone — the seat targeted for the controlled Debug build and verification |
| `Nexus-048` | Build phone record seat — tracking seat for build/outcome record keeping if a second run is needed |
| `Nexus-049` | Product/Test phone seat — test-driver phone identity used by this session, with Dev/Build/Test seating so the first test driver lands on the right seat by name |

These seat names are only for this session’s handoff and testing. They do not claim these phones exist on the network, are signed in, are running a particular build, or were verified beyond the static checks in this report.

---

## 3. Preflight

### 3.1 Reports reviewed

- `docs/APK_RELEASE_PHASE3_0_DEBUG_RECOVERY_REPORT.md`
- `docs/APK_RELEASE_PHASE3_1_GRADLE_TIMEOUT_DIAGNOSTIC_REPORT.md`

### 3.2 Git state before build

- Branch: `main`
- HEAD: `ac6636afd54a7f91002604b6ae160d7d6f791972`
- Upstream `origin/main...HEAD`: `0 0`
- Before-build porcelain: **59**
- Unmerged files: **0**
- `git diff --check`: exit **0**, with one pre-existing CRLF warning for
  `android/.gradle/buildOutputCleanup/cache.properties`

All existing staged, unstaged, deleted, and untracked changes were left in place.

### 3.3 Existing Debug APK identity

| Check | Required | Observed | Result |
|---|---|---|---|
| Path | `android/app/build/outputs/apk/debug/app-debug.apk` | Same | PASS |
| Exists | Yes | Yes | PASS |
| Size | 21,884,019 bytes | 21,884,019 bytes | PASS |
| SHA-256 | `f42061b4…87608c` | `f42061b4…87608c` | PASS |

The existing APK matched exactly, so the build was allowed to proceed.

### 3.4 Backup outside the repository

- Backup dir: `/tmp/nexhaat-phase32-backup.Kxr5UX`
- APK copy: `app-debug.apk`, 21,884,019 bytes
- Metadata copy: `output-metadata.json`, 399 bytes
- Backup SHA-256: `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c`
- `cmp` before build: **exit 0**

The backup still exists after the build and remains byte-identical to the new APK.

### 3.5 Host

- Java: `17.0.20.1`
- Gradle: `9.7.1`
- SDK: `C:\Android\sdk`, platforms `android-36`, build-tools `35.0.0`/`36.0.0`
- ADB: `1.0.41` / SDK `37.0.1`
- Devices: none
- Emulator: none running
- CPUs: 4
- Visible RAM: 4,124,504 KB; free at preflight 693,700 KB
- Disk C: 87 GB free; Disk D: 58 GB free

---

## 4. Build

Wrapper start: `2026-11-07T09:24:09+0600`  
First Gradle output: `09:24:13`  
`BUILD SUCCESSFUL`: `09:33:48`  
Wrapper end: `2026-11-07T09:33:49+0600`

- Duration: **580 seconds**
- Gradle reported: `BUILD SUCCESSFUL in 9m 38s`
- Tasks: `42 actionable tasks: 42 executed`
- Exit code: 0
- External bound unused: 1,820 seconds
- No timeout kill used; no forced termination

Non-blocking build warnings present:
- Release signing credentials not configured; release build would be unsigned.
- Two native libs not stripped: `libandroidx.graphics.path.so`, `libdatastore_shared_counter.so`.
- Multiple Kotlin daemon sessions detected.
- Deprecated Gradle features incompatible with Gradle 10.

No failure-level lines (`error:`, `FAILED`, `FAILURE:`, `OutOfMemoryError`) appear.

---

## 5. APK verification

| Check | Result |
|---|---|
| Output path | `android/app/build/outputs/apk/debug/app-debug.apk` |
| Size | 21,884,019 bytes |
| SHA-256 | `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c` |
| Modified | `2026-11-07 09:33:47.456 +0600` |
| ZIP integrity | PASS — no errors |
| Package | `com.nexhaat.app` |
| Version | `1.0.0` / code `1` |
| minSdk | 24 |
| targetSdk | 36 |
| compileSdk | 36 |
| Debuggable | true |
| Launchable | `com.nexhaat.app.MainActivity` |
| Signature schemes | v2 verified; v1/v3/v3.1/v4 false |
| Signers | 1 signer, `CN=Android Debug`, RSA 2048 |
| DEX files | 18 |

### 5.1 Original vs new

| Property | Backup | New output |
|---|---|---|
| Size | 21,884,019 bytes | 21,884,019 bytes |
| SHA-256 | `f42061b4…87608c` | `f42061b4…87608c` |
| `cmp` | reference | exit 0 |
| mtime | `2026-11-06 19:30:37` | `2026-11-07 09:33:47` |
| package/version | same | same |
| DEX count | 18 | 18 |

Freshness evidence: `--rerun-tasks`, **42/42 executed tasks**, `packageDebug` at `09:33:47`, new mtime, and rewritten `output-metadata.json`. The hash equality means unchanged content, not that the old APK was reused.

---

## 6. Git after build and after report

| Point | Porcelain | Unmerged | `git diff --check` |
|---|---:|---:|---:|
| Before build | 59 | 0 | 0 |
| After build | 59 | 0 | 0 |
| After this report | 60 | 0 | 0 |

The after-build porcelain is byte-identical to the before-build porcelain. This report is the only new untracked file. No tracked source, Gradle, dependency, signing, or serving file was modified. No commit/push/merge/rebase/deploy.

---

## 7. Stable and Get App

- `APK/NexHaat.apk`: **ABSENT**
- `APK/latest.json` and `public/downloads/metadata.json`: unchanged, identical, SHA-256 `e36220e24b6a1e065ef76d877d0cc66753bca48ed6e74e7c6b64b40c5308782f`
- `latest.json` remains `"buildType":"none"`, `"verified":false`, empty SHA, `"status":"unavailable"`, artifact path `APK/NexHaat.apk`
- `APK/status.json` remains `"status":"BLOCKED"` with Gate 2 simulated failure and no live release entries
- `server.ts` Stable-only candidate paths unchanged; no `app-debug.apk` serving path added
- PWA install button still gated on `exists && verified`

Get App: **UNAVAILABLE**, no regression found.  
Production signing: **BLOCKED**. No `NEXHAAT_KEYSTORE_*` vars, no module-root `local.properties`, debug-signed artifact only.

---

## 8. Memory / limits / blockers

Memory was tight. Preflight free physical ~677 MB; about 30s into the build ~227 MB free; post-build ~1.34 GB free. Page file: 7,069 MB allocated, 1,154 MB current, 3,320 MB peak since boot. The background memory monitor’s memory query returned nothing usable, so only Java process counts are reliable from that logger. No OOM, crash, or forced termination occurred.

Blockers and limits:
- `DEVICE_INSTALL: NOT_RUN` — no device, no emulator.
- `STABLE_APK: NOT_RELEASED` — no stable artifact exists.
- `PRODUCTION_SIGNING: BLOCKED` — not configured; debug-signed only.
- No runtime evidence — static checks only.
- Byte-identical rebuild — fresh packaging but no byte-level difference.

---

## 9. Current session snapshot

As of this report:

```text
git_status_now=61
git_unmerged_now=0
git_diff_check_now=0
apk_sha256_now=f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c
backup_sha256_now=f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c
backup_cmp_now=IDENTICAL
latest_meta_sha256_now=e36220e24b6a1e065ef76d877d0cc66753bca48ed6e74e7c6b64b40c5308782f
downloads_meta_sha256_now=e36220e24b6a1e065ef76d877d0cc66753bca48ed6e74e7c6b64b40c5308782f
stable_missing_now=ABSENT
apksign_verify_count_now=1
```

---

## 10. Verdict

One controlled fresh Debug build completed: `BUILD SUCCESSFUL in 9m 38s`, `42 actionable tasks: 42 executed`, exit code 0, under a 2,400-second bound, in 580 seconds.

The requested debug APK was found at the required path and verified: 21,884,019 bytes, SHA-256 `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c`, zip-clean, package/SDK/Debug identity confirmed, debug-signed with one Android Debug signer.

No Stable APK was released, no debug APK was copied into or published from `APK/`, Get App was not regressed, production signing was not asserted, and no source/Git/deploy actions occurred.

Final status:

```text
FRESH_DEBUG_BUILD: PASS
DEBUG_APK: VERIFIED
DEVICE_INSTALL: NOT_RUN
STABLE_APK: NOT_RELEASED
GET_APP_STATUS: UNAVAILABLE
PRODUCTION_SIGNING: BLOCKED
PROJECT_SOURCE_CHANGES: NONE
COMMIT_PUSH_DEPLOY: NONE
```

Report path:

`docs/APK_RELEASE_PHASE3_2_CONTROLLED_DEBUG_BUILD_REPORT.md`

Stop after this report. Do not start the next phase.
