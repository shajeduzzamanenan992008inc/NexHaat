# NexHaat Production Release Runbook

## Preconditions
- A reviewed pull request is merged to protected `main`.
- Required CI, configuration validation, CodeQL, and dependency checks pass.
- The release SHA is the exact tested commit.
- Database migration and rollback plan is reviewed.
- No unresolved critical/high issue is accepted without a documented owner and approval.
- Production Environment restrictions and required reviewers are configured.
- Azure Entra federated credential trusts the exact GitHub `production` environment subject.

## Automatic path
`.github/workflows/main_nexhaat.yml` runs on every push to `main`, builds the Python
artifact from the pushed commit, and deploys it to the `NexHaat` App Service
`Production` slot through Azure OIDC. The `deploy` job declares the GitHub Environment
`production`, so each run creates a commit-specific GitHub deployment record whose
state follows the real Azure deployment steps.

Known limitation: the CI-success `workflow_run` gate and the typed
`DEPLOY-PRODUCTION` confirmation described in earlier revisions of this runbook are
not present in the current workflow, which was regenerated from the Azure portal
Deployment Center on 2026-11-02. Until the gate is restored by the owner, a push to
`main` deploys without a separate CI-success precondition.

## Manual path
Use `workflow_dispatch` on `main` only. The workflow deploys the selected ref and does
not itself block a non-`main` ref, so selecting another branch would deploy
unreviewed code. This is not a substitute for review or Environment approval.

## Deployment status signals
These are separate signals; record each one separately instead of inferring one
from another:
- GitHub Actions run conclusion (build and deploy steps).
- GitHub Environment `production` deployment record (commit, state, approver).
- Azure App Service deployment operation result.
- Application health after deploy.

A green Actions run does not by itself prove the Environment deployment record or
the live application state, and vice versa.

## After deployment
- Verify the deployment run and artifact SHA.
- Run an approved health/smoke check against the confirmed health endpoint.
- Verify sign-in, catalog, cart, checkout sandbox, order history, seller and admin paths.
- Inspect error rate, latency, logs, database connectivity, and background jobs.
- Record release SHA, time, result, and known risks.

## Rollback
Rollback only through a reviewed, known-good artifact or documented Azure rollback
procedure. Database rollback may not be safe after new writes; prefer a compatible
forward fix where necessary. Record evidence and notify the owner.
