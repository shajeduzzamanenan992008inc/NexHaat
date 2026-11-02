# Phase 49 — Azure Deployment Evidence Report

**Date:** 2026-11-02  
**Repository:** `D:/FTP/NexHaat`  
**GitHub Actions run:** `41369767391`  
**Reported workflow:** `Build and deploy Python app to Azure Web App - NexHaat`  
**Reported source commit:** `97bc4bc6368eda6c29d98331aee5bfebfa60c301`  
**Reported target:** App Service `NexHaat`, Production slot  
**Reported OneDeploy ID:** `bf08d173-7e5d-455c-8898-c34fa8e4de9e`  
**Overall status:** **BLOCKED / PARTIAL** — supplied deployment details and
local Phase 48 evidence were reviewed. No authenticated GitHub or Azure
diagnostic access was available, so no independent event correlation or
underlying root cause could be established.

## 1. Baseline and evidence sources

| Source | Access / result |
|---|---|
| Phase 48 diagnostic report and roadmap entry | **PASS** — read from the local worktree |
| Phase 49 run ID, workflow, source SHA, OneDeploy ID, failure text | **USER-PROVIDED** — recorded as supplied, not independently validated |
| GitHub CLI | **BLOCKED** — `gh auth status` reports `GH_AUTH=UNAVAILABLE`; `gh run view 41369767391` cannot retrieve run metadata or logs |
| Azure CLI / Azure PowerShell | **BLOCKED** — `az` and `Connect-AzAccount` are not available in this environment |
| Azure Portal / Activity Log / App Service diagnostics | **BLOCKED** — no authorized read-only Azure session was available |
| Live Azure state | **NOT TESTED** — no settings, logs, resources, or deployment records were queried |

No run log, Azure Activity event, OneDeploy record, platform event, or
management-operation record was retrieved. The exact error and deployment ID
are therefore not independently confirmed in Phase 49.

## 2. UTC timeline

Exact event timestamps could not be collected because neither GitHub run
metadata nor Azure deployment/platform records were accessible.

| UTC time | Event | Evidence/status |
|---|---|---|
| Unknown | GitHub Actions run `41369767391` started | Run ID supplied by user; timestamp **BLOCKED** |
| Unknown | Build and artifact download completed | Reported by user; job logs **NOT TESTED** |
| Unknown | Azure OIDC login succeeded | Reported by user; job log **NOT TESTED** |
| Unknown | OneDeploy `bf08d173-7e5d-455c-8898-c34fa8e4de9e` started | Supplied deployment ID; Azure record **NOT TESTED** |
| Unknown | Deployment stopped with `Deployment has been stopped due to SCM container restart.` | User-provided error; raw action/Kudu log **NOT TESTED** |
| Unknown | Any overlapping deployment, scale/restart, configuration change, or platform operation | **UNKNOWN** — no GitHub/Azure event timeline |

Without UTC timestamps and a common event window, correlation or overlap
analysis cannot be performed.

## 3. Confirmed facts vs. classification

“Confirmed” below means confirmed from the specified evidence source; it does
not imply independent verification of a remote event.

| Finding | Classification | Evidence and limits |
|---|---|---|
| User reports OneDeploy stopped with the SCM-container-restart message | **CONFIRMED as user-provided evidence** | Supplied error text; raw run/deployment logs unavailable |
| Reported run and OneDeploy identifiers | **CONFIRMED as user-provided identifiers** | Run `41369767391`; deployment ID `bf08d173-7e5d-455c-8898-c34fa8e4de9e` |
| SCM restart interrupted deployment | **LIKELY proximate mechanism** | Consistent with the reported message, but not verified in the underlying logs |
| A second deployment or management operation caused the restart | **UNKNOWN** | No GitHub Actions history or Azure Activity Log available |
| Platform recycle/maintenance, resource pressure, storage exhaustion, Oryx interruption, or timeout caused it | **UNKNOWN** | No platform events, resource metrics, Oryx output, or deployment logs |
| Application code caused the SCM restart | **NOT ESTABLISHED** | No application or SCM diagnostics were available |
| Any Phase 49 production setting or resource changed | **CONFIRMED: NO** | Investigation was read-only; no Azure diagnostic session or write operation was used |

The cause of the restart remains **UNKNOWN**. No overlap-based explanation
should be assumed unless Azure/GitHub timestamps and event records prove it.
This report does not recommend a production retry.

## 4. Missing evidence and responsible access

An authorized GitHub repository operator can obtain:

1. Run `41369767391` metadata, source SHA, workflow URL, job conclusions,
   UTC job/step start and completion times, and the complete deployment-step
   log (with secrets and sensitive environment output excluded).
2. The uploaded artifact name and file manifest, plus any subsequent or
   overlapping deployment workflow runs.

An authorized Azure subscription/App Service operator can obtain:

1. App Service and App Service Plan **Activity Log** events covering the
   deployment interval, including operation, UTC time, status, correlation ID,
   and initiating principal.
2. **Diagnose and solve problems**, platform/restart events, App Service
   health/resource metrics, and relevant SCM/container logs.
3. Kudu/SCM deployment history and detailed OneDeploy logs for
   `bf08d173-7e5d-455c-8898-c34fa8e4de9e`.
4. Available Oryx/deployment output and a read-only view of the effective
   runtime and relevant build settings, including
   `SCM_DO_BUILD_DURING_DEPLOYMENT`.

The operators should correlate all records using UTC timestamps and
deployment/correlation IDs. They should redact secrets, access tokens,
connection strings, and sensitive environment values before sharing evidence.

## 5. Safe next step

Collect the GitHub run timeline/log and the corresponding Azure Activity,
Kudu/OneDeploy, platform, and resource evidence first. Compare the records
around the exact deployment interval and determine whether any operation
overlapped. If access remains unavailable, keep the cause unknown and escalate
the evidence request to the repository and Azure administrators. Only after
the failed deployment's state and trigger are understood should an owner
separately decide whether any remediation or release action is warranted.

No production retry, restart, deployment, or configuration change is
recommended or performed by this phase.

## 6. Local repository baseline and validation

At Phase 49 start:

| Item | Result |
|---|---|
| Repository root | `D:/FTP/NexHaat` |
| Branch / HEAD | `main` / `e4c25550fbc489d85b7b412ff855d864e9d9c645` |
| Upstream | `origin/main` |
| Worktree | Pre-existing modified `docs/plans/nexhaat-master-plan.md`; untracked Phase 44–48 documents; all preserved |

The local Phase 48 report records that local `runtime.txt` and the local
deployment workflow both specify Python 3.14. This does not verify the remote
run's source tree or live App Service runtime because the reported remote
commit object and Azure runtime settings were unavailable.

| Check | Result |
|---|---|
| `python scripts\validate_repository_structure.py --fail-on-review` | **PASS** — exact final result recorded after Phase 49 documentation edits |
| `git diff --check` | **PASS** — exact final result recorded after Phase 49 documentation edits |
| Final branch and HEAD | **PASS** — remain `main` / `e4c25550fbc489d85b7b412ff855d864e9d9c645` |
| Production changes | **NONE** |

## 7. Files changed

- `docs/architecture/PHASE49_AZURE_DEPLOYMENT_EVIDENCE_REPORT.md` — this
  read-only evidence report.
- `docs/plans/nexhaat-master-plan.md` — dated Phase 49 evidence entry.

Phase 44–48 files and all pre-existing worktree changes remain intact. No
workflow, application code, Azure setting, secret, environment variable, or
database was changed. No restart, redeployment, fetch, sync, commit, push,
merge, or deployment occurred.
