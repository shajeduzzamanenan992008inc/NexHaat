# Phase 48 — Azure SCM Restart Diagnostic Report

**Date:** 2026-11-02  
**Repository:** `D:/FTP/NexHaat`  
**Failed Actions run:** `41369767391`  
**Reported source commit:** `97bc4bc6368eda6c29d98331aee5bfebfa60c301`  
**Overall status:** **PARTIAL / BLOCKED** — the user-provided deployment
error and local workflow/runtime configuration were assessed, but authenticated
run logs and Azure platform diagnostics were unavailable. No configuration or
production resource was changed.

## 1. Baseline and preservation

| Item | Observed |
|---|---|
| Repository root | `D:/FTP/NexHaat` |
| Branch / local `HEAD` | `main` / `e4c25550fbc489d85b7b412ff855d864e9d9c645` |
| Upstream | `origin/main` |
| Initial worktree | `## main...origin/main`; modified roadmap and untracked Phase 44–47 documents, all pre-existing and preserved |
| Live `origin/main` | `97bc4bc6368eda6c29d98331aee5bfebfa60c301` from the last read-only `git ls-remote` observation |
| Failed run source commit | `97bc4bc6368eda6c29d98331aee5bfebfa60c301`, supplied in the task; its commit object is not in this local Git object database |

Phase 44–47 reports and the Phase 44 administrator checklist were read and
left unchanged. Phase 47 established that local/cached `main` is at `e4c2555`,
the live remote SHA is `97bc4b`, and remote Git objects were not retrieved.
No fetch or synchronization was performed in Phase 48.

## 2. Run evidence and limitations

The user reports that run `41369767391` had successful build and artifact
download steps, successful Azure OIDC login, then failed after OneDeploy
started with:

> Deployment has been stopped due to SCM container restart.

This is retained as **user-provided evidence**, not a log independently
retrieved in this phase. `gh auth status` reported GitHub CLI authentication
unavailable; `gh run view 41369767391` could not access the run. No other
authenticated Actions run-log tool was available in the configured
environment.

| Run detail | Status |
|---|---|
| Run ID and reported source SHA | **PARTIAL** — supplied by user; live remote `main` currently reports the same SHA |
| Build result / artifact download | **PARTIAL** — success reported by user; not verified from job logs |
| Azure login result | **PARTIAL** — success reported by user; not verified from job logs |
| Deployment result / error | **PARTIAL** — exact error text reported by user; raw step log unavailable |
| Deployment start/end timestamps | **BLOCKED** — no run metadata or step log access |
| Subsequent/overlapping GitHub deployment run | **UNKNOWN** — no Actions run list access |
| Overlapping Azure management operation | **UNKNOWN** — no Activity Log access |

The report's source-level workflow analysis below is against local `HEAD`
`e4c2555`. It is not proof of the exact workflow file used by remote commit
`97bc4b`, whose commit object was not downloaded.

## 3. Azure access and platform diagnostics

Azure CLI is **not installed** (`Get-Command az` returned unavailable). No
authorized Azure portal/API diagnostic session was available. Therefore no
App Service Activity Log, platform event, Kudu/SCM deployment record,
OneDeploy log, restart event, container log, storage metric, memory metric,
Oryx output, or runtime setting was inspected.

In particular, Phase 48 cannot confirm or exclude:

- a concurrent deployment or App Service management operation;
- platform-initiated recycle, host/worker maintenance, or SCM container
  restart;
- SCM worker memory, disk, or temporary-storage pressure;
- Oryx build activity or interruption;
- deployment timeout;
- current `SCM_DO_BUILD_DURING_DEPLOYMENT` value or other App Service settings.

No Azure state was changed, and production was not stopped, restarted, or
redeployed.

## 4. Local workflow and package review

Local `.github/workflows/main_nexhaat.yml` shows:

- Deployment uses `workflow_run` after successful CI on a push to `main`, or a
  manual dispatch path requiring the exact confirmation string.
- The build job checks out the tested commit, installs Python 3.14 and Node 22,
  runs validation/tests and `npm run build`, then uploads an artifact.
- The deploy job downloads that artifact, logs into Azure using OIDC, then
  invokes the pinned `azure/webapps-deploy` v3.0.7 action against Web App
  `NexHaat`, slot `Production`.
- No explicit Azure restart, stop, or start command appears in the local
  workflow. The deploy action initiates deployment; the local source does not
  reveal why the SCM container restarted.

Runtime/build observations:

| Check | Local evidence |
|---|---|
| Python runtime declaration | `runtime.txt` contains `python-3.14` |
| Workflow build Python | `actions/setup-python` requests `3.14` — **matches** `runtime.txt` |
| Oryx/App Service build setting | No `SCM_DO_BUILD_DURING_DEPLOYMENT` or `ENABLE_ORYX_BUILD` declaration found in searched repository sources; live setting is **UNKNOWN** |
| Explicit platform startup/deployment files | Root `.deployment`, `web.config`, `startup.sh`, `.azure`, and `azure.yaml` were not present |
| Workflow package scope | Artifact upload uses the workspace root (`.`), with explicit exclusions for Git/GitHub metadata, dependency/virtualenv/cache paths, env files, PEM, and key files |
| Build outputs / artifact listing | Build runs `npm run build` (TypeScript plus Vite); root artifact upload has no explicit `dist/` exclusion. The artifact manifest was not available, so actual contents and whether any generated files were unintended are **NOT TESTED** |
| `requirements.txt` | Runtime package declarations only; contains no deployment operation or Oryx control |
| Local Oryx manifest | `.gitignore` mentions `oryx-manifest.toml`; this is an ignore rule, not evidence of a manifest or live App Service setting |

The local deployment architecture document notes that Flask and the
React/Express surfaces are intended to be separate deployment artifacts and
that the actual Azure stack/startup command require inspection before
production changes. This makes the broad root artifact a **configuration
scope to review**, but there is no evidence tying its contents to this SCM
restart. Do not treat it as the cause without deployment logs and the
artifact's file manifest.

## 5. Root-cause classification

| Finding | Classification | Evidence and limits |
|---|---|---|
| OneDeploy was interrupted because the SCM container restarted | **CONFIRMED from user-provided error only** | Error says the deployment was stopped due to SCM container restart; the actual Actions log was not retrieved |
| The proximate failure is an SCM/Kudu deployment worker restart during OneDeploy | **LIKELY** | Direct interpretation of the supplied error text; does not identify who/what initiated the restart |
| A concurrent deployment or management action caused the restart | **POSSIBLE / UNKNOWN** | No Actions run list or Azure Activity Log available |
| Platform recycle/maintenance, resource/storage pressure, Oryx interruption, or timeout caused the restart | **POSSIBLE / UNKNOWN** | No platform events, resource metrics, Oryx, or deployment logs available |
| Application code caused the SCM restart | **NOT ESTABLISHED** | No app/runtime log evidence supports this conclusion; an SCM deployment-host restart is not itself proof of an app defect |
| Local Python runtime mismatch | **NOT INDICATED** | Local `runtime.txt` and workflow both specify Python 3.14; remote run source and live stack remain unverified |
| Artifact content caused the restart | **NOT ESTABLISHED** | Broad package scope noted, but actual uploaded artifact and OneDeploy logs were not accessible |

The **most likely immediate mechanism** is a restart of the App Service SCM
container while OneDeploy was active. The underlying trigger and root cause
remain **UNKNOWN**. No evidence supports attributing it to a concurrent
operation, resource limit, Oryx, timeout, or application code.

## 6. Safe diagnostic and remediation plan

An authorized Azure administrator should collect evidence before retrying:

1. From GitHub Actions run `41369767391`, record the workflow/run URL, source
   SHA, UTC job and step start/end timestamps, deployment action log, and
   artifact name/manifest. Confirm build, download, login, and OneDeploy
   conclusions separately. Do not include credentials or secret-bearing
   environment output in the report.
2. In Azure Portal, inspect **Activity log** for the App Service and App
   Service Plan across the deployment interval (with a narrow lead/lag window).
   Identify restart, configuration, scale, slot, or deployment operations and
   their initiating principal. Do not infer overlap if no event supports it.
3. Use **Diagnose and solve problems** for deployment failures and inspect
   Kudu/SCM deployment history and the OneDeploy deployment's detailed log.
   Correlate deployment ID, source package, and timestamps with the GitHub
   step.
4. Inspect App Service platform events, Linux/container/SCM logs as applicable,
   Log Stream, and available memory, disk, and temporary-storage metrics.
   Review Oryx/build logs and the current runtime/stack and
   `SCM_DO_BUILD_DURING_DEPLOYMENT` setting read-only. Redact secrets.
5. Compare the uploaded artifact manifest against the intended Flask App
   Service package; specifically identify generated frontend output, test
   files, and other build artifacts. Do not change packaging based only on
   the SCM restart message.
6. Only after the App Service health/current deployment state is checked and
   the restart trigger understood should the owner authorize a retry or
   targeted remediation. If platform events indicate an Azure-side recycle or
   repeated SCM failure, escalate with deployment IDs/timestamps to the Azure
   platform owner/support. If logs identify packaging or Oryx behavior, propose
   the narrowest environment-specific fix separately for approval.

No retry, restart, workflow change, or configuration edit is part of Phase 48.

## 7. Files changed and validation

Phase 48 changes:

- `docs/architecture/PHASE48_AZURE_SCM_RESTART_DIAGNOSTIC_REPORT.md` — this
  diagnostic report and evidence-based remediation plan.
- `docs/plans/nexhaat-master-plan.md` — dated Phase 48 entry.

Pre-existing Phase 44–47 reports, checklist, and roadmap edits remain intact.

| Check | Result |
|---|---|
| Repository root, branch, HEAD, upstream, and initial worktree status | **PASS** — recorded above |
| GitHub CLI authentication / `gh run view 41369767391` | **BLOCKED** — no authenticated host |
| Azure CLI availability | **BLOCKED** — Azure CLI is not installed; no portal diagnostic access |
| Run timestamps, actual logs, overlap, Azure Activity/Kudu/Oryx/resource evidence | **NOT TESTED / BLOCKED** — access/evidence unavailable |
| Local `runtime.txt` vs workflow Python version | **PASS** — both specify Python 3.14 |
| `python scripts\validate_repository_structure.py --fail-on-review` | **PASS** — result recorded after report and roadmap edits |
| `git diff --check` | **PASS** — no whitespace errors |

No application or workflow test was run because no source behavior or workflow
was changed. Branch and `HEAD` must remain unchanged at final verification.
