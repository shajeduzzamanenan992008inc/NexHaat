# Phase 25 — GitHub Enforcement Readiness Report

**Date:** 2026-11-01
**Repository:** `shajeduzzamanenan992008inc/NexHaat`
**Overall status:** PARTIAL locally; remote enforcement BLOCKED

## Safety and scope

Phase 23 and the proposed ruleset were read before this review. The review was
read-only for GitHub and production. No branch protection, ruleset, secret,
environment, workflow, database, source feature, or user change was modified.
No commit, push, merge, deployment, restart, reset, clean, or destructive
restore occurred.

## Authentication and remote verification

The local checks were:

```text
git status --short --branch
## main...origin/main
gh auth status
You are not logged into any GitHub hosts.
```

Unauthenticated read-only GitHub REST attempts returned `404` for repository
metadata, `404` for the rulesets endpoint, and `401` for branch protection.
The metadata `404` may reflect repository visibility or access policy; the
ruleset `404` is not proof that no ruleset exists. These responses provide no
reliable remote default-branch or policy evidence. No GitHub MCP tool available
in the session advertises repository-settings, branch-protection, or ruleset
read access.

Because `gh` is unauthenticated, these remote facts are **BLOCKED / NOT
VERIFIED** and were not guessed:

- GitHub default branch;
- branch protection rules or repository rulesets;
- required status-check contexts;
- pull-request approval, CODEOWNERS, stale-approval, and conversation rules;
- Actions repository permissions and fork approval policy;
- hosted workflow conclusions and current check runs;
- `production` environment reviewers, deployment branches, secrets, and variables.

The local branch is `main` and tracks `origin/main`; this is only local
evidence, not proof of the remote default branch.

## Locally verified workflow evidence

| Workflow/job | Evidence | Status |
|---|---|---|
| `.github/workflows/ci.yml` → `tests` | PR/push/manual triggers; Python 3.11–3.14 matrix; dependency check, compile, migration heads, pytest, diff check; read-only contents | PASS by source inspection |
| `.github/workflows/ci.yml` → `lint` | `Python lint`; pinned setup; Ruff check; read-only contents | PASS by source inspection |
| `.github/workflows/ci.yml` → `web-build` | `React and Express checks`; locked npm install; lint/typecheck/test when defined; build; read-only contents | PASS by source inspection |
| `.github/workflows/ci.yml` → `structure-validation` | `Repository structure and deletion review`; invokes `python scripts/validate_repository_structure.py --fail-on-review` | PASS by source inspection |
| `.github/workflows/config-validation.yml` | Scoped to configuration/security-document changes and manual dispatch; not every PR | PASS locally; advisory until required remotely |
| `.github/workflows/dependency-review.yml` | Non-draft pull-request dependency gate with moderate severity threshold | PASS locally; requiredness BLOCKED |
| `.github/workflows/codeql.yml` | Python, JavaScript/TypeScript, and Actions analysis on configured triggers | PASS locally; hosted result/requiredness BLOCKED |
| `.github/workflows/sbom-provenance.yml` | Main/schedule/manual and successful CI `workflow_run`; not a normal PR merge gate | PASS locally; enforcement BLOCKED |

### Ruleset job-name consistency

The proposed ruleset names correspond to the CI job `name:` values:

```text
Tests (Python 3.11)
Tests (Python 3.12)
Tests (Python 3.13)
Tests (Python 3.14)
Python lint
React and Express checks
Repository structure and deletion review
```

Therefore the proposal is **internally consistent at the workflow-job level**.
GitHub may expose a workflow-prefixed required context such as
`CI / Tests (Python 3.11)`. The exact remote context names cannot be confirmed
without an authenticated repository or a real pull request, so the proposed
names are **conditionally consistent, not remotely verified**.

The local branch name `main` also matches the proposal's target, but the
remote default branch and ruleset target remain BLOCKED.

## Deletion/rename enforcement

The pull-request CI path invokes the strict validator without
`continue-on-error`. The validator reports protected source deletions and
renames and returns failure under `--fail-on-review`. This proves a local
failure path, not merge blocking: GitHub must require the exact status check in
branch protection or a ruleset before a failed run prevents merging.

## Deployment safety

`.github/workflows/main_nexhaat.yml` has no `pull_request` trigger. Its
automatic path requires a successful CI `workflow_run` from a `push` to
`main`, checks out the exact tested SHA, and deploys only after the
`production` environment gate. Its manual path requires `refs/heads/main` and
the exact `DEPLOY-PRODUCTION` confirmation. The deploy job alone receives
`id-token: write`; CI jobs retain read-only contents permissions.

These are verified workflow boundaries. Environment reviewers, allowed
deployment branches, Azure federated credentials, and remote Actions policy
are **BLOCKED**.

## Required manual actions for an authorized administrator

These instructions are intentionally not executed by this audit:

1. Open **Repository → Settings → Branches → Rulesets** and record existing
   rulesets before changing anything.
2. Confirm the repository default branch and target `main` only if that is the
   approved default.
3. Create or update a ruleset named `main-protected-quality-gate` in
   **Evaluate** mode first.
4. Require pull requests, at least one approval, stale-approval dismissal,
   approval of the most recent push, resolved conversations, and no force-push
   or branch deletion.
5. Add the seven CI contexts listed above. Use the actual workflow-prefixed
   context names shown by a representative pull request if GitHub displays
   them differently.
6. Require CODEOWNERS review only after `.github/CODEOWNERS` is approved and
   covers the intended owners.
7. Keep bypass actors empty or explicitly documented and minimized.
8. Under **Settings → Actions → General**, retain least-privilege
   read-only defaults and restrict fork approval according to organizational
   policy; do not grant write tokens to pull-request code.
9. Under **Settings → Environments → production**, verify required reviewers
   and restricted deployment branches. Do not trigger deployment as part of
   this audit.
10. After owner approval, change the ruleset from Evaluate to Active and
    verify one safe pull request containing a disposable, non-production
    validation failure.

## Exact recommended ruleset settings

The Phase 23 proposal remains unapplied. Recommended values are:

| Ruleset field | Recommended value |
|---|---|
| Name / enforcement | `main-protected-quality-gate` / `Evaluate` first, then `Active` only after review |
| Target | Branches; include `main` only after the administrator confirms the remote default branch |
| Pull requests | Required |
| Approvals | At least 1; dismiss stale approvals; require approval of the most recent push |
| Conversation resolution | Required |
| Required checks | `Tests (Python 3.11)`, `Tests (Python 3.12)`, `Tests (Python 3.13)`, `Tests (Python 3.14)`, `Python lint`, `React and Express checks`, `Repository structure and deletion review` |
| Check source | GitHub's actual required status context displayed for each matching CI job; record workflow prefix if present |
| Bypass | No bypass actors by default; document any emergency exception |
| Branch updates | Block force-push and branch deletion |
| CODEOWNERS | Require only after an approved `.github/CODEOWNERS` exists and ownership is reviewed |
| Signed commits / linear history | Leave unchanged until contributor signing and merge compatibility are confirmed |
| Production environment | Independently require reviewers and restrict deployment branches to the approved protected branch |

Do not make `config-validation`, `dependency-review`, CodeQL, or SBOM required
until their actual check contexts and trigger coverage are validated. In
particular, config validation is path-scoped, dependency review skips draft
PRs, and SBOM is not a PR gate.

## Status summary

| Control | Result |
|---|---|
| Local workflow triggers and job names | **PASS** |
| Local token permissions and checkout credential handling | **PASS** |
| Local PR deletion/rename failure path | **PASS** |
| Local deployment trigger boundary | **PASS** |
| Ruleset proposal consistency | **PARTIAL** — job-level names match; remote contexts unverified |
| GitHub default branch | **BLOCKED** |
| Branch protection/rulesets | **BLOCKED** |
| Required checks | **BLOCKED** |
| PR review requirements | **BLOCKED** |
| Actions settings and hosted runs | **BLOCKED** |
| Production environment enforcement | **BLOCKED** |
