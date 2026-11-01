# NexHaat MEGA MEGA ULTRA Enterprise System — Release Notes

This package supersedes the previous `NexHaat-Ultra-Merged-GitHub-Config.zip`.

Highlights:
- Preserves the old NexHaat Master Copilot and Dependency Guardian material.
- Adds four specialist Copilot agents and scoped instruction files.
- Adds CodeQL analysis for Python, JavaScript/TypeScript, and GitHub Actions.
- Strengthens CI permissions, caching, timeouts, and check coverage.
- Adds PR and issue templates plus a root SECURITY.md policy.
- Gates Azure Production deployment on successful CI for main and repeats release
  verification before packaging.
- Uses the GitHub `production` environment and Azure OIDC.

Action pins were checked against current upstream release information on
2026-11-01. Some artifact and Azure actions remain exact version tags rather than
full commit SHAs; Dependabot is configured to monitor GitHub Actions updates.
See `.github/SECURITY-HARDENING-GUIDE.md` for details and required manual settings.

This package has been structurally and YAML-validated locally. It has not been run
inside the user's GitHub repository or Azure subscription.


## Enterprise Plus upgrade
- Fixed the production artifact-name mismatch by using the exact workflow-run head SHA
  consistently for artifact upload and download.
- Migrated Azure Login to verified immutable v3.1.0 and pinned Azure Web Apps Deploy
  v3.0.7 to its verified immutable commit.
- Added SPDX SBOM generation, source snapshot, SHA-256 checksums, 14-day artifact
  retention, and conditional signed SBOM attestation.
- Added GitHub configuration syntax and policy validation using Ruby's standard
  YAML parser; no extra runtime gem is required.
- Added four specialist agents: Database Steward, Performance/Reliability Engineer,
  AI Safety/Agent Governance, and API/Identity Architect.
- Added reusable Copilot prompts, path-scoped instructions, operational runbooks,
  and a CODEOWNERS template.
- Extended the Master Copilot Instructions with commerce invariants, data lifecycle,
  AI/MCP trust boundaries, accessibility, observability, and production-readiness rules.

## Validation boundaries
This ZIP has local structural/YAML/frontmatter validation. It has not been run in
the actual NexHaat GitHub repository, Azure subscription, or production environment.
Root package manifests and runtime assumptions must be checked against the complete
application repository before making checks mandatory or enabling production deploy.


## Current upstream action verification (2026-11-01)
- CodeQL Action v4.39.1 is an immutable, GitHub-verified release.
- Azure Login v3.1.0 is an immutable, GitHub-verified release and is used by the
  deployment workflow instead of the older v2 action.
- Azure Web Apps Deploy v3.0.7 is pinned to its verified full commit SHA.
- Anchore SBOM Action v0.24.3 is pinned to its verified full commit SHA.
- actions/attest v4.2.2 is pinned to its verified full commit SHA.
- upload-artifact v7.0.2 and download-artifact v8.0.2 are exact immutable releases;
  Dependabot is configured to track GitHub Actions updates.

Attestation is deliberately opt-in. Current GitHub plans support artifact attestations
for public repositories; private/internal repositories require GitHub Enterprise Cloud.
The SBOM workflow remains useful without enabling attestations.
