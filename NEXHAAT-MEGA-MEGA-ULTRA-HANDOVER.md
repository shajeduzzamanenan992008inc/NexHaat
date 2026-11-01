# NexHaat MEGA MEGA ULTRA — Final Handover

## Purpose
This is the next engineering-governance layer for NexHaat. It combines the previous
MEGA ULTRA package with additional agents, targeted instructions, reusable prompts,
runbooks, configuration validation, SBOM generation, and conditional provenance.

## Install safely
1. Back up `.github/` and `SECURITY.md`.
2. Extract this ZIP at the repository root on a feature branch.
3. Review `git status` and the complete diff before committing.
4. Confirm real repository manifests and all assumed app paths.
5. Run `GitHub Configuration Validation`, CI, CodeQL, Dependency Review and SBOM.
6. Configure branch rules, security settings, `production` Environment, and Azure OIDC.
7. Only after successful test runs should the relevant status checks become required.
8. Test Azure deployment with a safe release procedure before production use.

## Important production correction
The Azure artifact upload/download now share the same commit expression. Azure Login
uses v3.1.0 and Azure Web Apps Deploy uses v3.0.7. The workflow still needs a real
Azure federated credential matching `repo:OWNER/REPOSITORY:environment:production`.

## Files are not platform switches
The repository owner must still enable Dependency Graph, Dependabot Alerts,
Dependabot Security Updates, Secret Scanning, Push Protection, Code Scanning,
branch protection, Environment reviewers, and Azure identity settings where available.

## Optional signed provenance
Set repository variable `NEXHAAT_ENABLE_ARTIFACT_ATTESTATIONS` to `true` only after
confirming the repository's GitHub plan supports attestations. Public repositories
can use the feature on current plans; private/internal repositories require GitHub
Enterprise Cloud. Without this variable, SBOM and source snapshot artifacts are still
generated; the attestation job is skipped.

## Constraints
- Copilot agents are invoked through supported Copilot surfaces; GitHub Actions do
  not automatically invoke them.
- Private-repository artifact attestation requires GitHub Enterprise Cloud.
- The SBOM source snapshot is not the production deployment package.
- No Docker ecosystem was assumed without a verified Dockerfile.
- No production health endpoint was invented.
- The application itself is not changed by this GitHub configuration pack.
- A green check does not prove complete security, compliance, availability, or scale.
