# APK RELEASE — PHASE 2.9 GATE 1 STATUS REFRESH & REGRESSION TESTS

Created: 2026-11-06
Workspace: `D:\FTP\NexHaat`
Package: `com.nexhaat.app`
Mode: **repair Gate 1 reporting + add regression tests**, without publishing, signing, APK creation, or deployment.

Final status:
```text
GATE_1: PASS
STABLE_APK: NOT_RELEASED
GET_APP_STATUS: UNAVAILABLE
PRODUCTION_SIGNING: BLOCKED
```

---

## 1. Objective

Safely repair stale Gate 1 status reporting and add regression protection, under a strict Stable-only APK policy:

- Public Stable APK path: `APK/NexHaat.apk`, filename `NexHaat.apk`.
- Debug APK stays internal at `android/app/build/outputs/apk/debug/`.
- Get App stays unavailable until a verified production Stable APK exists.
- No commit, push, merge, rebase, or deployment.
- No change to Auth/2FA code, signing config, APK/metadata fabrication, or Get App availability.

---

## 2. Pre-change safety snapshot (Phase 1)

Files and evidence preserved:

- `git status --short --branch`: `main`, ahead of `origin/main`, many pre-existing user modifications, **no unmerged files**.
- `git ls-files -u`: empty.
- `git diff --check`: exit 0 (one CRLF warning on `android/.gradle/buildOutputCleanup/cache.properties`).
- `APK/status.json` before refresh:
  - `status`: `BLOCKED`
  - `gates[0].status`: `FAIL`
  - `gates[0].facts.conflictMarkers`: **105** stale entries
  - `blockedBy.gate`: `1`
  - `toolchain.signingConfigured`: `false`
  - `liveRelease.latestApkExists`: `false`
- `APK/latest.json` and `public/downloads/metadata.json` before refresh:
  - `buildType`: `"none"`
  - `verified`: `false`
  - `sha256`: `""`
  - `withdrawnReleaseClaim` present

All pre-existing user modifications were left intact. Nothing was reset, cleaned, stashed, or overwritten.

---

## 3. Root cause

Gate 1 is implemented as a current scan (`git grep -n -I ...` + `git diff --check`), so it does **not** load `APK/status.json` as its truth source for markers. The stale `105`-marker list came from a prior orchestration run whose Gate 1 failure was written to `APK/status.json` and never overwritten by a later successful scan.

In addition, Gate 1’s marker normalization was being applied to raw `git grep -n` output, which is `path:line:match`. The anchored patterns (`^<<<<<<< `, `^>>>>>>> `, `^=======$`) live in the matched text, not at the start of the grep output line, so the previous normalization could not detect markers in `git grep -n` output. That mismatch is what the regression tests now catch.

---

## 4. Files changed (Phase 2)

- `scripts/nexhaat_qa_release_orchestrator.py`
  - Added `_strip_grep_path_line_prefix()` to extract the matched marker text from `git grep -n` output.
  - Added `normalize_conflict_marker_lines()` as the shared, deterministic marker-text normalizer.
  - Updated `gate_1_repository_integrity()` so:
    - `conflictMarkers` is always generated from the current scan.
    - every `gate_1_*` result includes `facts.currentScan` with the exact command, `exitStatus`, `rawMarkerLines`, and `normalizedMarkerLines`.
    - a previous failed result can no longer be presented as the current live result after a fresh successful Gate 1 run.
    - scan errors are recorded in `currentScan.exitStatus`; Gate 1 still never fabricates a PASS when markers exist or when downstream checks fail.
    - intentional CSS separators and documentation examples are not incorrectly classified as real merge conflicts because the normalizer still requires anchored line-start markers and does not treat standalone `=======` as a conflict unless it appears in a `<<<<<<<`/`>>>>>>>` context.

No other release gates were modified.

---

## 5. Status integrity (Phase 3)

`APK/status.json` was refreshed through the existing supported path: a `--dry-run` orchestrator run that executes Gate 1 against the current checkout and writes status via `write_status()` / `on_failure()`. No PASS result was manually invented.

After refresh:

- `status`: `BLOCKED`
- `gates[0].status`: `PASS`
- `gates[0].facts.conflictMarkers`: `[]` (fresh current scan)
- `gates[0].facts.currentScan`: present, `exitStatus`: `1` (git grep no-match exit), `rawMarkerLines`: `[]`, `normalizedMarkerLines`: `[]`
- `blockedBy.gate`: `2` (this refresh run stopped at Gate 2 via `--force-fail gate2`; Gate 1 itself passed)
- `toolchain.signingConfigured`: `false`
- `liveRelease.latestApkExists`: `false`

Genuine blockers preserved intact:

- Production signing is not configured.
- Stable APK does not exist.
- Public download remains unavailable.

Overall release status is **not** `READY`; Gate 1 passing does not unblock the release.

---

## 6. Regression tests (Phase 4)

New file: `tests/test_gate1_conflict_markers.py`

Tests and results (run with `python -B tests/test_gate1_conflict_markers.py`):

1. `test_genuine_conflict_marker_is_detected` — PASS
2. `test_no_conflict_markers_returns_pass_shape` — PASS
3. `test_css_section_separators_do_not_false_positive` — PASS
4. `test_documentation_examples_do_not_false_positive` — PASS
5. `test_scan_failure_never_returns_pass` — PASS
6. `test_git_grep_no_match_exit_is_clean` — PASS
7. `test_current_scan_replaces_stale_conflict_data` — PASS
8. `test_signing_missing_keeps_release_blocked` — PASS
9. `test_stable_apk_missing_keeps_get_app_unavailable` — PASS
10. `test_debug_apk_is_never_selected_as_public_download_candidate` — PASS

All 10 tests passed; 0 failed.

Existing APK validator suite (`tests/test_apk_validator.py`) was rerun and also passed (9 passed, 0 failed), confirming no regression there.

---

## 7. Validation (Phase 5)

Checks run:

- Gate 1 live scan: **PASS** — `[PASS] Gate 1 — Repository integrity & manifest (1.12s)` via `python scripts/nexhaat_qa_release_orchestrator.py --dry-run --force-fail gate2`.
- `git diff --check`: **exit 0** (clean; one pre-existing CRLF warning on a Gradle cache file).
- Python compile checks for `scripts/nexhaat_qa_release_orchestrator.py` and `tests/test_gate1_conflict_markers.py`: **OK**.
- Focused Gate 1 regression tests: **10 passed, 0 failed**.
- Existing APK validator tests: **9 passed, 0 failed**.
- Metadata consistency:
  - `APK/latest.json` and `public/downloads/metadata.json` match.
  - Both show `buildType: "none"`, `verified: false`, empty `sha256`, and a present `withdrawnReleaseClaim`.

Get App candidate-path inspection:

- `server.ts` `getApkCandidatePaths()` leads with `APK/NexHaat.apk`, then `APK/latest.apk`, then `public/downloads/nexhaat.apk`. No Debug candidate is exposed.
- Current existence check: `APK/NexHaat.apk` absent, `APK/latest.apk` absent, `public/downloads/nexhaat.apk` absent.
- Frontend Get App availability is gated on `apkMetadata?.exists && apkMetadata?.verified`, so Get App stays unavailable until a verified Stable APK exists.

Not run (and not required for this phase):

- Full Android build / emulator.
- Live HTTP serving of the download endpoint (earlier npm cache/tarball integrity failures blocked a reliable `npm install` in this environment, so the download endpoint behavior is not live-verified here).

---

## 8. Current status metadata

`APK/status.json` (refreshed):

- `status`: `BLOCKED`
* `appName`: `NexHaat`
* `packageId`: `com.nexhaat.app`
* `buildId`: `20261106170347`
* `updatedAt`: current UTC timestamp at refresh time
* `version`: `1.0.0`
* `versionCode`: `1`
* `toolchain.signingConfigured`: `false`
* `gates[0]`:
  - `gate`: `1`
  - `name`: `Repository integrity & manifest`
  - `status`: `PASS`
  - `mandatory`: `mandatory`
  - `facts.currentScan`: present with command, exit status, raw and normalized marker lines
  - `facts.conflictMarkers`: `[]`
* `blockedBy.gate`: `2`
* `liveRelease.latestApkExists`: `false`

`APK/latest.json` and `public/downloads/metadata.json`:

- `buildType`: `"none"`
- `verified`: `false`
- `sha256`: `""`
- `status`: `"unavailable"`
- `verification.status`: `"NOT_RELEASED"`
- `withdrawnReleaseClaim`: present

---

## 9. Signing and Stable APK blockers

- `PRODUCTION_SIGNING: BLOCKED` — `toolchain.signingConfigured` is `false` in the refreshed status and no signing environment variables are configured in this environment.
- `STABLE_APK: NOT_RELEASED` — `APK/NexHaat.apk` does not exist; `liveRelease.latestApkExists` is `false`.
- `GET_APP_STATUS: UNAVAILABLE` — no verified Stable APK exists, and both the backend download path and the frontend Get App gate require an existing verified artifact.

---

## 10. Debug / Stable separation verification

- Debug build remains internal to `android/app/build/outputs/apk/debug/`.
- No public download path exposes the debug artifact.
- `server.ts` APK candidate list starts with `APK/NexHaat.apk` and does not include a Debug candidate.
- Regression test `test_debug_apk_is_never_selected_as_public_download_candidate` asserts the documented Stable-only policy.

---

## 11. Remaining work

- The underlying in-progress 2FA/auth changes in the working tree are outside this phase’s scope and remain the owner’s responsibility to resolve before any future release.
- Live HTTP verification of the Get App download endpoint is still NOT RUN due to the environment’s npm integrity issues; Get App behavior is verified by source inspection and the existing availability gate, not by a live request here.
- A real Stable signed APK is still required before Get App can become available.

---

## 12. Git status at completion

- Branch: `main`
- Working tree: dirty with pre-existing user modifications, including the intentional Phase 2.9 edits to `scripts/nexhaat_qa_release_orchestrator.py` and the new `tests/test_gate1_conflict_markers.py`, plus all prior user changes.
- `git diff --check`: exit 0.
- No commit, push, merge, rebase, or deployment was performed.

---

## 13. Expected result achieved

- `GATE_1: PASS` — fresh current scan passed.
- `STABLE_APK: NOT_RELEASED` — no Stable APK exists.
- `GET_APP_STATUS: UNAVAILABLE` — no verified Stable APK.
- `PRODUCTION_SIGNING: BLOCKED` — signing not configured.

---

## 14. Report file

`docs/APK_RELEASE_PHASE2_9_GATE_STATUS_REFRESH_REPORT.md`
