# NexHaat Security Hardening — Required Repository Setup

This guide distinguishes configuration files from GitHub account/repository settings.
Committing YAML does not automatically enable every GitHub security feature.

## A. Enable GitHub security features

Open the NexHaat repository → **Settings → Security / Advanced Security** and review:

1. Dependency Graph.
2. Dependabot Alerts.
3. Dependabot Security Updates.
4. Secret Scanning.
5. Push Protection.
6. Code Scanning / Code Security for CodeQL.

Availability depends on repository visibility, account/organization plan, and GitHub
product entitlements. Public repositories have broader free security feature access;
some private-repository features require an eligible paid security plan.

## B. Protect the default branch

Create a repository Ruleset or branch protection rule for `main`:

- Require pull requests for changes.
- Require the CI checks actually produced by this repository.
- Require Dependency Review on dependency-changing PRs.
- Require CodeQL once the repository is eligible and its workflow succeeds.
- Require conversation resolution.
- Block force pushes and branch deletion.
- Restrict bypass permissions to the smallest necessary set.
- Do not mark checks as required until they have completed successfully at least once.

Select exact check names from the completed GitHub Actions runs; matrix jobs can have
expanded names such as `Tests (Python 3.14)`.

## C. Protect the Production environment

Create a GitHub Environment named exactly:

`production`

Configure:
- Deployment branch/tag rule: protected `main` only.
- Required reviewers for production deployments where the repository plan supports it.
- Prevent self-review where a second reviewer is available.
- Store production-only secrets in the environment if you intentionally migrate them
  from repository secrets, then update the workflow references accordingly.

On GitHub Free, required reviewers and some protection rules are available for public
repositories; private-repository availability depends on plan.

## D. Azure OIDC change — IMPORTANT

The upgraded deployment workflow references the GitHub Environment `production`.
When a GitHub Environment is used, the OIDC subject commonly changes from a branch
subject such as:

`repo:OWNER/REPOSITORY:ref:refs/heads/main`

to an environment subject:

`repo:OWNER/REPOSITORY:environment:production`

The Azure Entra ID federated credential must trust the exact subject emitted by the
workflow. Before expecting deployment to work, add/update the federated credential
for the real NexHaat owner/repository and `production` environment. Verify the issuer,
audience (`api://AzureADTokenExchange` where applicable), subject, tenant, client,
and subscription. Do not paste credential values into chat or commit them.

Existing secret names in the workflow are preserved. This ZIP does not verify that
the Azure federated credential or secret values are valid.

## E. Deployment gate behavior

Automatic production deployment now starts only when:
- The workflow named `CI` completes successfully.
- The completed CI run was caused by a `push`.
- The pushed branch is `main`.

The privileged workflow does not check out pull-request code. It checks out the exact
main commit associated with the successful CI run and repeats production build/test
verification before packaging.

A manual deploy can be requested only from `main` and requires the exact confirmation
string `DEPLOY-PRODUCTION`; the same production build/test verification runs again.
The `production` Environment rules remain an independent protection layer.

## F. CodeQL and Dependency Review eligibility

- CodeQL scans Python, JavaScript/TypeScript, and GitHub Actions workflow code.
- Dependency Review checks newly introduced vulnerable dependencies in pull requests.
- Private repositories may need the appropriate GitHub Code Security / Advanced
  Security entitlement for code scanning or dependency review.
- GitHub-hosted `ubuntu-latest` runners are used. Node 24-based action releases require
  a sufficiently recent Actions runner; GitHub-hosted runners are maintained by GitHub.
- Native secret scanning and push protection are repository settings, not workflows
  created by this ZIP.

## G. Action pinning policy

The primary first-party actions in CI and CodeQL are pinned to verified full commit
SHAs with release comments. Artifact and Dependency Review actions are pinned to exact
release tags in this package; Dependabot watches GitHub Actions updates. GitHub
recommends full-length commit SHA pinning as the strongest immutable reference.
When changing a pin, verify the SHA belongs to the official action repository and
review the release before updating it.

## H. First validation sequence

1. Back up the current `.github` folder and `SECURITY.md`.
2. Install this archive on a feature branch, not directly on `main`.
3. Review the complete diff, especially the changed Azure deployment workflow.
4. Confirm the root `requirements.txt`, `package-lock.json`, Python app paths, and
   npm scripts still match the repository.
5. Run the CI workflow.
6. Confirm CodeQL and Dependency Review are eligible and successful.
7. Configure the `production` environment and Azure OIDC federated subject.
8. Test deployment in a safe environment before production.
9. Enable required status checks only after successful runs.
10. Review the first release and verify application health and rollback readiness.

## Official references

- Repository security quickstart: https://docs.github.com/en/code-security/getting-started/quickstart-for-securing-your-repository
- Secret scanning: https://docs.github.com/en/code-security/how-tos/secure-your-secrets/detect-secret-leaks/enable-secret-scanning
- Push protection: https://docs.github.com/en/code-security/how-tos/secure-your-secrets/prevent-future-leaks/enable-push-protection
- Secure use of GitHub Actions: https://docs.github.com/en/actions/reference/security/secure-use
- Environments and deployment protection: https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
- CodeQL workflow configuration: https://docs.github.com/en/code-security/reference/code-scanning/workflow-configuration-options
- Dependency Review Action: https://github.com/actions/dependency-review-action


## I. SBOM and signed provenance

- `sbom-provenance.yml` creates an SPDX JSON SBOM and a source snapshot from the
  exact successful CI-tested `main` SHA, then uploads the files for 14 days.
- The provenance job generates an SBOM attestation for the snapshot and SBOM.
- Public repositories can use artifact attestations on current GitHub plans.
- Private/internal repositories require GitHub Enterprise Cloud for artifact
  attestations. The private-repository job is skipped unless the repository variable
  `NEXHAAT_ENABLE_PRIVATE_ATTESTATIONS` is explicitly set to `true` by an authorized
  owner after entitlement verification.
- The SBOM artifact is not the deployed Azure package. It is a supply-chain inventory
  and source snapshot for traceability. Do not confuse these artifacts.
- SBOM generation is not a vulnerability scan; use CodeQL, Dependency Review,
  Dependabot Alerts, and approved security testing for their respective purposes.

## J. Configuration validation

The config validation job parses `.github` YAML and Copilot Markdown frontmatter.
It also blocks mutable action references, `write-all`, and `pull_request_target`.
It is a lightweight guardrail, not a full semantic validator, action sandbox, or
proof that a workflow is safe. A human must still review workflow changes.

## K. Action runtime and pin maintenance

- GitHub-hosted runners are used. Node 24 actions require a sufficiently recent
  Actions runner; self-hosted runners must be upgraded before using these actions.
- Reviewed Azure action references are Azure Login v3.1.0 and Web Apps Deploy v3.0.7.
- Recheck action releases and security advisories before updating pins. Dependabot
  monitors action version changes, but a human must verify the upstream repository,
  release integrity, permissions, and behavior before merging.
