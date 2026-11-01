# NexHaat MEGA ULTRA GitHub Engineering System

This archive upgrades the prior merged NexHaat GitHub configuration. It preserves the
previous Master Copilot instructions and Dependency Guardian, adds specialist agents,
path-specific instructions, CodeQL analysis, repository contribution templates, a
security policy, and a CI-gated Azure production workflow.

## Package contents

```text
NexHaat/
├── SECURITY.md
└── .github/
    ├── copilot-instructions.md
    ├── dependabot.yml
    ├── SECURITY-HARDENING-GUIDE.md
    ├── NEXHAAT-GITHUB-SETUP.md
    ├── PULL_REQUEST_TEMPLATE.md
    ├── agents/
    │   ├── README.md
    │   ├── dependency-guardian.agent.md
    │   ├── security-architect.agent.md
    │   ├── quality-engineer.agent.md
    │   ├── architecture-reviewer.agent.md
    │   └── release-guardian.agent.md
    ├── instructions/
    │   ├── frontend.instructions.md
    │   ├── python-backend.instructions.md
    │   └── github-actions.instructions.md
    ├── ISSUE_TEMPLATE/
    │   ├── bug_report.yml
    │   └── feature_request.yml
    └── workflows/
        ├── ci.yml
        ├── codeql.yml
        ├── dependency-review.yml
        ├── config-validation.yml
        ├── sbom-provenance.yml
        └── main_nexhaat.yml

    ├── prompts/
    │   ├── repository-deep-audit.prompt.md
    │   ├── implement-feature-safely.prompt.md
    │   ├── threat-model-change.prompt.md
    │   ├── release-readiness.prompt.md
    │   ├── production-incident.prompt.md
    │   └── dependency-audit.prompt.md
    ├── runbooks/
    │   ├── production-release.md
    │   ├── incident-response.md
    │   ├── database-migration.md
    │   ├── security-incident.md
    │   ├── backup-restore.md
    │   └── ai-agent-safety.md
```

## Installation (PowerShell)

1. Back up the current `.github` folder and root `SECURITY.md` if one exists.
2. Put this ZIP in the NexHaat repository root.
3. From the NexHaat root run:

```powershell
Expand-Archive -LiteralPath ".\NexHaat-MEGA-ULTRA-GitHub-System.zip" -DestinationPath "." -Force
```

4. Review the Git diff before committing. Do not overwrite unrelated user changes.
5. Install on a feature branch and test workflows before merging to `main`.

## What changed from the previous package?

### Copilot and REA
- Expanded repository-wide Copilot engineering rules.
- Added targeted frontend, Python backend, and GitHub Actions instruction files.
- Added Security Architect, Quality Engineer, Architecture Reviewer, and Release
  Guardian custom agents.
- Preserved the existing Dependency Guardian.
- Added role-selection guidance and stricter review/approval boundaries.

### CI
- Preserved the existing Python version matrix and existing app/test/migration checks.
- Added optional npm lint, typecheck, and test scripts only when the scripts exist.
- Added explicit timeouts, least-privilege permissions, credentialless checkouts,
  modern action versions, and dependency-aware caches.
- First-party checkout, setup-python, setup-node, and CodeQL actions are pinned to
  verified full-length commit SHAs with release comments.

### CodeQL
- Added scheduled and PR/push scanning for:
  - Python
  - JavaScript/TypeScript
  - GitHub Actions workflows
- Uses CodeQL security-extended queries.
- Private repositories may need the proper Code Security entitlement.

### Dependency management
- Retains npm, pip, and GitHub Actions Dependabot ecosystems based on the supplied CI.
- Retains grouped non-major updates and cooldowns.
- Dependency Review checks pull requests for introduced vulnerabilities at Moderate
  severity or higher.

### Azure Production deployment
- The old independent push-to-production behavior has been replaced.
- Automatic deployment runs only after a successful `CI` workflow on a `push` to
  `main`.
- It checks out the exact commit associated with the successful CI run.
- It repeats production build/test checks before packaging.
- It uses a GitHub Environment named `production`, deployment concurrency, short-lived
  artifact retention, and OIDC authentication.
- Manual deployment is restricted to `main` and requires typing
  `DEPLOY-PRODUCTION`; build/test verification still runs.

## CRITICAL: Azure OIDC configuration must be reviewed

Adding `environment: production` can change the OIDC subject Azure sees. The Azure
Entra federated credential may need its subject updated or an additional credential
created for:

`repo:OWNER/REPOSITORY:environment:production`

Replace OWNER/REPOSITORY with the actual GitHub owner and repository. Preserve the
existing credential until the new environment-based OIDC path is verified. Do not
share secret values.

## Required GitHub repository settings

Follow `.github/SECURITY-HARDENING-GUIDE.md` and configure:
- Dependency Graph, Dependabot Alerts, and Dependabot Security Updates.
- Secret Scanning and Push Protection (where available).
- Code Scanning / Code Security (where available).
- Branch ruleset for `main`.
- Required checks after their first successful run.
- `production` Environment with branch restriction and reviewer approval where
  supported by the repository plan.

The exact availability depends on repository visibility and GitHub plan.

## Run Copilot Agents

### VS Code
Open Copilot Chat → Agent Selector → choose the required NexHaat agent. If it does
not appear, confirm `.github/agents/*.agent.md` paths and reload the workspace.

### Copilot CLI
Restart Copilot CLI after adding the files, then use `/agent` to select a specialist.
For subagent delegation, provide clear scope and expected output. The
`include-custom-instructions: true` field asks supported CLI subagents to include the
repository instructions.

### REA and MCP
Do not assume external REA or MCP automatically loads these files. Explicitly supply
the Master Copilot Instructions and relevant scoped instructions unless automatic
loading has been verified. Never give an agent broader MCP permissions than needed.

## Important limitations

- This is a GitHub engineering/configuration package; it does not implement marketplace
  features inside the NexHaat application.
- GitHub Actions do not automatically invoke Copilot custom agents.
- Secret scanning and push protection are enabled in GitHub repository settings,
  not by adding a YAML file.
- GitHub plans affect CodeQL, Dependency Review, and environment protection availability.
- The CI workflow assumes the same repository facts as the supplied workflow:
  root `requirements.txt`, `app`, `migrations`, `tests`, `run.py`, `wsgi.py`,
  root `package-lock.json`, and `npm run build`. Verify these paths before production.
- npm lint/typecheck/test run only if the corresponding scripts exist.
- No Docker ecosystem was added because the supplied archive does not prove a
  Dockerfile exists.
- Deployment success is not the same as application health. Add an authorized
  post-deployment smoke/health check once the real health endpoint is confirmed.
- A green workflow does not prove full production readiness, regulatory compliance,
  or Amazon-scale capacity.

## Recommended rollout

1. Install on a feature branch.
2. Run CI and repair any real project failures.
3. Validate CodeQL and Dependency Review availability/results.
4. Configure branch ruleset and GitHub security settings.
5. Create `production` environment and update Azure federated credential subject.
6. Test the automatic and manual deployment paths safely.
7. Review post-deployment health and rollback.
8. Only then make the required checks mandatory for `main`.


## MEGA enterprise additions

### New specialist agents
- Database Steward: migration safety, integrity, tenancy, backup and recovery.
- Performance and Reliability Engineer: measured performance, resilience and
  observability; no invented SLOs or load claims.
- AI Safety and Agent Governance: prompt injection, model data flow, tool/MCP
  permissions, privacy and AI cost controls.
- API and Identity Architect: API contracts, authentication, authorization,
  tenant isolation and webhook safety.

### Reusable Copilot prompts
Use `.github/prompts/*.prompt.md` for repository audit, safe feature implementation,
threat modeling, dependency audit, incident triage, and release readiness. These
prompts are starting points; review their scope and tool permissions for each task.

### Configuration validation
`config-validation.yml` parses GitHub YAML and Copilot frontmatter and rejects
mutable action references (`@main`, `@master`, `@HEAD`), `write-all` permissions,
and `pull_request_target` triggers. It is a policy guard, not a complete GitHub
workflow semantic validator. Review the action's actual behavior as well.

### SBOM and provenance
`sbom-provenance.yml` runs after successful CI on a push to `main`, weekly, or
manually on `main`. It creates an SPDX JSON SBOM, a source snapshot and checksums,
then uploads them for 14 days. For public repositories it creates a signed SBOM
attestation. The attestation job is opt-in through repository variable
`NEXHAAT_ENABLE_ARTIFACT_ATTESTATIONS=true`. Enable it for public repositories
on current GitHub plans, or for private/internal repositories only when the
repository has GitHub Enterprise Cloud entitlement and the organization approves.
Otherwise the SBOM and source snapshot are still generated and uploaded, but
attestation is skipped.

### Azure workflow corrections
- Artifact upload and download now use the same resolved source SHA for `workflow_run`
  and manual runs, avoiding a workflow-run artifact-name mismatch.
- Azure Login is pinned to immutable v3.1.0 and Azure Web Apps Deploy to v3.0.7.
- The workflow remains CI-gated and checks out the exact tested commit.
- Azure Environment/OIDC configuration and the actual Azure application settings
  still need validation in the owner's account.

### Additional scoped instructions
Database, API/identity, test, security, AI, performance, and commerce instructions
are loaded by Copilot where their `applyTo` patterns match. Confirm the paths against
the real repository and refine glob patterns if the source layout differs.

### CODEOWNERS
`.github/CODEOWNERS.example` is a template only. Replace placeholders with actual
GitHub owners, then copy to `.github/CODEOWNERS` to activate it. Do not commit the
placeholder template as an active CODEOWNERS file.
