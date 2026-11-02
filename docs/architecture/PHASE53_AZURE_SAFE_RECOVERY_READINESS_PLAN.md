# Phase 53 — Azure Safe Recovery Readiness Plan

**Date:** 2026-11-02  
**Incident:** GitHub Actions run `41369767391`; OneDeploy
`bf08d173-7e5d-455c-8898-c34fa8e4de9e`  
**Readiness:** **BLOCKED** — Phase 52 root cause is **UNKNOWN** and the failed
deployment state and Azure service health have not been independently
verified.

## Decision

No remediation, retry, restart, slot swap, or deployment is proposed. The SCM
restart is only a likely proximate mechanism based on user-provided error text;
there is no evidence to select a cause-specific production change. Continue
read-only evidence collection through
[`PHASE50_AZURE_ADMIN_DIAGNOSTIC_HANDOFF.md`](PHASE50_AZURE_ADMIN_DIAGNOSTIC_HANDOFF.md).

## Required gates before a future, separately authorized deployment

### 1. Evidence and incident closure

- [ ] Obtain the GitHub run timeline and redacted deployment logs, including
  run/source SHA, job/step UTC timestamps, artifact name/digest, and OneDeploy
  response.
- [ ] Obtain Azure Activity Log, Resource Health/platform restart events,
  Kudu/SCM deployment history, OneDeploy details, and available resource/Oryx
  diagnostics for the same UTC window.
- [ ] Determine whether any event overlapped; record supporting and
  contradictory evidence. Do not infer overlap.
- [ ] Have the Azure/App Service owner document and approve any cause-specific
  remediation. If root cause remains UNKNOWN, keep recovery blocked.

### 2. Target and artifact verification

- [ ] Confirm current App Service/Production-slot health and the last known
  deployed release without changing the slot.
- [ ] Verify the exact remote source commit and artifact identity against the
  successful CI build; inspect the artifact manifest and integrity evidence.
- [ ] Confirm the App Service's effective Python stack/startup configuration
  and relevant Oryx/deployment settings through authorized read-only access.
  The local Phase 48 source inspection found Python 3.14 in both the workflow
  and `runtime.txt`, but this is not remote runtime verification.
- [ ] Review database migration compatibility and current data-write state
  before any future promotion or rollback decision.

### 3. Approval and execution boundary

A future release/recovery requires separate explicit approval from the
service/release owner and authorized Azure administrator, an identified
tested commit and artifact, a reviewed remediation, a release window, and
documented stop/rollback conditions. This document does not authorize or
execute any production operation.

### 4. Post-recovery verification, if separately authorized later

- [ ] Confirm the authorized deployment's exact run, commit, artifact digest,
  target slot, and deployment result.
- [ ] Verify `/health/live` and `/health/ready` and application logs.
- [ ] Exercise approved low-risk smoke checks for sign-in, catalog, and
  customer/seller/admin access; use sandbox-only payment checks if applicable.
- [ ] Check database migration state, error rates, and App Service/SCM health.
- [ ] Record UTC completion time and observed health; stop and escalate on
  unexpected errors rather than retrying automatically.

## Rollback considerations

Follow the repository's deployment architecture and release-readiness
guidance: identify the previous known-good artifact and exact SHA, verify
database migration compatibility, retain approved configuration in its
authorized secret/configuration source, and define health checks. Do not
blindly reverse migrations after writes; prefer a reviewed compatible
forward-fix when rollback is not data-safe. No known-good artifact, rollback
readiness, Azure health, or restore path for this incident has been
independently verified.

## Owners and current status

| Owner | Required action | Status |
|---|---|---|
| GitHub repository operator | Provide redacted Actions run metadata/logs and artifact identity | **BLOCKED** — authenticated access unavailable |
| Azure subscription/App Service administrator | Provide UTC-correlated Activity, Resource Health/platform, Kudu/SCM, OneDeploy, runtime/Oryx, and resource evidence | **BLOCKED** — authorized Azure diagnostic access unavailable |
| NexHaat service/release owner | Review evidence, accept the proposed recovery plan, and separately authorize any release action | **NOT STARTED** — no cause-specific plan is supported yet |

**Production action performed:** **NONE**. This readiness plan requires
evidence and separate human approval; it does not recommend a retry while the
cause and current deployment state remain unknown.
