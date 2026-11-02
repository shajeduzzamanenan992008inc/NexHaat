# Phase 50 — Azure Administrator Diagnostic Handoff

**Purpose:** Read-only evidence collection for the failed Azure App Service
deployment. This checklist does not authorize restart, configuration change,
slot swap, redeployment, or production recovery.

## Incident identifiers

| Field | Value / status |
|---|---|
| GitHub repository | `shajeduzzamanenan992008inc/NexHaat` |
| GitHub Actions run | `41369767391` (user-provided; run logs not independently accessed) |
| Reported run workflow | `Build and deploy Python app to Azure Web App - NexHaat` |
| Reported source commit | `97bc4bc6368eda6c29d98331aee5bfebfa60c301` |
| Azure resource | App Service `NexHaat` |
| Slot | `Production` |
| OneDeploy ID | `bf08d173-7e5d-455c-8898-c34fa8e4de9e` |
| Reported failure | `Deployment has been stopped due to SCM container restart.` |
| Root cause | **UNKNOWN** — Phase 48–49 did not have authenticated GitHub or Azure diagnostics |

Identifiers and error above are from the request and previous reports. They
are not a substitute for portal/API records.

## Evidence handling and scope

- Use authorized, read-only access. Do not restart, stop, swap, redeploy, edit
  app settings, change identity/networking, or alter the database.
- Record timestamps in UTC, source, resource/slot, operation, status, actor,
  correlation ID, and evidence reference.
- Share only the minimum relevant log excerpts. Redact access tokens, secret
  values, connection strings, private keys, customer data, and unrestricted
  environment dumps.
- If an evidence source has expired or is unavailable, record that explicitly;
  do not infer an event from its absence.

## A. Azure Activity Log

After obtaining the exact UTC start/end from GitHub Actions, query a narrow
window covering the deployment interval and a documented lead/lag. Include the
App Service and its App Service Plan where relevant.

- [ ] Record the query's UTC start/end and resource scope.
- [ ] Inspect management operations for configuration updates, restart,
  stop/start, scale, slot, deployment, and other App Service operations.
- [ ] For each relevant event record operation name, event/submission time,
  status, actor/principal, correlation ID, and resource ID.
- [ ] Distinguish an operation initiated by an administrator/automation from
  an Azure platform event.
- [ ] Do not claim overlap unless event times actually overlap the deployment.

## B. App Service platform diagnostics

- [ ] Inspect Diagnose and solve problems for deployment/restart issues in the
  same UTC window.
- [ ] Review App Service platform, worker, container, and SCM/Kudu restart
  events as applicable.
- [ ] Review Resource Health and platform maintenance/service-health events.
- [ ] Capture available memory, CPU, disk, temporary storage, worker health,
  and quota evidence around the event.
- [ ] Record unavailable/expired diagnostics as missing evidence, not as proof
  that no restart or resource event occurred.

## C. Kudu / SCM / OneDeploy

- [ ] Find OneDeploy record
  `bf08d173-7e5d-455c-8898-c34fa8e4de9e` and record its status and timestamps.
- [ ] Capture deployment start/end, SCM restart time, detailed error, and
  deployment/correlation IDs.
- [ ] Review Kudu/SCM deployment history for other deployments in the window.
- [ ] Identify whether a different deployment or management operation actually
  overlapped; record its identity and timestamps if present.
- [ ] Preserve the artifact/deployment manifest reference without exposing
  secrets or private payload contents.

## D. GitHub Actions run

- [ ] For run `41369767391`, verify workflow name, source SHA, run URL, and
  trigger.
- [ ] Record build, artifact upload/download, Azure login, and deployment job
  conclusions and UTC start/end times separately.
- [ ] Record artifact name, digest/checksum if available, and file manifest.
- [ ] Capture the exact OneDeploy step error and deployment ID from the log.
- [ ] Inspect nearby runs of the same deployment workflow for overlapping
  activity. Do not infer Azure-side operations solely from GitHub run overlap.
- [ ] Exclude secret values and sensitive environment output from shared
  evidence.

## E. Runtime, Oryx, and package

- [ ] Compare the run's source tree and artifact manifest with the intended
  Flask App Service package.
- [ ] Local Phase 48 inspection found `runtime.txt` and workflow build Python
  both set to Python 3.14; verify the exact remote run SHA and effective Azure
  stack independently.
- [ ] Read the effective runtime/startup configuration and relevant deployment
  settings, including `SCM_DO_BUILD_DURING_DEPLOYMENT`, only through authorized
  read-only access.
- [ ] Review Oryx build/deployment logs, if Oryx ran, and distinguish its
  status from OneDeploy/SCM host status.
- [ ] Inspect the uploaded artifact root structure, including frontend build
  output and test/build files; do not assume files were present merely because
  the local workflow uploads `.`.
- [ ] Record configuration or package differences as evidence; do not change
  settings or rerun a deployment during this investigation.

## Evidence record

| Timestamp UTC | Source | Event | Correlation/Deployment ID | Result | Evidence reference |
|---|---|---|---|---|---|
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |

**Confirmed root cause:**  

**Supporting evidence:**  

**Contradictory evidence:**  

**Missing evidence:**  

**Confidence level (with rationale):**  

## Escalation / handoff

If the records identify a platform event, resource constraint, overlapping
operation, Oryx failure, artifact issue, or another cause, provide the
correlated evidence and a proposed narrow remediation to the service owner.
Any remediation, retry, restart, or release requires separate explicit
authorization and review. If logs are unavailable or conflicting, mark the
cause **UNKNOWN** and continue read-only diagnostics.
