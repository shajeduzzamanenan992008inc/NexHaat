# Phase 23 — Proposed GitHub Ruleset Configuration

**Status:** Proposal only; not applied  
**Repository:** `shajeduzzamanenan992008inc/NexHaat`

This document is a safe proposed configuration. No GitHub repository setting,
branch protection rule, ruleset, secret, environment, or permission was
changed while preparing it.

## Recommended ruleset

| Setting | Proposal |
|---|---|
| Name | `main-protected-quality-gate` |
| Enforcement | `active` after owner review |
| Target | Branches |
| Include | `main` |
| Required pull request | Yes |
| Required approvals | At least 1 approval; require CODEOWNERS review when CODEOWNERS is enabled |
| Dismiss stale approvals | Yes, for new commits |
| Require approval of most recent push | Yes |
| Require conversation resolution | Yes |
| Require signed commits | Decide separately based on contributor workflow; do not enable without confirming signing coverage |
| Linear history | Decide separately; enabling it could conflict with the current merge workflow |
| Required status checks | `Tests (Python 3.11)`, `Tests (Python 3.12)`, `Tests (Python 3.13)`, `Tests (Python 3.14)`, `Python lint`, `React and Express checks`, `Repository structure and deletion review` |
| Optional additional checks | `GitHub Configuration Validation`, `Dependency Review`, `CodeQL Security Analysis`, and `NexHaat SBOM and Provenance` where GitHub makes their conclusions available as required checks |
| Bypass actors | Empty by default; document and minimize any emergency bypass actor |
| Deletion protection | Do not permit force-push or branch deletion for `main` |

## Why these checks

The CI workflow runs on pull requests and contains the strict structural
validator, Python test matrix, Python lint, and web build. The validator exits
non-zero for protected source deletions and renames when invoked with
`--fail-on-review`. These checks are only merge-blocking after this ruleset (or
equivalent branch protection) is applied.

The configuration-validation and dependency-review workflows are path/event
scoped, while CodeQL and SBOM/provenance have their own triggers. They should
not be described as mandatory until their exact GitHub check names and
conclusions are confirmed in a real pull request.

## Deployment boundary

Keep production deployment outside pull-request execution. The current
deployment workflow is triggered by a successful CI `workflow_run` from a
`push` to `main`, or by manual dispatch from `main` with the literal
`DEPLOY-PRODUCTION` confirmation. Require the `production` environment with
reviewers and restricted deployment branches before treating that boundary as
enforced.

## Actions and token permissions

Retain default read-only permissions for CI. Grant `id-token: write` only to
the Azure deployment job that uses OIDC. Do not grant repository write
permissions to pull-request jobs, and do not use `pull_request_target` for
untrusted code.

## Application procedure

1. Authenticate with an authorized GitHub account or organization-approved
   connector.
2. Record the current default branch, existing rulesets, required checks,
   environments, and Actions policy without changing them.
3. Compare actual check names from a representative pull request with this
   proposal.
4. Obtain explicit owner approval for every setting that changes merge or
   deployment behavior.
5. Apply the smallest ruleset change through the approved GitHub administration
   path, then verify enforcement with a safe pull request.

Until these steps are completed, the configuration is **PROPOSED**, not
**ENFORCED**.
