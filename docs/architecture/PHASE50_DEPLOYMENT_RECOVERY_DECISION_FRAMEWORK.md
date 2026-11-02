# Phase 50 — Deployment Recovery Decision Framework

**Incident:** GitHub Actions run `41369767391`; reported OneDeploy
`bf08d173-7e5d-455c-8898-c34fa8e4de9e`; reported failure
`Deployment has been stopped due to SCM container restart.`  
**Current root cause:** **UNKNOWN**. Phase 48–49 evidence is limited to
user-provided run details and local workflow/runtime inspection; no authenticated
GitHub or Azure platform logs were available.

## Decision gates

### 1. Root cause confirmed and resolved

- Preserve the source evidence, UTC event timeline, affected artifact identity,
  and confirmation that the proposed fix addresses the triggering event.
- Prepare a separately reviewed recovery/release plan: owner approval,
  deployment target/slot, exact tested commit and artifact, health checks,
  rollback/roll-forward decision, and stop conditions.
- Confirm database migration compatibility and current application health
  before any release decision.
- This state is not reached until evidence and authorization exist. This
  framework does not execute the plan.

### 2. Root cause identified but unresolved

- Record the confirmed cause, responsible system/owner, impact, and specific
  remediation required.
- Identify approvals, risks, observability, and verification needed to close
  the issue.
- Keep production unchanged until the owner authorizes a reviewed remediation.

### 3. Evidence inconclusive

- Mark the cause **UNKNOWN**; list contradictory and missing evidence.
- Continue read-only diagnostics with the Azure administrator handoff checklist.
- Do not infer deployment overlap from the SCM-restart message alone.
- Do not recommend a production retry while failure state or trigger remains
  unclear.

### 4. Azure or GitHub access unavailable

- Mark the investigation **BLOCKED** and identify the missing access/source.
- Provide `PHASE50_AZURE_ADMIN_DIAGNOSTIC_HANDOFF.md` to an authorized operator.
- Request only redacted records and UTC timestamps—not secrets, credentials,
  connection strings, or unrestricted environment dumps.
- Do not change settings or attempt to bypass access controls.

## Mandatory no-action boundary

No automatic retry, restart, stop/start, slot swap, redeployment, workflow
dispatch, identity/configuration change, or database action is authorized by
this document. A later production action requires separate explicit
authorization and its own reviewed release/recovery plan.

## Existing repository guidance

Use the Stage 10 operations runbook for recovery controls and isolated restore
requirements. The deployment architecture requires an identified artifact and
retained known-good release before promotion. Its rollback guidance calls for
health verification and migration-compatibility review; no Azure rollback or
restore has been verified or performed for this incident.
