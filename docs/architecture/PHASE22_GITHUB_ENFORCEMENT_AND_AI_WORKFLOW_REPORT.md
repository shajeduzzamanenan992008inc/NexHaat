# Phase 22 — GitHub Enforcement and AI Workflow Report

**Date:** 2026-11-01  
**Status:** PARTIAL locally; GitHub governance items BLOCKED without
authentication

## Google AI Studio workflow

The current integration documents accurately describe Google AI Studio output
as reference material that must be quarantined, mapped, reviewed, and tested.
They preserve Flask as the marketplace authority and require additive
integration.

The enforcement layers are distinct:

| Layer | What it means in this repository | Status |
|---|---|---|
| AI instructions | `AGENTS.md`, `.github/instructions/*`, and the AI Studio guides tell an AI/developer what to inspect, preserve, and validate | **Documented; not an automatic enforcement mechanism** |
| Local checks | `scripts/validate_repository_structure.py`, TypeScript build/lint, Python tests/lint, Android tests, and whitespace checks run when a developer invokes them | **Available and locally tested where reported** |
| GitHub CI | `.github/workflows/ci.yml` runs on pushes, pull requests, and manual dispatch; its structure job invokes the validator with `--fail-on-review` | **Workflow definition verified; hosted status not verified** |
| Branch protection/rulesets | GitHub repository settings must require the intended CI checks and reviews before merge | **BLOCKED: unauthenticated GitHub CLI** |
| Human approval | Deletion/rename review, production deployment approval, provider enablement, staging validation, and external side effects require people and/or protected environments | **Required and documented** |
| External/staging checks | Authenticated browser/CORS/CSRF, OTP delivery, payment callbacks, live providers, device E2E, restore rehearsal, and production health need credentials or an isolated environment | **BLOCKED or NOT TESTED as listed below** |

`AGENTS.md` does **not** automatically enforce behavior in Google AI Studio.
It is repository guidance only when the consuming tool loads it. Enforcement
comes from executable local checks, GitHub Actions, repository rules, protected
environments, and human review.

## GitHub access and configuration verification

The following safe command was attempted without requesting or printing any
secret:

```text
gh auth status
You are not logged into any GitHub hosts.
```

Because GitHub CLI authentication was unavailable, the following are
**BLOCKED / NOT VERIFIED**, not guessed:

- default branch as reported by GitHub;
- branch protection rules or repository rulesets;
- required status checks;
- pull-request review count, code-owner review, or dismissal requirements;
- repository Actions permissions and fork approval policy;
- latest CI job/run status;
- repository environments, deployment approvals, and environment restrictions;
- repository secrets and variables.

The local Git state identifies `main` as the current branch and
`main...origin/main` as its local remote relation, but this is not a substitute
for GitHub repository configuration evidence.

## Locally verified workflow boundaries

### CI

`.github/workflows/ci.yml` uses read-only `contents` permissions, pinned
checkout/setup actions, `persist-credentials: false`, explicit timeouts, and
no deployment or secret references. The structure job invokes:

```text
python scripts/validate_repository_structure.py --fail-on-review
```

The default GitHub Actions failure behavior propagates non-zero command exits.

### Production deployment

`.github/workflows/main_nexhaat.yml` is bounded locally as follows:

- `workflow_run` deployment requires a successful CI run from a `push` to
  `main`; manual dispatch additionally requires `refs/heads/main` and the
  literal confirmation `DEPLOY-PRODUCTION`.
- The build checks out the exact tested commit SHA and uploads a short-lived
  artifact.
- Deployment requires the `production` environment and grants `id-token: write`
  only to the deploy job.
- No pull-request or fork event is a deployment trigger.

The workflow's repository/environment protections and Azure federated
credential configuration remain **NOT VERIFIED** because GitHub authentication
was unavailable. The workflow definition includes some version-tagged artifact
actions rather than full SHA pins; this is a documented supply-chain
hardening risk, not a setting changed in Phase 22.

## Final status matrix

| Area | Status | Evidence / limitation |
|---|---|---|
| Local structural validator and strict review gate | **PASS** | Disposable fixtures and current repository runs |
| CI trigger/permissions/checkout/setup/command/failure behavior | **PASS** | Direct workflow inspection |
| CI hosted execution status | **BLOCKED** | No authenticated GitHub access |
| Google AI Studio workflow documentation | **PASS** | Correctly separates guidance from executable enforcement |
| Automatic AGENTS.md enforcement in Google AI Studio | **NOT APPLICABLE / NOT CLAIMED** | Guidance is not a security boundary |
| Default branch from GitHub | **BLOCKED** | `gh auth status` unauthenticated |
| Branch protection/rulesets | **BLOCKED** | Not inspectable without GitHub access |
| Required checks and PR reviews | **BLOCKED** | Not inspectable without GitHub access |
| Actions permissions/settings | **BLOCKED** | Workflow files are inspectable; repository settings are not |
| Deployment workflow boundary | **PASS locally / BLOCKED remotely** | YAML boundary verified; environment/settings not verified |
| Staging/provider/credential-dependent checks | **BLOCKED or NOT TESTED** | No approved staging or provider credentials used |

## Remaining risks

1. GitHub may not require the CI structure-validation job, tests, lint, or web
   build before merge until branch protection/rulesets are confirmed.
2. GitHub Actions repository/fork approval settings and environment reviewers
   are unknown.
3. Live provider, authenticated staging, device, restore, and production
   health behavior remains unverified.
4. The validator intentionally does not resolve every supported language or
   runtime import mechanism; its limitations are recorded in the Phase 21
   report.
5. Version-tagged artifact actions in the deployment/SBOM workflows should be
   reviewed under the repository's SHA-pinning policy before a future
   infrastructure change.

## Preservation confirmation

No actual NexHaat source file was deleted or renamed to simulate testing.
No commit, push, merge, deployment, production configuration change, database
mutation, reset, clean, or destructive restore occurred.
