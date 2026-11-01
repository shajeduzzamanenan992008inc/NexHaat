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
The Azure deployment workflow listens for a successful `CI` workflow caused by a push
to `main`. It checks out the exact `workflow_run.head_sha`, repeats production checks,
packages the artifact, and deploys through OIDC.

## Manual path
Use `workflow_dispatch` on `main` only and enter the exact phrase
`DEPLOY-PRODUCTION`. This is not a substitute for review or Environment approval.

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
