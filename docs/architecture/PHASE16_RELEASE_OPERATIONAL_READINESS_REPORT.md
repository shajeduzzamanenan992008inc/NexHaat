# Phase 16 — Release Engineering and Operational Readiness

**Date:** 2026-11-01  
**Status:** PARTIAL / BLOCKED for staging and production verification  
**Scope:** Local release audit and isolated backup rehearsal only. No commit,
push, merge, deployment, restart, production database/configuration change,
real payment, real OTP, or real notification was performed.

## Executive summary

All existing GitHub Actions workflows were inspected. The CI workflow retains
Python tests/lint/build checks, the deployment workflow checks out the exact
successful `workflow_run` SHA and requires an explicit manual confirmation for
manual production dispatch, and separate CodeQL, dependency-review,
configuration-validation, and SBOM/provenance workflows are present. No workflow
was modified.

The local SQLite backup command completed successfully to an isolated session
file. A restore rehearsal was **BLOCKED** because the repository has no
documented disposable restore database/environment and the restore command
explicitly targets the configured application database. Production was not used
as a substitute. Staging availability could not be confirmed from this local
workspace and is therefore **BLOCKED**.

## CI/CD audit

| Workflow | Evidence | Status |
|---|---|---|
| `.github/workflows/ci.yml` | Python 3.11–3.14 matrix, pip check, compileall, migration-head check, pytest, Ruff, npm ci, frontend lint/typecheck/test/build, timeouts, concurrency, read-only permissions | **PASS by source inspection** |
| `.github/workflows/main_nexhaat.yml` | Exact tested SHA checkout, repeated checks, short artifact retention, environment-file rejection, protected `production` environment, Azure OIDC only in deploy job, deployment concurrency | **PASS by source inspection** |
| `.github/workflows/codeql.yml` | Python, JavaScript/TypeScript, and Actions analysis with security-extended queries and security-events write only in the analysis job | **PASS by source inspection** |
| `.github/workflows/dependency-review.yml` | Pull-request dependency review with moderate severity gate | **PASS by source inspection** |
| `.github/workflows/sbom-provenance.yml` | SHA-pinned checkout, exact CI-tested source selection, SPDX SBOM, SHA256 sums, short retention, opt-in attestation | **PASS by source inspection** |
| `.github/workflows/config-validation.yml` | YAML/Copilot-frontmatter/workflow safety validation script | **PASS by source inspection** |

Live GitHub run conclusions, repository Environment reviewers, branch
protections, Azure federated-credential configuration, and secret values were
not accessed. Secret names were not exposed beyond their existing workflow
references.

## Release-readiness checklist

| Area | Status | Evidence / required gate |
|---|---|---|
| Exact release SHA and artifact identity | PASS by workflow design | `workflow_run.head_sha`, named artifact, short retention |
| Environment variables | PARTIAL | `production-check` reports missing local production settings |
| Database migrations | PASS locally / operator gate | CI checks migration heads; production migration approval and backup remain required |
| Authentication and OTP | PASS by source/tests / staging gate | Existing Flask/CSRF/OTP controls preserved; browser/provider checks not run |
| CORS and CSRF | PARTIAL | Source controls exist; deployed origin/cookie/preflight behavior needs staging |
| HTTPS and secure cookies | PARTIAL | Production checks enforce requirements; live hosting configuration not verified |
| Static assets | PASS locally | Web build succeeds; deployment artifact flow is present |
| Logging and error monitoring | PARTIAL | Application logging/AI metadata hooks exist; live dashboards and alert routes not verified |
| Health checks | PASS by source inspection | `/health/live` and `/health/ready` exist; live endpoint not queried |
| Dependency security | PARTIAL | Lockfile, dependency review, CodeQL, and SBOM workflows exist; live results not checked |
| Backup | PASS for isolated local SQLite backup | Backup verified at the session artifact path |
| Restore | BLOCKED | No disposable restore target/environment was available |
| Rollback | PASS as documented procedure / NOT TESTED | Runbook requires known-good artifact and compatible migration review |
| Staging | BLOCKED | No confirmed staging URL, credentials, or approved test data in workspace |

## Backup and restore rehearsal

### Executed

Command:

```powershell
python -m flask --app run.py backup-db --to C:\Users\enan9\.copilot\session-state\c67885d9-0c60-477b-80ea-1612d94e67c7\files\phase16-local-backup.sqlite3
```

Result: **PASS** — the application reported “Backup verified and written”; the
isolated SQLite backup is 913,408 bytes. It was written outside the repository
and is not a production backup.

### Not executed

The restore command was not run. `restore-db --help` confirms it requires both
`--from FILE` and explicit `--confirm-target`, and the implementation restores
over the configured database. No disposable application database, isolated
environment, or approved restore target was available. This is **BLOCKED**, not
evidence of restore readiness.

Proposed safe rehearsal: provision a disposable SQLite/PostgreSQL database with
synthetic data, apply migrations, create a verified backup, restore into a
separate empty target, validate schema/row counts/foreign keys and representative
commerce records, record duration and backup identity, then destroy only that
disposable environment after approval.

## Monitoring and operations

**PASS by source inspection:** liveness/readiness routes, opt-in `Server-Timing`,
database-size checks, backup verification, audit events, and bounded configured
timeouts are present.

**PARTIAL / NOT TESTED:** no live monitoring dashboard, alert route, background
job queue health, PostgreSQL health, Azure runtime health, CDN/media health, or
staging smoke check was verified. No alert or notification was sent.

## Rollback plan

1. Identify the deployed release SHA and verified artifact name.
2. Stop promotion and use the previously known-good artifact through the protected
   deployment environment.
3. Do not blindly reverse database migrations after new writes; prefer a reviewed
   compatible forward fix when rollback is not data-safe.
4. Restore environment configuration from the approved secret/configuration
   source, without exposing values.
5. Verify `/health/live`, `/health/ready`, sign-in/OTP sandbox behavior, catalog,
   cart, checkout sandbox, order history, seller, and admin paths.
6. Record SHA, artifact, time, verification output, and unresolved risk.

No rollback was executed.

## Verification

| Check | Result |
|---|---|
| `npm run lint` | **PASS** |
| `npm run build` | **PASS** — after Phase 15 lazy loading; Vite Admin chunk warning remains |
| `python -m pytest -q` | **PASS** — 305 passed in 419.55s (6:59) |
| `python -m ruff check .` | **FAIL** — pre-existing `app/routes/portals.py` import ordering |
| `python -m flask --app run.py production-check` | **FAIL / EXPECTED LOCAL GATE** — production environment variables and services are absent |
| Local SQLite backup rehearsal | **PASS** |
| Restore rehearsal | **BLOCKED** — no disposable target |
| `.\android\gradlew.bat -p android :app:test --no-daemon` | **PASS** — `BUILD SUCCESSFUL` in 2m 59s; existing warnings remain |
| Live GitHub Actions results | **NOT TESTED** |
| Staging browser/device verification | **BLOCKED** |
| Production verification/deployment | **NOT TESTED and prohibited for this task** |

## Outstanding risks

- Staging origin, test accounts, mock provider configuration, and device/emulator
  access are not available.
- Production readiness remains open for PostgreSQL, HTTPS/CORS/cookies, mail,
  payment credentials, invoice font, ClamAV/S3 media, WAF/ingress, scheduled
  backups, monitoring, and restore evidence.
- The existing Ruff failure is outside the Phase 15 source change and was not
  silently edited.
