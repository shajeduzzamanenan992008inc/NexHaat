# Phase 44 — Administrator Action Checklist

**Date:** 2026-11-02  
**Repository:** `shajeduzzamanenan992008inc/NexHaat`  
**Local baseline:** `main` / `e4c25550fbc489d85b7b412ff855d864e9d9c645`

This checklist is based on the deployment and security workflows at the stated
local baseline. GitHub CLI authentication was unavailable, GitHub's PR API
returned 404 for PR #31, and Azure/GitHub settings were not accessible. These
items are therefore administrator verification steps, not claims that settings
are currently incorrect or have been changed. Do not share secret values.

## Azure administrator actions

1. In Microsoft Entra ID, inspect the federated identity credential associated
   with the service principal or managed identity selected by the deployment
   workflow's existing client-ID secret reference. Compare the exact claims:
   - **Issuer:** `https://token.actions.githubusercontent.com`
   - **Subject:** `repo:shajeduzzamanenan992008inc/NexHaat:environment:production`
   - **Audience:** `api://AzureADTokenExchange`

   The issuer and subject are derived from GitHub Actions OIDC and the workflow's
   `production` environment. The audience is the default declared by the exact
   `azure/login` action commit pinned in the workflow. Do not create a wildcard
   trust. Confirm the credential is attached to the identity selected by the
   workflow; do not disclose client, tenant, or subscription values.

2. In GitHub, confirm the deploy job's environment is named exactly `production`,
   its deployment branch policy is appropriate for `main`, and any intended
   reviewer protections are configured. The local workflow already declares
   that environment and scopes `id-token: write` to the deploy job.

3. If an exact Azure/GitHub claim mismatch is confirmed, correct only the
   federated credential through the approved identity-management process. Keep
   the existing least-privilege OIDC design; do not replace it with a
   long-lived credential.

4. After the identity configuration is reviewed, verify a deployment only in
   an explicitly authorized release window and through the normal protected
   `production` environment. Confirm the run's source SHA, OIDC login result,
   deployment result, and application health. No production deployment was
   started during Phase 44.

## GitHub repository administrator actions

1. Under **Settings → Security → Code security and analysis**, verify whether
   Code Scanning is available for this repository and organization plan/policy.
   Enable an authorized supported configuration if appropriate; retain the
   existing CodeQL workflow and its Python, JavaScript/TypeScript, and Actions
   analyses. Then rerun CodeQL and verify each analysis and result upload.

2. Verify that the dependency graph is enabled and that Dependency Review is
   supported for this repository's visibility and organization/enterprise
   policy. Review the current PR #31 state, exact head SHA, and latest
   `Review changed dependencies` log. The upstream v3.0.8 action changes its
   runtime from Node.js 20 to Node.js 24; the local workflow uses
   GitHub-hosted `ubuntu-latest`, but the exact PR and remote runner execution
   were not inspected. Confirm the check executes on the hosted runner and
   distinguish an unsupported-feature/API failure from completed vulnerability
   findings. Do not approve or merge the PR as part of this verification.

3. If Dependency Review is unavailable or policy-controlled, ask the
   organization/enterprise administrator to confirm the applicable entitlement
   and enablement path. Do not remove or replace the Dependency Review gate
   with a no-op.

4. For the reported skipped attestation job, inspect the run's `needs` result and
   the repository/organization variable
   `NEXHAAT_ENABLE_ARTIFACT_ATTESTATIONS`. The local workflow intentionally
   runs signing only when SBOM generation succeeds and this variable is exactly
   `true`. Confirm plan/entitlement eligibility before enabling it. Do not
   represent an unsigned artifact as signed.

5. After any authorized setting change, rerun the affected workflow(s) and
   verify their latest run IDs, source commit, job conclusions, and logs. A
   settings change or local source inspection alone is not proof of success.
