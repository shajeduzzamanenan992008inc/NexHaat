# Phase 44 — CI/CD, Security, and Deployment Remediation Report

**Date:** 2026-11-02  
**Repository:** `shajeduzzamanenan992008inc/NexHaat`  
**Overall status:** **PARTIAL / BLOCKED** — local workflows and configuration
were reviewed and no local defect requiring a safe correction was established.
Current GitHub run logs, PR state/checks, security-feature settings, Azure
federated credentials, and attestation variable state were inaccessible. The
administrator actions are documented separately.

## 1. Baseline and preservation

| Item | Evidence |
|---|---|
| Repository root | `D:/FTP/NexHaat` from `git rev-parse --show-toplevel` |
| Branch | `main` |
| Local `HEAD` | `e4c25550fbc489d85b7b412ff855d864e9d9c645` |
| Remote `origin/main` | `e4c25550fbc489d85b7b412ff855d864e9d9c645` from `git ls-remote origin refs/heads/main`; local `origin/main` agrees |
| Initial worktree | Clean: `git status --short --branch` reported `## main...origin/main`; no pre-existing modified, staged, or untracked files |
| Prior phase reports | Phase 40, 41, 42, and 43 reports are present and were not modified |
| Secrets / production | No secret values or `.env` contents were read; no production or Azure settings were accessed |

The remote branch SHA was verified independently with `git ls-remote`, but this
does not provide workflow-run or repository-settings access. No user changes
were present to preserve at task start. This report, the administrator
checklist, and the roadmap entry are the only intended changes.

## 2. Remote evidence and limitations

`gh auth status` was unavailable (`GH_AUTH_UNAVAILABLE`). The GitHub connector's
read-only `pull_request_read` requests for PR #31 (`get` and `get_check_runs`)
returned HTTP 404. Because the repository documentation identifies the
repository as private and the requests were unauthenticated, this does **not**
establish that PR #31 is closed or nonexistent. Its current state, head/base
references, latest check conclusions, and logs remain **BLOCKED / NOT
VERIFIED**.

No CI, CodeQL, SBOM, deployment, or Dependency Review run logs were retrieved.
The reported failures are treated as user-provided evidence, with prior
CodeQL/SBOM history explicitly attributed to Phases 37–40 and 39–42. No remote
run or administrator setting is claimed as verified in Phase 44.

## 3. Findings by reported blocker

### Azure OIDC — **PARTIAL; remote identity verification BLOCKED**

The deployment workflow at
`.github/workflows/main_nexhaat.yml` uses the `production` GitHub environment,
grants `id-token: write` only to the deploy job, and invokes the pinned
`azure/login` action using existing secret references for its client, tenant,
and subscription identifiers. No audience override is set. The exact pinned
`azure/login` action metadata declares its default audience as
`api://AzureADTokenExchange`.

The expected token claims for this workflow are:

- Issuer: `https://token.actions.githubusercontent.com`
- Subject: `repo:shajeduzzamanenan992008inc/NexHaat:environment:production`
- Audience: `api://AzureADTokenExchange`

These are derived from the workflow's GitHub environment and the pinned
action's default. The user-reported `AADSTS700213` indicates that Azure did not
find a federated identity record matching the presented identity. The local
workflow configuration contains no demonstrated issuer/subject/audience
defect. The exact Azure-side mismatch (including whether the credential is
missing, attached to another identity, or has different claims) cannot be
determined without the Azure-side credential and run log. No workflow change,
credential change, or deployment was made.

### CodeQL — **BLOCKED for current remote verification**

`.github/workflows/codeql.yml` still analyzes `javascript-typescript`, `python`,
and `actions`, initializes `security-extended`, and uploads through
`github/codeql-action/analyze`. The workflow covers pushes and pull requests
to `main`, scheduled analysis, and manual dispatch. `security-events: write`
is scoped to the analysis job; repository and Actions permissions are
read-only otherwise. No repository-owned defect was identified from source
inspection.

Earlier Phase 37/40 reports record the message
`Code scanning is not enabled for this repository.` The current setting and
latest CodeQL logs could not be inspected, so the current cause is not
independently reconfirmed. If that prior error remains current, it is a
repository/organization feature-availability or configuration blocker, not a
reason to remove a language or analysis job. No setting or workflow change was
made.

### Dependabot PR #31 / Dependency Review — **BLOCKED**

The local deployment workflow references `azure/webapps-deploy` v3.0.7; the
same reference is the only occurrence found in the repository. The reported
PR update to v3.0.8 and its failing check could not be inspected because
authenticated PR access was unavailable.

The official Azure action v3.0.8 release page identifies the release as a
deprecation-warning fix and links a GitHub-verified signed release commit.
The upstream v3.0.7-to-v3.0.8 diff also changes the action runtime from
Node.js 20 to Node.js 24 and changes bundled action/dependency code. This
repository invokes it on GitHub-hosted `ubuntu-latest`, not a pinned
self-hosted runner, so no local runner-version conflict is evident from the
workflow. Runtime compatibility was not exercised on GitHub, and this
assessment does not replace review of PR #31's exact diff/check log. The local
`.github/workflows/dependency-review.yml` retains its
pull-request trigger, read-only `contents` permission, and
`actions/dependency-review-action@v5.0.0` vulnerability check at Moderate
severity or higher. No local workflow defect or actual vulnerability finding
was established. The user-reported “Dependency review is not supported on
this repository” could reflect feature/plan availability; current cause and
PR state remain unknown. No PR was approved or merged, and no workflow or
action pin was changed.

### SBOM and provenance attestation — **PARTIAL; skip reason BLOCKED**

Source inspection of `.github/workflows/sbom-provenance.yml` confirms:

- A successful CI `workflow_run` uses the triggering run's `head_sha`; manual
  and scheduled runs use the selected main-branch SHA.
- The source archive is written under `RUNNER_TEMP`, outside the `.` tree
  being archived, and the generated `sbom.spdx.json` is excluded.
- The archive and SBOM are checksummed in the working directory, and the
  generated `SHA256SUMS.txt` is checked with `sha256sum --check`.
- Upload and attestation producer/consumer artifact names derive from the same
  resolved SHA. The artifact includes the SBOM, source snapshot, and checksum
  manifest.
- Attestation requires successful SBOM generation and
  `vars.NEXHAAT_ENABLE_ARTIFACT_ATTESTATIONS == 'true'`; the consumer uses the
  uploaded archive and SBOM as its subject and SBOM input.

The optional gate is documented in `.github/NEXHAAT-GITHUB-SETUP.md`: signing
is opt-in and depends on repository visibility/plan entitlement and
organization approval. The source condition is intentional. Without the run
log and variable configuration, the exact reason for the reported skipped job
cannot be proven; an unset/false/non-exact variable is a plausible cause if
the prerequisite job succeeded. No signing success or provenance verification
is claimed, and no workflow change was made.

## 4. Cross-workflow consistency and scope

- CI remains separate and unchanged as the quality gate.
- Deployment remains gated on a successful CI push to `main`, checks out the
  tested commit, and uses the protected `production` environment and OIDC.
- CodeQL and Dependency Review security jobs remain intact.
- SBOM generation, checksum verification, artifact upload, and conditional
  attestation remain intact.
- The only `azure/webapps-deploy` occurrence locally remains v3.0.7.
- No application, API, database, Android, Express/AI, or product files were
  changed.
- No remote settings, secrets, PRs, branch protections, or production
  resources were changed. No commit, push, merge, or deployment occurred.

## 5. Checks and commands

| Check / command | Result |
|---|---|
| `git rev-parse --show-toplevel` | **PASS** — `D:/FTP/NexHaat` |
| `git branch --show-current` | **PASS** — `main` |
| `git rev-parse HEAD` | **PASS** — `e4c25550fbc489d85b7b412ff855d864e9d9c645` |
| `git status --short --branch` before edits | **PASS** — clean worktree, tracking `origin/main` |
| `git rev-parse origin/main` | **PASS** — same SHA as `HEAD` |
| `git ls-remote origin refs/heads/main` | **PASS** — remote main returned the same SHA |
| `rg` search for Azure deployment action references | **PASS** — only the existing v3.0.7 reference found |
| `gh auth status` | **BLOCKED** — no authenticated GitHub host |
| GitHub connector PR #31 `get` / `get_check_runs` | **BLOCKED** — both returned 404; private-repository access/state cannot be inferred |
| Latest CI, CodeQL, deployment, SBOM, and Dependency Review run logs | **NOT TESTED / BLOCKED** — authenticated Actions access unavailable |
| Azure federated credential and GitHub security/attestation settings | **NOT TESTED / BLOCKED** — no settings access |
| YAML parser / actionlint | **NOT AVAILABLE** — actionlint, Ruby, yq, yamllint, PyYAML, and Node YAML parsers were not found |
| Shell syntax for workflow `run` blocks | **NOT RUN** — no workflow shell was changed; prior phase verification is not a Phase 44 run |
| Application unit tests / builds | **NOT RUN** — this phase changes documentation only; workflows and application code are unchanged |
| `python scripts\validate_repository_structure.py --fail-on-review` | **PASS** — 6/6 required docs, 190 registry paths, no missing imports/config or source deletions/renames; three documentation worktree entries were expected |
| `git diff --check` | **PASS** — no whitespace errors |

## 6. Status summary and remaining risks

| Issue | Phase 44 status | Remaining verification |
|---|---|---|
| Azure OIDC | **PARTIAL** | Azure administrator must compare the exact claims and selected identity; an authorized deployment run is required afterward |
| CodeQL upload | **BLOCKED** | Repository administrator must verify Code Scanning eligibility/enablement and rerun all three language analyses |
| PR #31 / Dependency Review | **BLOCKED** | Authenticated access required to establish PR state, inspect the exact v3.0.8 update and check logs, and verify feature availability/findings |
| SBOM attestation skip | **PARTIAL** | Authenticated run/variable/plan inspection required to prove the skip reason and whether signing is eligible |

The administrator steps are in
[`PHASE44_ADMIN_ACTION_CHECKLIST.md`](PHASE44_ADMIN_ACTION_CHECKLIST.md).
No production release readiness is asserted. The principal release risks are
the unverified Azure trust configuration and the unavailable remote status of
security checks and provenance signing.

## 7. Files changed

- `docs/architecture/PHASE44_ADMIN_ACTION_CHECKLIST.md` — sanitized,
  evidence-based administrator actions.
- `docs/architecture/PHASE44_CICD_SECURITY_AND_DEPLOYMENT_REMEDIATION_REPORT.md`
  — this report.
- `docs/plans/nexhaat-master-plan.md` — dated Phase 44 evidence entry.

No workflow or application code was changed.

## References

- Local workflow: [Azure production deployment](../../.github/workflows/main_nexhaat.yml)
- Local workflow: [CodeQL](../../.github/workflows/codeql.yml)
- Local workflow: [Dependency Review](../../.github/workflows/dependency-review.yml)
- Local workflow: [SBOM and provenance](../../.github/workflows/sbom-provenance.yml)
- Local guidance: [GitHub setup](../../.github/NEXHAAT-GITHUB-SETUP.md)
- Upstream: [Azure Login action metadata at the pinned commit](https://raw.githubusercontent.com/Azure/login/a641126d1b8aa4d1fa005f4f92df94a3a4c4c906/action.yml)
- Upstream: [Azure/webapps-deploy v3.0.8 release](https://github.com/Azure/webapps-deploy/releases/tag/v3.0.8)
- Upstream: [Azure/webapps-deploy v3.0.7-to-v3.0.8 diff](https://github.com/Azure/webapps-deploy/compare/v3.0.7...v3.0.8)
- Microsoft: [Authenticate to Azure from GitHub Actions with OIDC](https://learn.microsoft.com/azure/developer/github/connect-from-azure-openid-connect)
