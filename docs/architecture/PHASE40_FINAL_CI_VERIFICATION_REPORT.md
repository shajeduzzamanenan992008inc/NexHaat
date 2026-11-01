# Phase 40 — Final CI Verification

**Date:** 2026-11-01  
**Branch / HEAD:** `main` / `e1b8449c57cfdfb23352349d91e95158cff456f3`

## Current state and Phase 39 status

At inspection, `git status --short --branch` was clean and showed
`main...origin/main`; the Phase 39 workflow change is present in the current
local `HEAD`, not an uncommitted worktree edit. The known Phase 39 baseline
`5000ff6c871d3f2dcc4f5d75ccf83e943c2f180f` is an ancestor of this `HEAD`.
The local branch has no reported difference from its cached `origin/main`
tracking reference. This is local Git metadata, not confirmation of the live
remote default branch.

`gh --version` reported `2.103.3`. `gh auth status` reported that no GitHub
host is authenticated. Per scope, remote inspection stopped there; no latest
workflow runs, job logs, artifacts, branch settings, or live remote branch
state could be verified. **Remote Phase 39 publication and CI results remain
BLOCKED / NOT VERIFIED.** No push was made or is implied.

## SBOM workflow verification

The current `.github/workflows/sbom-provenance.yml` confirms:

- The checkout and artifact names derive from `SOURCE_SHA`; for a successful
  CI `workflow_run`, this is the tested run's `head_sha`.
- The tarball destination is `${RUNNER_TEMP}/${archive}`, outside the checked
  out `.` traversal root. The generated `sbom.spdx.json` is excluded from that
  source archive.
- Existing exclusions for Git metadata, dependencies, virtual environments,
  caches, environment files, PEM files, and key files remain.
- The archive is checked for nonzero size and copied into the workspace only
  after tar completes. `sha256sum` then covers the archive and SBOM.
- Artifact upload still includes the SBOM, source snapshot, and checksum
  manifest. The conditional provenance job still downloads that artifact and
  attests the same archive subject and SBOM.

The Phase 39 report's root-cause analysis remains consistent with the source:
the previous command wrote its archive into the same directory it traversed.
Local source inspection confirms the fix is in `HEAD`; it does not prove a
remote run created or uploaded an artifact.

## CodeQL and CI status

The prior Phase 37/38 evidence records the CodeQL upload error
`Code scanning is not enabled for this repository.` The CodeQL workflow retains
its three-language matrix, and no setting or workflow change was made here.
Current remote job outcomes could not be read.

| Check / job | Status | Evidence |
|---|---|---|
| SBOM snapshot/archive construction | **PASS — local source verified** | Archive path is under `RUNNER_TEMP`, not checkout; generated SBOM excluded |
| SBOM checksum, artifact upload, provenance flow | **PASS — workflow source verified** | `sha256sum`, upload file list, and attestation inputs remain present |
| Latest remote SBOM workflow run/artifact | **BLOCKED — NOT VERIFIED** | GitHub CLI unauthenticated; no remote inspection |
| CodeQL `Analyze (actions)` | **BLOCKED — remote status NOT VERIFIED** | Prior supplied evidence reports Code Scanning disabled |
| CodeQL `Analyze (python)` | **BLOCKED — remote status NOT VERIFIED** | Prior supplied evidence reports Code Scanning disabled |
| CodeQL `Analyze (javascript-typescript)` | **BLOCKED — remote status NOT VERIFIED** | Prior supplied evidence reports Code Scanning disabled |
| Latest remote CI status | **BLOCKED — NOT VERIFIED** | GitHub CLI unauthenticated; no remote inspection |
| Live remote default branch contains Phase 39 | **BLOCKED — NOT VERIFIED** | Local cached `origin/main` tracking state is not live remote evidence |

An authorized repository administrator must review **Settings → Security →
Code security and analysis → Code scanning** and enable Code Scanning while
retaining the existing advanced CodeQL workflow. If this is unavailable or
locked, the organization/enterprise administrator must review its policy and
authorize the feature. Afterward, a new CodeQL run must complete all three
matrix jobs successfully.

## Checks and changed files

- `git diff --check` — **PASS**.
- `bash -n` on the exact extracted SBOM workflow `run` block — **PASS**.
  An initial attempt to give Git Bash a Windows temporary-file path failed
  because of path conversion; piping the exact extracted script to Bash stdin
  succeeded.
- YAML parser — **NOT AVAILABLE**; no installed actionlint, yq, yamllint,
  Ruby, PyYAML, or Node YAML package was found.
- `gh --version` — **PASS**, version `2.103.3`.
- `gh auth status` — **BLOCKED**, no authenticated GitHub host.

Files changed in Phase 40:

- `docs/architecture/PHASE40_FINAL_CI_VERIFICATION_REPORT.md` — this report.
- `docs/plans/nexhaat-master-plan.md` — dated Phase 40 evidence entry.

The SBOM workflow itself was not changed in Phase 40. Remote SBOM/CI/CodeQL
verification requires authenticated GitHub access. If the Phase 39 change is
not on the live remote branch, publishing it requires explicit user
authorization; this task did not push it. No GitHub setting change, commit,
merge, deployment, or production action occurred.
