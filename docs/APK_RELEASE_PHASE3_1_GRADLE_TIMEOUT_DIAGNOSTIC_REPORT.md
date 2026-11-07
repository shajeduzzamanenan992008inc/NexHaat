# APK RELEASE — PHASE 3.1 GRADLE TIMEOUT DIAGNOSTIC REPORT

Created: 2026-11-07
Workspace: `D:\FTP\NexHaat`
Android root: `android/`
Mode: DIAGNOSTIC ONLY — NO BUILD ATTEMPTED

## Final status

```text
TIMEOUT_ROOT_CAUSE: LIKELY
DIAGNOSTIC: PASS
DEBUG_APK: PRESERVED
STABLE_APK: NOT_RELEASED
GET_APP_STATUS: UNAVAILABLE
PROJECT_CHANGES: NONE
```

`TIMEOUT_ROOT_CAUSE: LIKELY` means the evidence strongly supports the stated cause
but does not include direct process-termination telemetry or a build that was allowed
to complete. `DIAGNOSTIC: PASS` means the requested investigation and report were
completed; it does not mean the timeout is fixed or that a fresh build succeeded.

---

## 1. Executive summary

The forced command:

```bash
./gradlew.bat :app:assembleDebug --rerun-tasks --no-daemon --console=plain
```

was terminated by its external **600-second execution bound** while it was still
performing legitimate D8/dex work. The Gradle client observed the daemon connection
drop at the cutoff and printed:

```text
The message received from the daemon indicates that the daemon has disappeared.
```

That message is a **client-side symptom of losing the daemon**, not proof that the
Gradle daemon crashed internally. At the moment of the cutoff:

- The project Dex output directory was being written at
  `08:53:42.845`, `08:53:42.969`, and `08:53:43.283`.
- The client log’s last write was `08:53:43.633`, approximately **0.35 seconds**
  after the last observed DEX file write.
- The forced run had been executing for approximately **9 minutes 40 seconds**
  (589 seconds from build start to log end), not the full 600-second wrapper life.
- No `OutOfMemoryError`, no JVM `hs_err_pid*.log`, no heap dump, and no Windows
  Java/Gradle crash event was found.
- A prior successful build on the same host with the same 2 GiB Gradle daemon heap
  took **24m 12s** and executed 15 tasks; it included one-time Android SDK
  Build-Tools 35 / Platform 36 installation, so it is not a clean cold-build
  benchmark, but it establishes that this host can legitimately spend far longer
  than 600 seconds in a producing build.

Most likely cause: **the 600-second cap was shorter than this forced full rebuild
needed on a 4 GB-RAM / 4-vCPU host; the build was killed mid-dex and the daemon
disappearance followed from that termination.** Low physical memory and the
effective 2 GiB Gradle heap likely slowed the build, but memory exhaustion is not
proven.

No build, emulator launch, installation, cache deletion, or configuration change
was performed in this phase.

---

## 2. Evidence inspected and exact locations

### 2.1 Phase 3.0 report and captured logs

| Evidence | Location | Observed facts |
|---|---|---|
| Phase 3.0 report | `docs/APK_RELEASE_PHASE3_0_DEBUG_RECOVERY_REPORT.md` | `DEBUG_BUILD: PASS` with the up-to-date caveat; forced run timed out; APK preserved |
| Successful client log | `/tmp/nexhaat-phase3-assembleDebug.log` = `C:\Users\Enan\AppData\Local\Temp\nexhaat-phase3-assembleDebug.log` | 3,590 bytes; mtime `2026-11-07 08:41:46.040`; `BUILD SUCCESSFUL in 1m 15s`; 42 up-to-date |
| Forced client log | `/tmp/nexhaat-phase3-assembleDebug-forced.log` = `C:\Users\Enan\AppData\Local\Temp\nexhaat-phase3-assembleDebug-forced.log` | 5,120 bytes; mtime `2026-11-07 08:53:43.633`; last line is daemon disappearance |
| Forced Gradle daemon log | `C:\Users\Enan\.gradle\daemon\9.7.1\daemon-5292.out.log` | 25,386 bytes; 142 lines; PID 5292; mtime `08:51:25`; no normal-stop sequence |
| Successful Gradle daemon log | `C:\Users\Enan\.gradle\daemon\9.7.1\daemon-7644.out.log` | 37,795 bytes; 222 lines; normal stop after `BUILD SUCCESSFUL in 1m 15s` |
| Prior producing build daemon log | `C:\Users\Enan\.gradle\daemon\9.7.1\daemon-12032.out.log` | 1,605,992 bytes; `BUILD SUCCESSFUL in 24m 12s`; 15 executed / 27 up-to-date |
| Kotlin daemon session marker | `C:\Users\Enan\AppData\Local\kotlin\daemon\kotlin-daemon.2026-11-07T02-46-03.444Z.2b3d8562b2f7db9b29b0a72d34f46ca2.17703.run` | 0 bytes; mtime `08:46:03`; no readable Kotlin daemon log |
| Build intermediates | `android/app/build/intermediates/...` | Active DEX and class output timestamps through `08:53:43` |
| Windows event logs | Application and System logs via `wevtutil` | No Java/Gradle crash or unexpected-shutdown event in the forced-build window |

### 2.2 Configuration files inspected (read-only)

- `android/gradle.properties`
- `android/build.gradle.kts`
- `android/app/build.gradle.kts`
- `android/settings.gradle.kts`
- `android/gradle/wrapper/gradle-wrapper.properties`
- `android/app/local.properties.debug` (untracked; base-URL only)
- Global Gradle properties/init scripts: **absent**
  (`C:\Users\Enan\.gradle\gradle.properties`, `init.gradle`, `init.gradle.kts`,
  `init.d/`)

### 2.3 Release-separation files inspected

- `APK/latest.json`
- `public/downloads/metadata.json`
- `server.ts` (Stable-only candidate paths, lines 875–894)
- `src/components/PWAInstallButton.tsx` (availability gate, line 23)
- `scripts/generate_apk_package.py`
- `src/services/apkDownloadService.ts`
- `android/app/build/outputs/apk/debug/app-debug.apk`

---

## 3. Timeline of the Phase 3.0 timeout

All times are local (`+0600`).

| Time | Event |
|---|---|
| `2026-11-06 19:06:38` | Prior producing build starts on daemon-12032 with `Starting build in new daemon [memory: 2 GiB]` |
| `2026-11-06 19:30:37` | Current Debug APK written (`app-debug.apk`) |
| `2026-11-06 19:30:44` | Prior build reports `BUILD SUCCESSFUL in 24m 12s`; 15 executed, 27 up-to-date |
| `2026-11-07 08:40:39` | Successful Phase 3.0 daemon-7644 starts |
| `2026-11-07 08:40:41` | Normal `assembleDebug` build starts |
| `2026-11-07 08:41:46` | Normal build reports `BUILD SUCCESSFUL in 1m 15s`; 42 up-to-date; daemon stops normally |
| `2026-11-07 08:43:43` | Inferred start of the 600-second forced command (`08:53:43` minus 600s) |
| `2026-11-07 08:43:52.190` | Forced single-use daemon-5292 starts with `-Xmx2048m` |
| `2026-11-07 08:43:54.132` | Forced build request received (`Build{id=f3bc600a-b752-475a-9a25-1941ac61a303}`) |
| `2026-11-07 08:45:17.790` | `manifest-merger-debug-report.txt` written |
| `2026-11-07 08:45` | `mergeLibDexDebug` directory created |
| `2026-11-07 08:46:03.458` | Kotlin daemon session marker created |
| `2026-11-07 08:46:32–37` | External-library DEX files written (`mergeExtDexDebug`) |
| `2026-11-07 08:49` | Kotlin daemon directory last modified |
| `2026-11-07 08:51:25.631` | Last write to daemon-5292 log (compiler warnings) |
| `2026-11-07 08:51` | `javac` classes and `tmp/kotlin-classes/debug` last modified |
| `2026-11-07 08:52` | `dex_archive_input_jar_hashes` last modified |
| `2026-11-07 08:53:42.845` | `mergeProjectDexDebug/0/classes.dex` written |
| `2026-11-07 08:53:42.969` | `mergeProjectDexDebug/3/classes.dex` written |
| `2026-11-07 08:53:43.283` | `mergeProjectDexDebug/5/classes.dex` written |
| `2026-11-07 08:53:43.633` | Forced client log ends with daemon disappearance; 600-second bound reached |
| After cutoff | No `java.exe`, Gradle, or emulator process remained |

The forced log’s last task headers were:

```text
> Task :app:dexBuilderDebug
> Task :app:mergeDebugGlobalSynthetics
The message received from the daemon indicates that the daemon has disappeared.
Build request sent: Build{id=f3bc600a-b752-475a-9a25-1941ac61a303, currentDir=D:\FTP\NexHaat\android}
Attempting to read last messages from the daemon log...
```

No `BUILD SUCCESSFUL` or `BUILD FAILED` line was produced for the forced run.

---

## 4. Gradle daemon findings

### 4.1 Forced daemon (`daemon-5292.out.log`)

- PID: `5292`
- Single-use daemon (`--no-daemon` still forks a single-use daemon)
- Build: `f3bc600a-b752-475a-9a25-1941ac61a303`
- Effective daemon JVM options:
  `[-Xmx2048m, -Dfile.encoding=UTF-8, -Duser.country=US, -Duser.language=en, -Duser.variant]`
- Log size: 25,386 bytes, 142 lines
- Last write: `08:51:25.631`
- Last content: Kotlin compiler warnings (annotation-target and deprecation warnings)
- No `OutOfMemoryError`
- No `Java heap space`
- No fatal exception or Gradle build-failure report
- No `daemon has finished executing the build`
- No `Daemon vm is shutting down...`
- No normal `Stop requested` / registry-removal sequence

The absence of a normal-stop sequence is consistent with abrupt termination, but
the daemon log alone cannot distinguish an external kill from a native JVM crash.
The daemon log receives relayed build output only at certain points; its `08:51:25`
mtime does **not** mean the daemon died at 08:51, because DEX output continued
until 08:53:43.

### 4.2 Successful daemon comparison (`daemon-7644.out.log`)

The successful 76-second build’s daemon log contains the complete lifecycle:

```text
The daemon has finished executing the build.
Daemon vm is shutting down... The daemon has exited normally or was terminated in response to a user interrupt.
Stop requested. Daemon is removing its presence from the registry...
```

It also contains a benign shutdown-hook `IllegalStateException` about a closed
file-contention handler. That exception occurred during normal shutdown and did
not affect the successful build.

### 4.3 Prior producing build (`daemon-12032.out.log`)

- Starts at `19:06:38.122` with `Starting build in new daemon [memory: 2 GiB]`
- Ends successfully at `19:30:44` with `BUILD SUCCESSFUL in 24m 12s`
- Task summary: `42 actionable tasks: 15 executed, 27 up-to-date`
- Produced the current APK at `19:30:37`
- The same log shows one-time installation of Android SDK Build-Tools 35 and
  Platform 36, so the 24m12s duration is **not** a pure warm-build benchmark.

This is the strongest timing comparison available on the host: a successful
producing build with the same daemon heap consumed far more than 600 seconds,
partly because of SDK installation.

### 4.4 Kotlin daemon

- Session marker:
  `C:\Users\Enan\AppData\Local\kotlin\daemon\kotlin-daemon.2026-11-07T02-46-03.444Z...run`
- Size: 0 bytes
- Marker mtime: `08:46:03.458`
- Kotlin daemon directory mtime: `08:49`
- No readable Kotlin daemon `.log` file was present
- No Kotlin `OutOfMemoryError` or crash record was found

The Kotlin session’s exact exit status is unavailable. The Gradle log shows
`:app:compileDebugKotlin` output and later Java/Hilt/D8 task headers, so Kotlin
compilation had progressed beyond the Kotlin-compile stage before the cutoff.

### 4.5 Crash artifacts and OS events

- No `hs_err_pid*.log`
- No `replay_pid*.log`
- No `java_pid*.hprof`
- Searched:
  - `D:\FTP\NexHaat`
  - `D:\FTP\NexHaat\android`
  - `C:\Users\Enan\.gradle`
  - `C:\Users\Enan\AppData\Local\Temp` (`/tmp`)
  - `C:\Users\Enan` up to depth 3
- No recent Java crash dump in `C:\Users\Enan\AppData\Local\CrashDumps`
- No recent Java report in
  `C:\ProgramData\Microsoft\Windows\WER\ReportArchive`
- Windows Application events in the forced-build window (`08:40–09:00`) were
  Security-SPP informational events only; no Java/Gradle Application Error
  (`1000`), Windows Error Reporting (`1001`), or .NET Runtime (`1026`) event was
  observed for this build.
- No System unexpected-shutdown (`41`), unexpected-shutdown (`6008`), or
  resource-exhaustion event was found around the cutoff. The only `2004` record
  in the queried window was an unrelated `Microsoft-Windows-Setup` informational
  event at `01:46 UTC`.
- System boot time: `2026-11-06 11:46:40`; no reboot occurred during the forced
  build.

These absences do not prove a crash could not have happened, but they do not
support a JVM crash or OS-level OOM kill.

---

## 5. JVM, memory, disk and process findings

### 5.1 Physical and virtual memory

Observed at diagnostic time:

| Metric | Value |
|---|---|
| Total physical memory | 4,028 MB |
| Available physical memory | 628 MB |
| Logical CPUs | 4 |
| Virtual memory maximum | 11,098 MB |
| Virtual memory available | 4,404 MB |
| Virtual memory in use | 6,694 MB |
| Page file allocated | 7,069 MB |
| Page file current usage | 1,096 MB |
| Page file peak usage | 3,320 MB |
| System boot time | 2026-11-06 11:46:40 |

Interpretation:

- The host has only **~4 GB physical RAM**, with under 1 GB free at inspection.
- Gradle’s effective daemon heap is **2,048 MB**, plus a separate Kotlin daemon,
  D8 workers, the Gradle client, and the agent/browser processes.
- The page file peak of 3,320 MB is a cumulative-since-boot figure and cannot be
  attributed to the forced run without per-process telemetry. It is consistent
  with memory pressure during large builds.
- This is a plausible **contributing slowdown**, not a proven cause of the daemon
  disappearance.

### 5.2 Disk

| Drive | Size | Used | Available | Use |
|---|---:|---:|---:|---:|
| C: (Gradle cache, JDK, SDK) | 151 GB | 64 GB | 87 GB | 43% |
| D: (project) | 87 GB | 30 GB | 58 GB | 35% |

- Disk model: `MEMO BOSS-256G`, fixed hard disk.
- No disk-space exhaustion.
- No evidence of a disk I/O failure.

### 5.3 Current process state

- No `java.exe` process
- No Gradle daemon process
- No `qemu-system-x86_64.exe` process
- No emulator launched
- ADB available but `adb devices -l` lists no devices

Process history beyond daemon logs and Windows event logs is unavailable; Windows
does not retain a normal process-exit history by default. The absence of current
processes is not evidence of how the forced daemon exited.

---

## 6. Configuration observations

### 6.1 Effective Gradle memory setting

`android/gradle.properties`:

```properties
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official
android.nonTransitiveRClass=true
```

The forced command’s shell environment set `_JAVA_OPTIONS=-Xmx4g`, and the client
log begins with `Picked up _JAVA_OPTIONS: -Xmx4g`. However, the daemon log
explicitly records:

```text
daemonOpts=-Xmx2048m,-Dfile.encoding=UTF-8,...
```

Therefore:

- The effective Gradle daemon heap was **2,048 MB**, not 4 GB.
- `_JAVA_OPTIONS` is not a reliable way to override the Gradle daemon heap when
  `org.gradle.jvmargs` explicitly sets `-Xmx`.
- A 4 GB `_JAVA_OPTIONS` value on a 4 GB host would not be a safe fix even if it
  did apply; it would increase page-file pressure.

### 6.2 Build configuration

- Gradle wrapper: `9.7.1`
- Android Gradle Plugin: `8.9.1`
- Kotlin: `2.2.20`
- Compose compiler plugin: `2.2.20`
- Hilt: `2.57.2`
- Kotlin annotation processing: `kotlin-kapt`
- `compileSdk`: 36
- `minSdk`: 24
- `targetSdk`: 36
- Debug artifact: 18 DEX files in the last validated APK
- `--rerun-tasks` invalidates all task outputs; it re-executes all 42 tasks,
  including resource processing, Kotlin/KAPT, Hilt bytecode transformation, and
  D8 dexing.

### 6.3 Other settings

- No `org.gradle.parallel` setting
- No `org.gradle.workers.max` setting
- No `kotlin.daemon.jvmargs` setting
- No `org.gradle.caching` setting
- No configuration cache setting
- Default worker count on this host is therefore 4 (one per logical CPU)
- Wrapper network timeout: 10,000 ms; retries: 0
- No dependency-resolution or network failure appeared in the forced log
- `android/local.properties` is absent; the untracked
  `android/app/local.properties.debug` contains only
  `NEXHAAT_DEBUG_BASE_URL=http://10.0.2.2:5000/` and is not read by the current
  root-project configuration. This is unrelated to the timeout.

### 6.4 Configuration assessment

Potentially problematic for a forced full rebuild on this host:

1. A 2 GiB Gradle heap plus a separate Kotlin daemon plus up to four workers on a
   4 GB machine.
2. A forced full task graph with no build cache or configuration cache.
3. A 600-second external cap applied to a build that can legitimately exceed it.
4. Reliance on `_JAVA_OPTIONS` for heap sizing while `org.gradle.jvmargs` is
   explicit.

Not supported as the cause:

- SDK/build-tools absence or incompatibility: the SDK is installed and the forced
  log shows resource and compile tasks progressing.
- Kotlin/KAPT syntax or compile failure: no compile error, and later Java/Hilt/D8
  task headers appear.
- Network/dependency failure: no resolution failure in the log.
- Disk exhaustion: both drives have ample free space.

---

## 7. Most likely root cause, confidence and supporting evidence

### 7.1 Root cause

**The forced rebuild was terminated by the external 600-second execution bound
while it was still actively dexing. The daemon disappearance is the client-side
consequence of that termination, not a demonstrated internal Gradle crash. The
600-second budget is too short for a `--rerun-tasks` full rebuild on this
4 GB-RAM / 4-vCPU host.**

Secondary contributor: low physical memory and a 2 GiB daemon heap (with a
separate Kotlin daemon and multiple workers) likely increased paging and slowed
compilation/dexing. This is a plausible performance contributor, not a proven
out-of-memory event.

### 7.2 Confidence

**LIKELY** — high confidence in the timeout/termination mechanism, lower confidence
in the exact balance between ordinary slowness and memory pressure, and no direct
process-kill telemetry.

### 7.3 Supporting evidence

1. The forced command was wrapped in a **600-second** bound and the tool itself
   also timed out at 600 seconds.
2. The forced client log’s final write was at `08:53:43.633`.
3. The last project DEX shard was written at `08:53:43.283`, only **0.35 seconds**
   before the client log ended; two more were written at `08:53:42.845` and
   `08:53:42.969`.
4. The forced log had no `BUILD FAILED`, no compile error, and no dependency
   resolution failure.
5. The daemon log has no `OutOfMemoryError`, fatal exception, or normal-stop
   sequence; it simply stops after compiler warnings while D8 output continues.
6. No JVM crash dump, heap dump, Java WER report, or Windows Java/Gradle crash
   event was found.
7. The successful comparison daemon has an explicit normal shutdown sequence; the
   forced daemon does not.
8. A prior successful producing build on this host with the same 2 GiB daemon
   heap took **24m 12s** (including one-time SDK installation), far beyond 600s.
9. The host has only 4,028 MB physical RAM and under 1 GB free at inspection,
   with a 3,320 MB page-file peak since boot.
10. All observed build progress was forward: resources, Kotlin/KAPT, Java/Hilt,
    external DEX, and project DEX, with no repeated-task loop or deadlock signal.

### 7.4 What cannot be concluded

- The forced build was not proven to be capable of completing successfully within
  any particular longer period.
- Memory exhaustion was not observed directly and is not confirmed.
- The exact supervisor that terminated the process tree (GNU `timeout`, the tool
  boundary, or Windows process cleanup) is not identified by an OS event.
- A silent native JVM termination coincident with the 600-second boundary is not
  mathematically excluded, though it is not supported by any crash artifact.

---

## 8. Alternative explanations that cannot be ruled out

1. **JVM native-memory or heap exhaustion.** The host is memory-constrained and
   the Gradle heap is 2 GiB. A native allocation failure can terminate a JVM
   without a Java heap dump. No `hs_err_pid` or OOM record was found, so this is
   possible but unsupported.
2. **Windows resource-exhaustion termination.** Windows Resource Exhaustion
   Detection can act on memory-hogging processes and may produce a WER record.
   No Java/Gradle WER record was found around the cutoff. This remains possible
   if the termination was not reported.
3. **Gradle daemon internal crash.** The daemon log ends abruptly without a normal
   stop, which is consistent with a crash. However, there is no fatal exception,
   no JVM crash file, and active DEX writes continued to within one second of the
   cutoff, so an internal crash is less likely than external termination.
4. **Kotlin/KAPT/D8 stall or deadlock.** A stall could explain the elapsed time.
   The observed DEX writes immediately before the cutoff argue against a complete
   deadlock, but a stall after the last write cannot be excluded.
5. **Worker concurrency/resource contention.** Four workers, a Kotlin daemon, and
   the Gradle daemon on 4 GB of RAM can contend heavily. This is likely a
   slowdown contributor, but no thread dump or per-process memory series exists
   to prove it.
6. **SDK/build-tools issue.** Not supported: the SDK is installed and resource and
   compile tasks progressed. No SDK error appears in the forced log.
7. **Tool-level timeout rather than build failure.** This is the primary
   explanation, not an alternative: the build was still producing output when the
   tool/GNU timeout ended it.

---

## 9. Recommended remediation plan (recommendations only)

No remediation was implemented in this phase.

1. **Give forced full rebuilds a realistic budget.** For
   `:app:assembleDebug --rerun-tasks` on this host, use at least **1,800–2,400
   seconds (30–40 minutes)**, or run it as a background job without a hard
   600-second kill. Reserve 600 seconds for normal up-to-date validation.
2. **Stop using `--rerun-tasks` as the default verification command.** It forces
   all 42 tasks and is not representative of incremental development. Use targeted
   task reruns or a deliberate clean/full build when fresh packaging evidence is
   actually required.
3. **Right-size memory and workers.** Test an explicit, measured configuration:
   for example, keep `org.gradle.jvmargs` at 2 GiB or reduce it to 1.5 GiB, set an
   explicit Kotlin daemon heap around 1 GiB, and cap Gradle at
   `--max-workers=2`. Close memory-heavy applications during builds. The robust
   fix is additional physical RAM (8–16 GB); a 4 GB host is below the practical
   floor for this Android toolchain.
4. **Do not rely on `_JAVA_OPTIONS` for daemon heap sizing.** Set the daemon heap
   in `gradle.properties` or a reviewed build invocation, and verify the effective
   value in the daemon log (`daemonOpts=...`) before trusting it.
5. **Capture a diagnostic build next time (only after authorization).** Use
   `--info --stacktrace`, write the log outside the repository, record peak
   working set and page-file use, and keep the daemon log. If the daemon
   disappears without an external timeout, add
   `-XX:+HeapDumpOnOutOfMemoryError` and inspect WER.
6. **Evaluate build cache/configuration cache separately.** They may reduce
   repeat-build cost, but they do not replace a realistic timeout and must be
   compatibility-tested with Hilt/KAPT and the Compose plugin.
7. **Preserve the validated APK.** Do not delete or overwrite
   `app-debug.apk` while experimenting; build to a separate output or back up the
   checksum, and revalidate package/version/signature after any successful fresh
   build.
8. **Keep Stable and Get App closed.** Do not promote any debug output; the
   existing Stable/Get App gates must remain in place.

---

## 10. Debug APK and Stable/Get App regression status

### 10.1 Debug APK

| Check | Result |
|---|---|
| Expected path | `android/app/build/outputs/apk/debug/app-debug.apk` |
| Exists | YES |
| Size | 21,884,019 bytes |
| SHA-256 | `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c` |
| Last modified | `2026-11-06 19:30:37` |
| Changed by this phase | NO |
| New `intermediates/apk/debug` output | NONE |
| `packageDebug` completed in forced run | NO |
| Status | **PRESERVED** |

The hash matches the Phase 3.0 validated artifact. No APK was deleted, moved,
renamed, replaced, or installed.

### 10.2 Stable and Get App

| Check | Result |
|---|---|
| `APK/NexHaat.apk` | ABSENT |
| `APK/` contents | `checksums.txt`, `latest.json`, `status.json` only |
| `public/downloads/` contents | `metadata.json` only |
| `APK/latest.json` SHA-256 | `e36220e24b6a1e065ef76d877d0cc66753bca48ed6e74e7c6b64b40c5308782f` |
| `public/downloads/metadata.json` SHA-256 | Same `e36220…8782f` |
| `buildType` | `none` |
| `verified` | `false` |
| `sha256` | empty |
| `status` | `unavailable` |
| `artifactPath` | `APK/NexHaat.apk` |
| Get App candidate paths | Stable paths only: `APK/NexHaat.apk`, `APK/latest.apk`, `public/downloads/nexhaat.apk` |
| Debug path references in serving code | NONE |
| Get App availability gate | `apkMetadata?.exists && apkMetadata?.verified` |
| Production signing configuration | UNTOUCHED (`git diff` empty for Gradle build files/properties; no signing env vars set) |
| Status | **STABLE_APK: NOT_RELEASED; GET_APP_STATUS: UNAVAILABLE** |

`APK/latest.json` still contains a historical `withdrawnReleaseClaim` referencing a
previous debug artifact at `APK/debug/latest-debug.apk`; that claim is marked
withdrawn and does not select or expose the current debug APK. Its content was not
changed in this phase.

---

## 11. Git working-tree preservation status

### 11.1 Repository identity

- Branch: `main`
- HEAD: `ac6636afd54a7f91002604b6ae160d7d6f791972`
- HEAD subject: `ac6636a 2026-11-04 20:25:41 +0600 Fix`
- Upstream comparison `origin/main...HEAD`: `0 0`
- Unmerged files: none
- `git diff --check`: exit `0` (one pre-existing CRLF warning for
  `android/.gradle/buildOutputCleanup/cache.properties`)

### 11.2 Porcelain counts before this report

| State | Count |
|---|---:|
| Unstaged modifications (` M`) | 13 |
| Staged modifications (`M `) | 12 |
| Staged + unstaged (`MM`) | 1 |
| Deleted, unstaged (` D`) | 1 (`bun.lock`) |
| Untracked (`??`) | 31 |
| **Total** | **58** |

After adding this required report, the count becomes **59** (this report is the
only new untracked entry). No other file was added, removed, or modified by this
phase.

### 11.3 Full pre-report porcelain status

```text
M  .env.example
 M android/.gradle/9.7.1/executionHistory/executionHistory.bin
 M android/.gradle/9.7.1/fileHashes/fileHashes.bin
 M android/.gradle/9.7.1/fileHashes/resourceHashesCache.bin
 M android/.gradle/buildOutputCleanup/cache.properties
 M android/.gradle/buildOutputCleanup/outputFiles.bin
M  android/app/src/main/java/com/nexhaat/app/data/repository/AuthRepository.kt
M  android/gradlew
M  android/gradlew.bat
M  app/api/routes/auth.py
M  app/api/serializers.py
M  app/models/security.py
M  app/routes/auth.py
M  app/services/two_factor.py
M  app/services/two_factor_crypto.py
 D bun.lock
 M docs/architecture/FEATURE_REGISTRY.json
M  docs/architecture/WEBSITE_ANDROID_FEATURE_PARITY.md
 M package-lock.json
 M public/assets/aistudio/Paste_November_03__2026_-_6_56PM_524861a5
 M scripts/generate_apk_package.py
 M server.ts
MM src/components/FlaskAuthPanel.tsx
 M src/components/PWAInstallButton.tsx
 M src/services/apkDownloadService.ts
M  tests/test_auth_two_factor.py
 M vite.config.ts
?? .aistudio/artifacts/brain/f5612304-9a28-401a-9b7c-307bf3960d0d/
?? .github/workflows/android-qa-release.yml
?? .temp_recovery/
?? APK/
?? android/app/local.properties.debug
?? android/build-debug-nohup.out
?? android/gradlew-build.pid
?? android/system-images;android-36;google_apis;x86_64/
?? docs/APK_RELEASE_ARCHITECTURE.md
?? docs/APK_RELEASE_PHASE2_4_PREFLIGHT_REPORT.md
?? docs/APK_RELEASE_PHASE2_5_DEBUG_BUILD_REPORT.md
?? docs/APK_RELEASE_PHASE2_6_INSTALLATION_REPORT.md
?? docs/APK_RELEASE_PHASE2_7_GET_APP_INTEGRATION_REPORT.md
?? docs/APK_RELEASE_PHASE2_8A_CONFLICT_AUDIT_REPORT.md
?? docs/APK_RELEASE_PHASE2_8B_GATE_EVIDENCE_REPORT.md
?? docs/APK_RELEASE_PHASE2_9_GATE_STATUS_REFRESH_REPORT.md
?? docs/APK_RELEASE_PHASE3_0_DEBUG_RECOVERY_REPORT.md
?? docs/APK_RELEASE_RECOVERY_PLAN.md
?? docs/APK_RELEASE_RECOVERY_STATUS.md
?? docs/AUTOMATED_TESTING_AUDIT.md
?? docs/FINAL_APK_RELEASE_VERIFICATION.md
?? docs/REA_EXECUTION_DIAGNOSTIC.md
?? docs/REA_LIVE_PROCESS_VERIFICATION.md
?? docs/TEST_COVERAGE_MATRIX.md
?? public/downloads/
?? reports/
?? scripts/nexhaat_qa_release_orchestrator.py
?? scripts/validate_apk.py
?? serverMarketplace.ts
?? tests/test_apk_validator.py
?? tests/test_gate1_conflict_markers.py
```

### 11.4 Preservation actions

- No `git clean`
- No `git reset`
- No `git stash`
- No `git checkout`
- No `git rebase`
- No destructive glob or deletion command
- No commit
- No push
- No merge
- No deployment

All staged, unstaged, deleted, and untracked user work was preserved.

---

## 12. Remaining blockers

1. **No fresh successful forced build.** The 600-second run did not complete; no
   new APK was packaged. The existing APK is preserved and validated, but it is
   not evidence of a fresh forced rebuild.
2. **Root cause not CONFIRMED.** There is no OS process-termination record,
   per-process memory series, or thread dump. The timeout/termination explanation
   is LIKELY, not proven to the exclusion of a silent JVM termination.
3. **Memory-constrained host.** 4,028 MB physical RAM and under 1 GB free at
   inspection make full Android rebuilds slow and page-file dependent. A 30–40
   minute budget is recommended for `--rerun-tasks`.
4. **No device verification.** No Android device or running emulator is present,
   so installation, launch, and smoke testing remain BLOCKED from Phase 3.0.
5. **No Stable release.** `APK/NexHaat.apk` is absent, production signing is not
   configured, and Get App remains unavailable by design.
6. **Windows process history unavailable.** Normal process exit history is not
   retained by default; only event logs, daemon logs, and filesystem timestamps
   were available.
7. **No configuration changes were made.** The recommended memory/worker/timeout
   changes require separate review and explicit authorization.

---

## Appendix A — Commands used (read-only)

```bash
git status --short --branch
git status --porcelain=v1
git rev-parse HEAD
git rev-list --left-right --count origin/main...HEAD
git diff --check
git diff --stat -- android/app/build.gradle.kts android/build.gradle.kts android/gradle.properties
stat /tmp/nexhaat-phase3-assembleDebug*.log
wc -l ~/.gradle/daemon/9.7.1/daemon-*.out.log
grep -nE 'daemonOpts|OutOfMemory|BUILD SUCCESSFUL|BUILD FAILED|Daemon vm|Stop requested' ~/.gradle/daemon/9.7.1/daemon-*.out.log
find ... -name 'hs_err_pid*.log' -o -name 'replay_pid*.log' -o -name 'java_pid*.hprof'
systeminfo
wmic pagefile get AllocatedBaseSize,CurrentUsage,PeakUsage /format:list
df -h /c /d
wevtutil qe Application /q:"*[System[(EventID=1000 or EventID=1001 or EventID=1026)]]" /c:20 /rd:true /f:text
wevtutil qe System /q:"*[System[(EventID=41 or EventID=6008 or EventID=2004 or EventID=2019)]]" /c:20 /rd:true /f:text
tasklist /FI "IMAGENAME eq java.exe"
```

No Gradle build, emulator launch, APK install, cache deletion, daemon-file
deletion, source edit, configuration edit, dependency change, workflow change,
commit, push, merge, or deployment was performed.

## Appendix B — Report file

`docs/APK_RELEASE_PHASE3_1_GRADLE_TIMEOUT_DIAGNOSTIC_REPORT.md`
