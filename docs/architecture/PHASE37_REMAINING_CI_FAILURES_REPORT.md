# Phase 37 — Remaining CI Failures

**Date:** 2026-11-01  
**Branch / local HEAD:** `main` / `3ce4d32e66462505f5292cd7b5aaae5b390c525d`

## Baseline and evidence

The worktree initially had only `.github/workflows/ci.yml` modified. The
current CI and CodeQL workflows and Phase 30–36 reports were inspected;
`PHASE29_CI_FAILURE_DIAGNOSIS_REPORT.md` is absent, as previously noted in
Phase 30. Existing user work was preserved.

The reported structure-job runner diagnostic was:

```text
Unable to resolve action actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9cae0
```

The reference omitted a `0` before the final `e0` in the immutable SHA. The
official `actions/setup-python` `v7.1.0` commit endpoint returned
`6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` (40 characters). This exact full
SHA is already used by the CI Python tests/lint jobs and the deployment
workflow.

The supplied remote CodeQL logs report **“Code scanning is not enabled for
this repository.”** The CodeQL workflow was inspected: it keeps push/PR,
scheduled, and manual triggers; all three language matrix entries; least-
privilege `actions: read`, `contents: read`, and `security-events: write`;
`init` with `security-extended`; and the `analyze` action, which performs
analysis and uploads results. No genuine workflow defect was found, and
permissions were not broadened.

## Four reported failures

| Failure | Evidence and action | Local status | Remote status |
|---|---|---|---|
| Repository structure and deletion review | Runner could not resolve the truncated setup-python SHA. Replaced only the structure job's ref with the full verified immutable SHA. Strict validator passes. | **FIXED LOCALLY** | **NOT VERIFIED** — requires a new run |
| CodeQL `Analyze (actions)` | Remote error says repository code scanning is not enabled. Existing Actions matrix entry, initialization, permissions, and analyze/upload step are intact. | **BLOCKED** | **BLOCKED** — enable code scanning in repository settings, then rerun |
| CodeQL `Analyze (python)` | Same remote configuration error; Python matrix entry and workflow configuration are intact. | **BLOCKED** | **BLOCKED** — enable code scanning in repository settings, then rerun |
| CodeQL `Analyze (javascript-typescript)` | Same remote configuration error; JavaScript/TypeScript matrix entry and workflow configuration are intact. | **BLOCKED** | **BLOCKED** — enable code scanning in repository settings, then rerun |

## Required manual GitHub action

An authorized repository administrator must enable GitHub code scanning for
this repository in **Settings → Security → Code security and analysis → Code
scanning** (choose the existing advanced/CodeQL workflow setup). If an
organization or enterprise policy controls this setting, the administrator
must enable/authorize it there. Preserve the current advanced
`.github/workflows/codeql.yml` configuration. No repository setting was
changed in this phase.

## Changes and checks

- `.github/workflows/ci.yml` — corrected the structure job's setup-python
  action reference to the full 40-character `v7.1.0` commit SHA. Job names,
  triggers, permissions, and strict validator invocation are unchanged.
- `docs/architecture/PHASE37_REMAINING_CI_FAILURES_REPORT.md` — this report.
- `docs/plans/nexhaat-master-plan.md` — dated Phase 37 evidence entry.

| Check | Result |
|---|---|
| `python -m ruff check app/routes/portals.py` | **PASS** — Phase 29 import-order fix remains valid |
| `python scripts/validate_repository_structure.py --fail-on-review` | **PASS** — no source deletion/rename findings or missing targets/configuration |
| `git diff --check` | **PASS** |
| `.github/scripts/validate_github_config.rb` | **NOT RUN** — Ruby is unavailable |
| Other YAML validator (`actionlint`, PyYAML) | **NOT AVAILABLE** — no validator installed; none was added |
| GitHub workflow rerun and CodeQL results | **NOT RUN** — no push or workflow dispatch authorized; GitHub CLI is unauthenticated |

The workflow YAML itself was inspected but is not reported as parser-validated.
The three CodeQL failures remain blocked even though their workflow source is
configured correctly. Local validation does not establish a remote pass.

## Closure

The structure-action reference is **fixed locally**, pending remote
verification. The three CodeQL jobs are **BLOCKED** until repository/org
Code Scanning is enabled and a subsequent run succeeds. A new GitHub run is
required after an authorized commit; no push, dispatch, commit, merge,
deployment, production change, or GitHub settings change occurred.
