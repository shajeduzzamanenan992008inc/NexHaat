# Phase 45 — CI/CD Blocker Verification Report

**Date:** 2026-11-02  
**Repository:** `shajeduzzamanenan992008inc/NexHaat`  
**Overall status:** **BLOCKED / PARTIAL** — local workflow configuration was
reviewed; current remote run status, PR #31, Azure identity configuration, and
GitHub security/attestation settings could not be authenticated or verified.
No workflow defect was established from local source.

## 1. Starting baseline and preservation

| Item | Starting evidence |
|---|---|
| Repository path | `D:/FTP/NexHaat` |
| Branch / HEAD | `main` / `e4c25550fbc489d85b7b412ff855d864e9d9c645` |
| Upstream | `origin/main` |
| Initial status | `## main...origin/main`; modified `docs/plans/nexhaat-master-plan.md`; untracked Phase 44 administrator checklist and report |
| Existing Phase 44 work | Preserved; Phase 44 documentation and its roadmap entry were not replaced |
| Local cached `origin/main` | `e4c25550fbc489d85b7b412ff855d864e9d9c645` |
| Live Git remote `main` | `97bc4bc6368eda6c29d98331aee5bfebfa60c301`, from `git ls-remote origin refs/heads/main` |

The local branch's cached upstream reference is stale relative to the live
remote: `ls-remote` returned a different SHA, and the remote commit object was
not present in the local object database. No fetch was performed. Therefore
the current remote commit's contents, relationship to local `HEAD`, and
workflow files are **NOT VERIFIED**. Local inspection below applies to the
workspace at `e4c2555`, not necessarily the newer remote `main`.

## 2. Remote GitHub evidence

`gh auth status` returned **GH_AUTH=UNAVAILABLE**. Accordingly, no Actions run
list, run logs, or PR #31 state/checks were retrieved. Phase 44's GitHub
connector attempts for PR #31 returned 404; this does not prove that the PR
is closed or absent. No run IDs, timestamps, or current conclusions are
available to report.

| Remote item | Status | Evidence / limitation |
|---|---|---|
| Recent CI runs and failure logs | **BLOCKED** | GitHub CLI unauthenticated |
| CodeQL runs and upload logs | **BLOCKED** | GitHub CLI unauthenticated; prior Phase 44 cites earlier reports of Code Scanning unavailable, not a current run |
| SBOM/provenance run and logs | **BLOCKED** | GitHub CLI unauthenticated |
| Azure deployment run and OIDC log | **BLOCKED** | GitHub CLI unauthenticated; reported AADSTS700213 is not freshly confirmed |
| Dependabot PR #31 and Dependency Review check | **BLOCKED** | GitHub CLI unauthenticated; prior connector requests returned 404 |
| Current remote `main` contents | **BLOCKED** | Remote SHA was observed, but its commit object/source was not available locally and no authenticated GitHub read was possible |

The supplied reports and Phase 44 evidence are historical context only. They
are not represented as a fresh reproduction or verification.

## 3. Local workflow findings

All workflow files under `.github/workflows/` were reviewed:
`ci.yml`, `codeql.yml`, `config-validation.yml`, `dependency-review.yml`,
`main_nexhaat.yml`, and `sbom-provenance.yml`.

### Azure production deployment — **PARTIAL / remote cause BLOCKED**

At local `HEAD`, `main_nexhaat.yml` keeps deployment gated behind successful CI
on a `main` push (or a guarded manual dispatch), checks out the tested commit,
uses a job-level `production` environment, and grants `id-token: write` only
to the deploy job. The login step invokes the pinned `azure/login` action
without a credentials input or audience override and uses the existing
client/tenant/subscription secret references.

From those verified local settings and the pinned action's default audience,
the expected OIDC claims to compare are:

- Issuer: `https://token.actions.githubusercontent.com`
- Subject: `repo:shajeduzzamanenan992008inc/NexHaat:environment:production`
- Audience: `api://AzureADTokenExchange`

These are expected workflow claims, not evidence of Azure's configured
federated credential. The reported `AADSTS700213` and an Azure-side
issuer/subject/audience mismatch are **NOT TESTED** in this phase. No evidence
shows a local workflow defect; the Azure identity attachment and claims cannot
be inspected without authorized Azure access. No deployment was triggered.
See the Phase 44 administrator checklist for the exact comparison steps.

### CodeQL — **BLOCKED remotely; local configuration reviewed**

Local `codeql.yml` still analyzes JavaScript/TypeScript, Python, and GitHub
Actions; triggers include push/PR to `main`, scheduled, and manual runs. The
analysis job has `actions: read`, `contents: read`, and `security-events:
write`, initializes `security-extended`, and runs CodeQL analysis/upload.
No source-level workflow defect was established.

The earlier Code Scanning unavailable error appears in historical Phase 37/40
evidence, but current plan eligibility, repository/organization settings, and
run logs were inaccessible. The current cause—feature availability, settings,
permissions, or another error—is **NOT DETERMINED**. No language or security
analysis was removed.

### Dependency Review / Dependabot PR #31 — **BLOCKED**

Local `dependency-review.yml` still runs on pull-request open, synchronize,
reopen, and ready-for-review events; its job uses read-only `contents`
permission and `actions/dependency-review-action@v5.0.0` with
`fail-on-severity: moderate`. No no-op or bypass was added.

The current state of PR #31, its base/head SHA, action diff, latest
`Review changed dependencies` check, and whether it failed before or during
vulnerability evaluation are **NOT TESTED**. The previously reported
unsupported-feature error is historical/user-supplied evidence only. Feature
availability, dependency graph status, licensing, and the presence of actual
vulnerability findings remain unknown. No PR was approved or merged and no
action reference was changed.

### SBOM and provenance attestation — **PARTIAL / remote execution BLOCKED**

Local `sbom-provenance.yml` retains the Phase 39/42 source archive and checksum
handling: source archive output is under `RUNNER_TEMP`, the generated SBOM is
excluded, checksums are generated and checked, and upload/consumer paths use
the same SHA-derived artifact name. The artifact includes the SBOM, source
archive, and `SHA256SUMS.txt`.

Attestation is intentionally conditional on successful `generate-sbom` and
the repository/organization variable
`NEXHAAT_ENABLE_ARTIFACT_ATTESTATIONS` being exactly `true`. The signing job
declares `id-token: write`, `attestations: write`, and
`artifact-metadata: write`, and downloads the expected artifact before
attesting the archive and SBOM. The workflow source alone does not establish
that generation or upload actually succeeded, that the skip was caused by the
optional variable, or that attestation ran. Current skip reason and signing
outcome are **BLOCKED / NOT VERIFIED** without run logs and variable/plan
settings. No unsigned artifact is represented as signed.

## 4. Validation

| Check | Result |
|---|---|
| `git rev-parse --show-toplevel`, branch, HEAD, upstream, and status | **PASS** — local baseline recorded above |
| `git ls-remote origin refs/heads/main` | **PASS** — observed live remote SHA differs from cached local `origin/main`; remote commit content unverified |
| `git cat-file -e <remote-sha>^{commit}` | **NOT AVAILABLE** — remote commit object is absent locally |
| `gh auth status` | **BLOCKED** — GitHub CLI authentication unavailable |
| YAML/workflow parser or actionlint | **NOT AVAILABLE** — actionlint, Ruby, yq, yamllint, PyYAML, and Node `yaml`/`js-yaml` modules not found |
| Shell syntax checks | **NOT RUN** — no workflow shell was changed; no authenticated runner logs were available |
| Targeted application tests/builds | **NOT RUN** — no application or workflow source changed |
| `python scripts\validate_repository_structure.py --fail-on-review` | **PASS** — required docs 6/6; registry paths 190; no missing imports/config or source deletions/renames; expected documentation worktree entries were reported |
| `git diff --check` | **PASS** — no whitespace errors |

No dependency was installed. Local syntax/structure checks do not prove
remote workflow execution.

## 5. Remaining administrator actions

1. **GitHub access:** an authorized operator should provide authenticated
   read-only Actions and pull-request access, then record current run IDs,
   timestamps, conclusions, and relevant failure-log excerpts for CI, CodeQL,
   SBOM/provenance, Azure deployment, and PR #31.
2. **Azure identity:** compare the exact expected issuer, environment subject,
   and audience above against the federated credential attached to the identity
   selected by the deployment workflow. Confirm the GitHub `production`
   environment alignment. Do not use wildcard trust or long-lived credentials.
3. **CodeQL:** verify Code Scanning eligibility and repository/organization
   settings. If currently unavailable, ask the authorized GitHub administrator
   to review plan/policy and enable a supported option, then rerun all three
   analyses.
4. **Dependency Review:** verify PR #31 and its actual failing check log,
   dependency graph and feature eligibility, and distinguish unsupported
   service/API errors from vulnerability findings. Preserve the security gate.
5. **Attestation:** inspect the run's prerequisite result, attestation variable,
   entitlement, and signing logs. Enable optional signing only through an
   authorized settings process after eligibility is confirmed.
6. After approved configuration review, rerun affected workflows and verify
   results by run ID and source SHA. Any production deployment requires a
   separately approved release window; Phase 45 did not authorize one.

## 6. Changed files and final state

Phase 45 changes:

- `docs/architecture/PHASE45_CICD_BLOCKER_VERIFICATION_REPORT.md` — this
  evidence report.
- `docs/plans/nexhaat-master-plan.md` — dated Phase 45 entry, appended without
  removing or replacing existing Phase 44 content.

No workflow, application, dependency, or configuration file was changed.
Phase 44's pre-existing modified roadmap and untracked reports remain
preserved. At completion, the worktree contains those same Phase 44 changes
plus the new Phase 45 report and roadmap addition. No commit, push, merge,
deployment, production restart, or GitHub/Azure settings change was performed.

| Blocker | Phase 45 status |
|---|---|
| Azure OIDC / AADSTS700213 | **PARTIAL** — local expected claims derived; Azure-side cause and current run not verified |
| CodeQL upload | **BLOCKED** — current remote failure and feature setting unavailable |
| PR #31 Dependency Review | **BLOCKED** — current PR and check inaccessible |
| SBOM generation/archive/checksum/upload | **PARTIAL** — local workflow logic inspected; execution not verified |
| SBOM attestation skip/signing | **BLOCKED** — exact skip condition and signing outcome unavailable |
