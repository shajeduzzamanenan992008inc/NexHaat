# APK RELEASE — PHASE 2.8B RELEASE GATE EVIDENCE RECONCILIATION

Created: 2026-11-06
Workspace: `D:\FTP\NexHaat`
Package: `com.nexhaat.app`
Mode: **READ-ONLY** — no source or metadata edits, no npm install, no Gradle build, no emulator/ADB, no signing changes, no APK handling, no commit/push/merge/deploy.

Final status: `GATE_EVIDENCE: STALE_FINDINGS_CONFIRMED`

---

## 1. Evidence sources

- `APK/status.json` — current release-orchestrator status artifact.
- `scripts/nexhaat_qa_release_orchestrator.py` — Gate 1 implementation and failure handling.
- `scripts/validate_apk.py` — APK validator (read for scope/exit-code contract; not executed on an APK here).
- `docs/APK_RELEASE_PHASE2_8A_CONFLICT_AUDIT_REPORT.md` — prior audit finding.
- `docs/APK_RELEASE_RECOVERY_PLAN.md` and `docs/APK_RELEASE_RECOVERY_STATUS.md` — prior release-state context.
- Direct evidence from the current checkout:
  - `git status --short --branch`
  - `git ls-files -u`
  - `git diff --check`
  - current `git grep -n -I -e "^<<<<<<< " -e "^>>>>>>> " -e "^=======$"`
  - a bounded run of `ReleaseOrchestrator.gate_1_repository_integrity()` (Gate 1 only, no pipeline, no publication).

---

## 2. Where `conflictMarkers` comes from

In `scripts/nexhaat_qa_release_orchestrator.py`, Gate 1 is
`ReleaseOrchestrator.gate_1_repository_integrity()`.

Its marker detection is **dynamic and current**, not hardcoded:

1. It runs
   `git grep -n -I -e "^<<<<<<< " -e "^>>>>>>> " -e "^=======$"`.
2. It collects non-empty lines from stdout if the exit code is `0` or `1`.
3. If any marker lines are found, it builds a Gate 1 FAIL result whose
   `facts["conflictMarkers"]` contains the scanned lines (truncated to 200).
4. Otherwise it proceeds to `git diff --check` and the remaining manifest/identity
   checks.

So the **intended** Gate 1 behavior is to report what is actually in the current
tracked trees at scan time.

The stale list is created when the orchestrator writes status. In
`on_failure()`, Gate 1's failed result is stored as `blockedBy`, and
`write_status()` persists the full `gates[0].to_dict()`, including
`facts.conflictMarkers`. Once persisted, that snapshot does not automatically
refresh unless Gate 1 is re-run and the pipeline succeeds or fails again.

---

## 3. Whether the stale list is dynamic or cached

It is a **persisted snapshot of a prior scan**, not a live query.

Current evidence:

- `APK/status.json` currently records:
  - `status`: `BLOCKED`
  - `gates[0].status`: `FAIL`
  - `gates[0].facts.conflictMarkers`: **105** entries
  - `blockedBy.gate`: `1`
- Current checkout evidence shows:
  - `git ls-files -u`: empty
  - `git diff --check`: exit 0
  - `git grep -n -I -e "^<<<<<<< " -e "^>>>>>>> " -e "^=======$"`: no matches
  - bounded Gate 1 run: **PASS**, `conflictMarkers` count = **0**

So the stored `105`-marker list is not what a current Gate 1 scan produces.

---

## 4. Does Gate 1 read current files or historical report data?

Gate 1 itself reads the current repository via `git grep` and `git diff --check`.
It does **not** load `APK/status.json` as its source of truth for markers.

The stale result is therefore not coming from Gate 1 logic being "stuck on old
data" during a scan. It comes from a **prior orchestration run** whose Gate 1
result was written to `APK/status.json` and never overwritten by a later
successful or reconciled scan.

---

## 5. Can stale findings survive after source files change?

Yes — and that is the core issue here.

The release-status artifact is a **history of the last orchestration outcome**,
not a live reflection of the working tree. If:

- a prior run failed Gate 1 and wrote the failed `conflictMarkers` list, and
- the working tree was later edited so that the anchored markers no longer exist,

then `APK/status.json` can still say FAIL with the old marker list even though
the current files are clean.

That is exactly the current state: the status file reports markers that the
current scan no longer finds.

---

## 6. Does the release gate have tests for this kind of false positive?

From the read-only evidence:

- `scripts/nexhaat_qa_release_orchestrator.py` has a `--dry-run` mode, a
  `--force-fail` mode for gates 1–6, and a `--verify-release` mode.
- `scripts/validate_apk.py` has a clear PASS/FAIL/BLOCKED exit-code contract and
  is written to avoid passing placeholder artifacts.
- The repository also has Python test files, including `tests/test_apk_validator.py`.

What was **not** found in this audit:

- No evidence that the repository contains an explicit automated test asserting
  that Gate 1 must stay in sync with the actual current `git grep` result after
  markers are removed from source files.
- No evidence that `APK/status.json` is regenerated or invalidated automatically
  when the working tree changes outside a new pipeline run.

So the reconciliation issue is not proved to be caused by a missing unit test, but
the current behavior is consistent with status being a persisted snapshot rather
than a continuously refreshed live view.

---

## 7. Current vs stale findings

### 7.1 Stale findings recorded in `APK/status.json`

- Gate 1 status: `FAIL`
- `blockedBy.gate`: `1`
- `conflictMarkers`: 105 lines
- Notable named paths in the stale list:
  - `android/app/src/main/java/com/nexhaat/app/data/repository/AuthRepository.kt`
  - `app/api/routes/auth.py`
  - `app/models/security.py`
  - `app/routes/auth.py`
  - `app/services/two_factor.py`
  - `app/services/two_factor_crypto.py`
  - `docs/architecture/WEBSITE_ANDROID_FEATURE_PARITY.md`
  - `public/assets/aistudio/Paste_November_03__2026_-_6_56PM_524861a5`
  - `tests/test_auth_two_factor.py`
- Release status: `BLOCKED`
- `liveRelease.latestApkExists`: `false`
- `toolchain.signingConfigured`: `false`

### 7.2 Current findings from the checkout

- No unmerged files.
- `git diff --check` clean.
- Anchored marker scan: **0** matches in the scanned trees.
- Bounded Gate 1 run: **PASS**, `conflictMarkers` **empty**.

### 7.3 Files present in the stale list but not confirmed as still problematic

These paths are in the stored stale list, but the current checkout evidence does
not confirm them as active conflict-marker files:

- `public/assets/aistudio/Paste_November_03__2026_-_6_56PM_524861a5`
- every auth/2FA file listed above

The Phase 2.8A audit also found that the committed `ac6636a` grep for
`^<<<<<<< ` does not include the aistudio paste file, which makes that particular
stale entry inconsistent with HEAD as well.

---

## 8. Release status integrity check

### 8.1 Signing configuration

- `APK/status.json` says `toolchain.signingConfigured: false`.
- That is consistent with the current environment not having the four signing
  environment variables and with no keystore being present for this audit.

So signing status is currently accurate in the status file.

### 8.2 Actual Stable APK existence

- `APK/NexHaat.apk`: not present.
- `APK/status.json` `liveRelease.latestApkExists`: `false`.
- `liveRelease.publicMirrorExists`: `false`.
- `liveRelease.releases`: `[]`.

So the Stable-APK-absent part of the status record is accurate.

### 8.3 Actual release verification status

- No verified Stable APK exists.
- Get App remains unavailable under the current policy because no verified
  `APK/NexHaat.apk` exists.
- The release status is therefore correctly `BLOCKED` in the broad sense, but its
  **Gate 1 reason is stale**.

### 8.4 Current Gate 1 result

- Stored: FAIL (105 stale markers).
- Live Gate 1 run: PASS (0 markers).

So Gate 1 is the exact field where the stored status diverges from the current
evidence.

### 8.5 Debug versus Stable separation

- Debug build remains internal to `android/app/build/outputs/apk/debug/`.
- No public download path is exposing the debug artifact.
- The stale conflict-marker issue is separate from Stable/Debug separation, but
  the status file should still not claim unresolved repository markers if the
  current checkout does not contain them.

---

## 9. Root cause

The root cause is **status-a artifact staleness**, not an undetected marker
somewhere in the current tree.

More specifically:

1. A prior orchestrator run scanned the repository, found anchored conflict
   markers, and wrote `APK/status.json` with a Gate 1 FAIL and a stored
   `conflictMarkers` list.
2. Subsequently, the working tree was edited so that the current
   `git grep` for anchored `<<<<<<<` / `=======` / `>>>>>>>` no longer matches
   in the inspected source/docs/config trees.
3. The status file was not regenerated from the current tree, so the stored
   "leftover conflict markers found in the working tree" message is now outdated.
4. Downstream reports and failure artifacts then inherited or repeated the stale
   marker list, which made the discrepancy look larger than the underlying issue.

The important nuance: the committed history `ac6636a` really did contain conflict
markers, so the stale snapshot was once defensible as a record of a prior state.
It has simply not been reconciled with the current checkout.

---

## 10. Exact files requiring future changes

These are the files that should be changed later to prevent the discrepancy from
recurring. This audit does not edit them.

### 10.1 Release status refresh path

- `scripts/nexhaat_qa_release_orchestrator.py`
  - The clearest fix is that status should always represent the most recent
    attempted pipeline result, and any manual/auditor reconciliation should be done
    by re-running the relevant gate or pipeline rather than by assuming the stored
    `conflictMarkers` list is live.
  - If the intended design is a "live status" view, Gate 1 should either refresh
    status on demand or the status file should make clear that it reflects the last
    run, not the current tree.

### 10.2 Marker detection precision

- `scripts/nexhaat_qa_release_orchestrator.py`, Gate 1 scan
  - The current pattern set is reasonable for standard Git conflict markers at line
    start.
  - If the project ever intentionally uses `=======` as a literal separator in
    tracked source, the scan must be tightened so those are not false positives.
  - The current Phase 2.8A finding shows the only surviving literal matches in
    source trees were CSS section separators in `src/index.css`, which are
    `/* ... ======= ... */` comments, not standalone `=======` lines.

### 10.3 False-positive immunity

- Any future marker checker should be tested against known false positives:
  - CSS `/* ==== ... ==== */` separators such as those in `src/index.css`.
  - Test fixtures or documentation examples that legitimately contain the literal
    text.
- The safest baseline is the current anchored patterns plus explicit exclusions or
  context checks for non-conflict uses.

### 10.4 Status integrity and fail-closed

- `APK/status.json` should continue to be fail-closed for the real blockers:
  - no verified Stable APK
  - signing not configured
- But the specific Gate 1 marker claim should be recoverable by re-running Gate 1
  or the pipeline, not locked in as if it were still true.

---

## 11. Recommendations

### 11.1 What should be fixed

1. Do not treat `APK/status.json` as a live tree scan. Treat it as the result of
   the last orchestration attempt.
2. When reconciling, re-run Gate 1 (or the pipeline) against the current checkout
   and allow that to overwrite the stale Gate 1 result.
3. If the repository wants a standing "is this tree currently conflict-free?"
   answer, implement it as a fresh scan, not as a stored stale list.
4. Tighten marker detection only if the repository intentionally uses
   `=======` or similar tokens as literal separators in tracked source. Until then,
   the current anchored patterns are sufficient and the only surviving false
   positives found were CSS comment separators.

### 11.2 What should be tested

1. A reconciliation check: after removing markers from source, the pipeline/gate
   should report no remaining conflict markers and should overwrite the stale
   status entry.
2. A false-positive check: known intentional separators/comments in source should
   not be reported as conflicts.
3. A status-integrity check: if signing is not configured and no Stable APK exists,
   the status must still remain blocked even after a clean Gate 1 scan.

---

## 12. Remaining blockers

1. **Stale Gate 1 marker list in `APK/status.json`** — the stored
   `conflictMarkers` and FAIL detail do not match the current checkout.
2. **Release still blocked for real reasons unrelated to the stale markers** —
   no verified Stable APK and signing not configured remain true blockers.
3. **No evidence of an automated reconciliation test** ensuring Gate 1 status
   stays in sync with the current tree after markers are removed.
4. **Authoritative decision about any markers that might exist outside the
   inspected trees or in a non-standard form** — this audit cannot rule that out
   completely; it can only say the current anchored scans and live Gate 1 run did
   not find them.

---

## 13. Conclusion

The current working tree does **not** contain the stale conflict markers recorded
in `APK/status.json`. Gate 1 itself is implemented as a current scan, and when run
against the current checkout it passes with zero markers.

The discrepancy exists because `APK/status.json` records a prior failed scan and
has not been refreshed from the current tree.

Therefore the supported status is:

```text
GATE_EVIDENCE: STALE_FINDINGS_CONFIRMED
```

The stale finding is confirmed, and the real remaining question is not "are there
secret markers in the tree," but "how should release status stay accurately
reconciled with the current checkout."

---

## 14. Report file

`docs/APK_RELEASE_PHASE2_8B_GATE_EVIDENCE_REPORT.md`

---

## 15. Safety confirmations

- No source file was edited.
- No metadata file was edited.
- No APK was created, copied, moved, or renamed.
- No signing configuration was changed.
- No npm install, Gradle build, emulator, or ADB action was performed.
- No commit, push, merge, rebase, or deployment was performed.
- Existing user modifications in the working tree were preserved.
