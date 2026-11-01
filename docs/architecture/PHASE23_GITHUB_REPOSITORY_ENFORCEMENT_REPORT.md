# Phase 23 — GitHub Repository Enforcement Report

**Date:** 2026-11-01  
**Status:** PARTIAL locally; remote GitHub enforcement BLOCKED

## Scope and safety

All Phase 5–22 reports were read before this audit. The six existing workflow
files were inspected directly. No GitHub setting was changed, and no secret
value or token was requested, printed, or stored. No commit, push, merge,
deployment, production restart, reset, clean, or destructive restore occurred.

## GitHub access

The repository is identified locally as `shajeduzzamanenan992008inc/NexHaat`.
The safe access attempt returned:

```text
gh auth status
You are not logged into any GitHub hosts.
```

`gh repo view` and the repository ruleset API could not run because the CLI is
unauthenticated. No authorized GitHub connector was available in this session.
Therefore the following are **BLOCKED / NOT VERIFIED**:

- GitHub-reported default branch;
- branch protection rules and rulesets;
- required status checks;
- pull-request approval, CODEOWNERS, stale-approval, and conversation rules;
- repository Actions permissions and fork approval policy;
- hosted CI conclusions and current check runs;
- repository environments, reviewers, deployment branches, secrets, and variables.

The local branch is `main` and tracks `origin/main`, but that is not proof of
the remote default branch or enforcement configuration.

## Workflow enforcement inspection

| Workflow | Trigger and boundary | Local result | Mandatory remotely? |
|---|---|---|---|
| `.github/workflows/ci.yml` | `push`, `pull_request`, manual dispatch; read-only permissions; pinned checkout/setup actions; strict validator, Python matrix, lint, web build | **PASS by source inspection** | **BLOCKED** until branch protection/rulesets are verified |
| `.github/workflows/config-validation.yml` | `.github/**` or `SECURITY.md` changes on push/PR, plus manual dispatch; read-only contents | **PASS by source inspection** | **BLOCKED**; not every PR triggers it |
| `.github/workflows/dependency-review.yml` | Non-draft pull requests; dependency review with moderate severity failure threshold | **PASS by source inspection** | **BLOCKED**; requiredness unknown |
| `.github/workflows/codeql.yml` | `main` push/PR, weekly schedule, manual dispatch; security-events write only for analysis | **PASS by source inspection** | **BLOCKED**; requiredness and hosted results unknown |
| `.github/workflows/sbom-provenance.yml` | Successful CI `workflow_run` from main push, scheduled/manual main paths; short artifact retention; opt-in attestation | **PASS by source inspection** | **BLOCKED**; not a PR merge gate by its trigger |
| `.github/workflows/main_nexhaat.yml` | Successful CI `workflow_run` from a main push or explicitly confirmed manual dispatch; protected `production` environment; exact tested SHA artifact | **PASS locally** | **BLOCKED**; environment reviewers/settings unknown |

### Pull-request deletion enforcement

The CI workflow does run on `pull_request`, and its
`structure-validation` job invokes:

```text
python scripts/validate_repository_structure.py --fail-on-review
```

The validator detects protected source deletions and renames and exits
non-zero. With ordinary GitHub Actions command semantics and no
`continue-on-error`, that job fails and the workflow conclusion fails. This
proves the local workflow path is **strict**, but it does not prove GitHub will
block merging until the job is required by branch protection or a ruleset.

### Unexpected deployment protection

The deployment workflow does not trigger on pull requests or fork events. Its
`workflow_run` path requires a successful CI run from a `push` to `main`; its
manual path requires `refs/heads/main` and the exact
`DEPLOY-PRODUCTION` input. The build checks out the exact tested SHA, and the
deploy job uses the `production` environment with OIDC permissions limited to
that job. These are **verified workflow boundaries**, not proof that the
remote environment has reviewers or restricted branches.

## Advisory versus mandatory

**Verified advisory/local behavior:** repository guidance, the proposed
ruleset document, workflow definitions, and any workflow that is not configured
as a required check.

**Potentially mandatory by workflow design but not remotely verified:** the
CI structure, Python, lint, and web jobs if a GitHub ruleset requires their
exact check names.

**Not proven mandatory:** CodeQL, dependency review, config validation, SBOM,
or deployment environment approvals.

The proposed configuration is recorded separately in
`PHASE23_PROPOSED_RULESET_CONFIGURATION.md` and was not applied.

## Phase 23 conclusion

| Control | Status |
|---|---|
| Workflow trigger and token-permission review | **PASS locally** |
| PR source-deletion strict validator path | **PASS locally** |
| Deployment trigger boundary | **PASS locally / BLOCKED remotely** |
| Default branch from GitHub | **BLOCKED** |
| Branch protection/rulesets | **BLOCKED** |
| Required checks | **BLOCKED** |
| PR review requirements | **BLOCKED** |
| Actions repository permissions | **BLOCKED** |
| Hosted CI status | **BLOCKED** |
