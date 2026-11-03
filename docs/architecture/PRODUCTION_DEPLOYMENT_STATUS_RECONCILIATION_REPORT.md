# Production Deployment Status Reconciliation Report

**Date:** 2026-11-03
**Scope:** GitHub Actions Azure deployment results vs. GitHub `production` Environment
deployment history for the `NexHaat` Azure Web App.
**Baseline commit:** `9b4e28c0aad9ffd6cdfb2903473ed9c06629a633` (worktree clean,
`main` == `origin/main`).
**Production deployment performed:** NO
**Commit / push performed:** NO
**GitHub or Azure settings changed:** NO

---

## 1. Original symptoms

1. GitHub repository **Deployments** history showed three entries in state **Failed**:
   "Latest changes (#40)", "New update (#39)", "Updated files".
2. GitHub Actions runs **#47, #48, #49** of the Azure deployment workflow were reported
   **successful**; run #49 built, logged in to Azure, and deployed the Web App successfully
   at commit `9b4e28c`.
3. The two signals appeared contradictory. They are in fact independent: an Actions run
   conclusion is not a GitHub Environment deployment record, and neither is an Azure
   deployment operation result.

## 2. Evidence collected

All evidence below comes from the local repository (`git`), the workflow source, and the
release runbook. GitHub-hosted run logs, deployment records, Environment settings, and
Azure deployment history were **not accessible** in this environment (no authenticated
`gh`/API access) and are marked **BLOCKED** where relevant.

| # | Finding | Evidence | Confidence | Required action |
|---|---|---|---|---|
| E1 | The current deploy job declared **no** `environment:` key, so it cannot create GitHub Environment deployment records. | `.github/workflows/main_nexhaat.yml` at `9b4e28c`: `deploy` job contained `runs-on`, `needs`, `permissions`, `steps` only. | Confirmed | Fix: declare `environment: production` (done). |
| E2 | A hardened workflow **did** declare `environment: name: production`, and each of the three failed-deployment commits contains that declaration. | `git show <sha>:.github/workflows/main_nexhaat.yml` for `e4c2555` (line 150), `e1b8449` (line 148), `5000ff6` (line 148) → `name: production`. | Confirmed | Fix restores the same environment name for consistency. |
| E3 | The three failed deployment titles map exactly to three commits on `main`. | `git show -s --format=%s`: `e4c25550...` = "Latest changes" (2026-11-02 00:52), `e1b8449c...` = "New update" (2026-11-01 22:48), `5000ff6c...` = "Updated files" (2026-11-01 22:32). | Confirmed | Treat them as historical, commit-specific records — not as evidence about running #49. |
| E4 | On 2026-11-02 the workflow was replaced by an Azure-portal-generated template, removing the Environment declaration and the release gate. | `git show --stat 97bc4bc` ("Add or update the Azure App Service build and deployment workflow config", 2026-11-02 06:55): `.github/workflows/main_nexhaat.yml` 74 insertions / 170 deletions. `git show e4c2555:.github/workflows/main_nexhaat.yml` is 244 lines with `workflow_run` CI gating, exact-SHA checkout, verification steps, `concurrency`, and `environment: name: production`. | Confirmed | Fix restores the environment declaration only; broader gate restoration needs owner decision. |
| E5 | The workflow that produced the current successful runs is the portal template, which triggers on **every push to `main`** and on `workflow_dispatch`. | `on:` block in current workflow: `push.branches: [main]`, `workflow_dispatch`. | Confirmed | Documented in runbook correction. |
| E6 | The portal regeneration also switched the Azure OIDC secret set. | Hardened workflow used `AZUREAPPSERVICE_CLIENTID_3835337063124149AAF2ED293D18D27C` / `TENANTID_E4CED2CF...` / `SUBSCRIPTIONID_1142190C...`; current workflow uses `...CLIENTID_F7E1BD86...` / `TENANTID_61F72245...` / `SUBSCRIPTIONID_1D69F25E...`. | Confirmed (names differ); whether the older identity was misconfigured is **BLOCKED** | No change made to credentials. Compare federated credential subjects before altering. |
| E7 | No workflow, script, or source file in the repository creates GitHub deployments or posts deployment statuses through the Deployments API. | Repository-wide search for `api.github.com/.../deployments`, `deployment_status`, `createDeployment` → 0 matches. Only `.github/workflows/main_nexhaat.yml` deploys to Azure; no other workflow declares `environment:`. | Confirmed | No custom status integration to repair or remove. |
| E8 | The release runbook described a workflow that no longer exists (CI `workflow_run` trigger, `DEPLOY-PRODUCTION` confirmation input). | `.github/runbooks/production-release.md` "Automatic path"/"Manual path" vs. current `on:` block (E5). | Confirmed | Documentation corrected. |
| E9 | The workflow's Azure target is unchanged and explicit: app `NexHaat`, slot `Production`, `azure/webapps-deploy@v3`. | Current `deploy` job steps. | Confirmed | Preserved; not modified. |
| E10 | The deployed artifact is the artifact built by the same run, from the ref that triggered the run; there is no cross-commit artifact reuse. | `build` uploads `python-app`; `deploy` downloads `python-app` with `needs: build`. | Confirmed | Already commit-consistent for push events. |
| E11 | Why the three historical deploy runs failed (build failure, Azure login failure, Environment approval rejection, or OIDC subject mismatch) cannot be determined locally. | No run logs, no `gh` authentication, no Azure access. | **BLOCKED** | Requires GitHub run log review and Azure federated credential inspection. |
| E12 | Whether the `production` Environment exists and what protection rules it has (required reviewers, wait timer, branch policy) is unknown. | Not inspectable from the repository. | **BLOCKED** | Requires GitHub Settings → Environments review. |

## 3. Root cause

**Two independent conditions explain the mismatch; neither is an Azure deployment failure.**

1. **The three "Failed" records are historical and commit-specific.** They belong to
   `5000ff6` ("Updated files"), `e1b8449` ("New update") and `e4c2555` ("Latest changes") —
   commits deployed by the older hardened workflow that declared
   `environment: name: production` (E2, E3). Those runs did fail, so GitHub recorded
   failed deployment states for exactly those commits.
2. **No newer deployment record could be created at all.** After the 2026-11-02 Azure
   portal regeneration (`97bc4bc`, E4), the workflow no longer declares an
   `environment:` (E1). GitHub only creates an Environment deployment record for a job
   that declares one. Runs #47–#49 therefore deployed to Azure successfully while
   creating **zero** `production` deployment records. The Environment history stayed
   frozen at the three older failures, producing the apparent contradiction.

In the Phase 2 taxonomy this is **F (historical deployments failed; newer runs succeeded)
combined with C (the workflow does not declare the intended Production Environment)**.
It is *not* A (a status that should have been updated but failed to be), not B (wrong
commit/deployment ID), not D (no post-deploy status step exists), not E (only one
deployment workflow exists), and not G (no evidence of protection-rule interference —
that possibility is BLOCKED, not established).

The individual failure reason of the three historical runs remains **UNKNOWN** (E11).

## 4. Files changed and why

| File | Change | Reason |
|---|---|---|
| `.github/workflows/main_nexhaat.yml` | Added `environment: name: production` with `url: ${{ steps.deploy-to-webapp.outputs.webapp-url }}` to the `deploy` job, plus an explanatory comment. | Without an environment declaration GitHub cannot create a commit-specific `production` deployment record, so the record state can never track the real Azure deployment result (root cause 2). The environment name matches the previously working declaration and the runbook. |
| `.github/runbooks/production-release.md` | Corrected "Automatic path" and "Manual path"; added a "Deployment status signals" section. | The documented trigger model (`workflow_run` + `DEPLOY-PRODUCTION`) was demonstrably false (E8). Release and rollback guidance was preserved. |
| `docs/architecture/PRODUCTION_DEPLOYMENT_STATUS_RECONCILIATION_REPORT.md` | New report (this file). | Required documentation of symptoms, evidence, root cause, validation and remaining external work. |

Nothing else was modified: no application logic, no API contracts, no migrations, no
secrets, no Azure configuration, no other workflow.

## 5. Workflow lifecycle before and after

**Before (at `9b4e28c`, portal-generated):**

```
push main ──► build (venv, pip install -r requirements.txt, upload artifact "python-app")
           └► deploy (download artifact, azure/login, azure/webapps-deploy)
                └─ no environment declaration → no GitHub deployment record
```

**After (this change):**

```
push main ──► build (unchanged)
           └► deploy  [environment: production]
                ├─ GitHub creates a deployment record for the triggering commit SHA
                ├─ azure/login (OIDC, unchanged secret names)
                ├─ azure/webapps-deploy (app NexHaat, slot Production, unchanged)
                └─ record state = job outcome: success only after the Azure deploy step
                   succeeds; failure when any step fails. No manual status writes.
```

Guarantees established by the change:

- **Success cannot precede Azure deployment**: the job only concludes successfully after
  `azure/webapps-deploy` returns success; GitHub derives the deployment state from the job.
- **Commit-specific**: the deployment record's SHA is the run's triggering commit, i.e. the
  commit that `build` packaged.
- **No duplicate records**: only one job declares `production`; no other workflow deploys.
- **No fake statuses**: no Deployments API calls are added.

Historical hardened lifecycle (for reference, not restored): `CI` success on `main`
→ `workflow_run` → exact `head_sha` checkout → verification → package → `deploy`
(`environment: production`) → OIDC deploy.

## 6. Validation results

| Check | Result | Notes |
|---|---|---|
| `git diff --check` | PASS | No whitespace errors. |
| Workflow structural inspection (Python/`grep` static checks) | PASS | `environment` is a **job-level** key of `deploy`; `name: production`; `app-name: NexHaat`; `slot-name: Production`; deploy depends on `build`; single deploy job. |
| YAML parse with a real parser | **NOT TESTED** | No YAML parser is available locally (`pyyaml`, `js-yaml`, `yaml`, Ruby `YAML` all absent). Installing one was deliberately avoided. |
| `actionlint` | **NOT TESTED** | Not installed locally. |
| `python scripts/validate_repository_structure.py --fail-on-review` | PASS | `repository_structure=PASS`, 0 source deletions/renames, 190 registry paths checked, 3 worktree entries for review (the 3 intended files). |
| Existing Python tests | **NOT RUN** | The change touches no Python code or test-covered behavior. |
| Live GitHub Actions run / Environment record | **NOT TESTED** | Requires a separately authorized real deployment. |
| Azure federated credential subject | **NOT VERIFIED** | Requires Azure portal access. |

## 7. Remaining external GitHub/Azure configuration requirements

These cannot be verified or changed from the repository and must be confirmed by an
administrator **before** relying on the next deployment:

1. **Azure federated credential subject.** Declaring `environment: production` changes the
   OIDC subject from `repo:<owner>/<repo>:ref:refs/heads/main` to
   `repo:<owner>/<repo>:environment:production`. If the federated credential for the
   currently used client ID (`...F7E1BD86...`) trusts only the branch subject,
   `azure/login` will fail on the next run. Confirm the credential matches the
   environment subject, or add it, before deploying.
2. **`production` Environment settings.** Confirm the Environment exists, and decide on
   required reviewers / wait timer / branch policy. If required reviewers are configured,
   the `deploy` job will wait for manual approval instead of running automatically — this
   is the documented intent, but it changes deploy timing.
3. **Historical failures.** Review the three failed runs' logs to determine the actual
   failure mode; do not retroactively reinterpret them as Azure deployment failures.
4. **Release gate restoration (decision required).** The pre-2026-11-02 workflow enforced
   CI-success gating, exact-SHA checkout, verification steps, and a typed manual
   confirmation. Restoring it would need owner approval and would be reverted if the
   Azure portal Deployment Center regenerates the workflow again.

## 8. Production deployment performed

**NO.** No workflow was triggered, no Azure operation was run, no restart occurred.

## 9. Commit / push performed

**NO.** All changes are uncommitted local working-tree edits.

## 10. Remaining risks and recommended next steps

| Risk | Impact | Mitigation |
|---|---|---|
| Environment declaration reintroduces an OIDC subject mismatch | Next deployment fails at `azure/login` | Verify the federated credential (item 7.1) before the next push to `main`. |
| Required reviewers configured on `production` | Deployments pause awaiting approval | Expected per runbook; ensure an approver is available. |
| Azure portal Deployment Center may regenerate the workflow again | Environment declaration silently removed, records stop being created | After any portal-driven workflow change, re-check that `deploy` still declares `environment: production`. Consider reconciling runbook and workflow policy. |
| The portal template deploys on every push to `main` with no verification or CI gate | Unreviewed/unverified code reaches production | Restore the hardened gate (separate, owner-approved change). |
| `workflow_dispatch` is not restricted to `main` | A manual dispatch from another branch would deploy that branch | Restrict the job with a `github.ref == 'refs/heads/main'` guard (separate change) or document as an operator rule (documented for now). |
| Historical failure cause unknown | Cannot assert the new configuration fixes those failures | Review run logs (item 7.3). |

**Verification standard (not met by this change alone):** the fix can be called *verified*
only after a separately authorized deployment produces a successful `production`
deployment record for the exact deployed commit, independently confirmed on the GitHub
Deployments page, together with a healthy application check.

## 11. Non-goals honored

- No application business logic, API, schema, migration, or integration changed.
- No Azure secret, credential, OIDC, app setting, slot, or production configuration changed.
- No deployment, restart, migration, commit, push, merge, tag, or release performed.
- No GitHub deployment history altered; no custom status integration added.
- No other workflow removed or replaced; `ci.yml`, `codeql.yml`,
  `config-validation.yml`, `dependency-review.yml`, and `sbom-provenance.yml` untouched.
