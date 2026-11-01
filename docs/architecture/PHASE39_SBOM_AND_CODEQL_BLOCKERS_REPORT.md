# Phase 39 — SBOM and CodeQL Blockers

**Date:** 2026-11-01  
**Branch / HEAD:** `main` / `5000ff6c871d3f2dcc4f5d75ccf83e943c2f180f`

## Baseline and evidence

At inspection, `git status --short --branch` reported `main...origin/main`
with no worktree changes. The supplied HEAD matched the user-provided latest
remote commit. Phase 37 and Phase 38 reports and the current SBOM/CodeQL
workflows were reviewed before editing.

The supplied SBOM run error was `tar: .: file changed as we read it`. Direct
access to run `41327093578` was unavailable: `gh auth status` reported no
authenticated GitHub host, and unauthenticated run/API URLs returned 404.
Therefore the log text is user-provided evidence, not independently retrieved.

## SBOM snapshot diagnosis and fix

**Root cause established from the workflow:** the archive command used
`tar -czf "$archive" ... .`, making the tarball itself a new file in the
directory being traversed. This changes the input directory during traversal
and is consistent with the reported tar diagnostic. The same command also
would have included the already-generated `sbom.spdx.json` in the source
snapshot, although that file is not part of `SOURCE_SHA`.

`.github/workflows/sbom-provenance.yml` now writes the tarball to
`${RUNNER_TEMP}`, outside the checked-out source tree, excludes the generated
SBOM, confirms the archive is nonempty, and copies the completed archive into
the workspace before checksum generation. Checkout still targets
`SOURCE_SHA`; the existing `.git`, dependency, virtual-environment, cache,
environment-file, PEM, and key exclusions are preserved. The artifact still
contains the SBOM, source snapshot, and SHA-256 manifest, and the optional
attestation still uses the same subject paths and permissions. No application
source files are excluded beyond the existing exclusions and the generated
SBOM.

The failure mechanism is directly supported by the command's input/output
paths. It was not independently reproduced with the runner's GNU tar because
this Windows environment provides BSD tar; a focused temporary-fixture check
verified the corrected external-output archive behavior and contents.

## CodeQL

The existing CodeQL workflow retains its push/PR, schedule, and manual
triggers; `javascript-typescript`, `python`, and `actions` matrix; read
permissions plus `security-events: write`; and `security-extended` analysis.
No workflow defect was identified, and the workflow was not changed.

The user-provided failure is `Code scanning is not enabled for this
repository.` The prior Phase 37/38 reports record the same remote error.
Direct run-log and repository-setting inspection is currently **BLOCKED**:
GitHub CLI is unauthenticated and public run URLs returned 404. No settings
were changed.

**Manual action for an authorized repository administrator:**

1. Open the repository's **Settings → Security → Code security and analysis**.
2. Review **Code scanning** and enable GitHub Code Security/code scanning for
   this repository, retaining the existing advanced CodeQL workflow.
3. If the setting is unavailable or locked, ask the organization or enterprise
   administrator to review the governing policy and enable/authorize code
   scanning for this repository.
4. After the setting is enabled and the workflow changes are published through
   the normal authorized process, run CodeQL and verify all three matrix jobs
   complete successfully.

## Verification and status

| Item | Result |
|---|---|
| SBOM tar root cause from workflow | **PASS — established**: archive output was created under the `.` traversal root |
| SBOM source archive correction | **PASS — local change**: archive output moved to `RUNNER_TEMP`; generated SBOM excluded |
| Focused temporary archive fixture | **PASS** — source fixture retained; generated SBOM and excluded paths absent; archive not self-included |
| Supplied SBOM workflow run | **BLOCKED** — user supplied the tar error, but its log could not be fetched directly |
| New remote SBOM run confirming fix | **NOT TESTED** — no push/dispatch authorized |
| CodeQL workflow source | **PASS — inspected**; no change made |
| CodeQL remote jobs and setting | **BLOCKED** — no authenticated remote access; administrator action required |
| Workflow shell syntax (`bash -n`) | **PASS** |
| Workflow YAML parser | **NOT AVAILABLE** — actionlint, Ruby, yq/yamllint, PyYAML, and Node YAML packages were not available |
| `git diff --check` | **PASS** |

Changed files:

- `.github/workflows/sbom-provenance.yml`
- `docs/architecture/PHASE39_SBOM_AND_CODEQL_BLOCKERS_REPORT.md`
- `docs/plans/nexhaat-master-plan.md`

The source snapshot fix is **locally implemented but not remotely verified**.
A new remote run is required after the workflow change is included in an
authorized push. CodeQL remains **BLOCKED** until an authorized administrator
enables/reviews Code Scanning and a subsequent run succeeds. No application
source, tests, CodeQL workflow, GitHub settings, or production configuration
was changed. No commit, push, merge, or deployment occurred.
