# Full Repository Audit Report

**Date:** 2026-11-02
**Status:** PARTIAL

## Baseline and coverage

- Repository: `shajeduzzamanenan992008inc/NexHaat`
- Branch / HEAD: `main` / `326af005a2a5503ef6639e36a8ad9f0f10ddca14`
- Initial worktree: clean. The baseline read-only remote comparison observed the same `main` commit; no fetch or synchronization was performed.
- Tracked files: 8,689. Of these, 8,079 are under `node_modules/`; 23 are under `android/.gradle/`, 28 under `.playwright-mcp/`, and `android/local.properties` is tracked. The local properties value is intentionally not reproduced here.
- Syntax check: 162 tracked Python files parsed without syntax errors.
- Inspected areas include Flask/API and commerce paths, database/migration metadata, React/TypeScript and Express integration points, Firebase rules/client usage, Android configuration and API adapters, GitHub Actions, dependencies, project instructions, and operational documentation.
- A deduplicated count of individually reviewed source files was not recorded. Generated/vendor trees were not reviewed file by file. This is not a complete audit of every tracked file or every runtime path.
- The focused client/AI review also inspected `server.ts`, `serverSecurity.ts`, `src/components/AIAssistantDrawer.tsx`, `src/context/AppContext.tsx`, `src/lib/firebase.ts`, and `firestore.rules`.
- The template inventory found 69 Jinja templates. Six high-impact auth, checkout, payment-status, rider, seller-order, and admin-order templates were directly reviewed; the remaining templates were not individually inspected.

## Findings

| ID | Severity | Status | Evidence and impact | Root cause / disposition |
|---|---|---|---|---|
| AUD-API-001 | Low | PASS | Non-object JSON sent to API routes was not rejected centrally while routes read mapping fields. Regression coverage at `tests/test_api_foundation.py:72-77` sends arrays and scalar values to `/api/v1/auth/login` and expects the standard 422 envelope. | Fixed with the blueprint-level JSON-object guard at `app/api/__init__.py:30-39`; one regression test function added. |
| AUD-SEC-001 | High | PARTIAL | `.github/workflows/main_nexhaat.yml` allows `workflow_dispatch` and the deployment job obtains OIDC credentials and targets Production without a workflow-declared protected environment or source-level ref gate. An unreviewed-ref deployment depends on external OIDC trust and repository controls, which were not verified. | Requires owner/admin review of GitHub protections and Azure federated trust before a narrowly scoped workflow change. Not changed. |
| AUD-SEC-002 | Medium | PARTIAL | Delivery proof images are saved under the configured static upload directory (`app/config.py:200`, `app/routes/portals.py:148-181`, `app/security.py:411-412`). Flask's default static route is public; stored proof can include private delivery/location details. | Confirmed source-level exposure. A safe correction requires private storage, authorized retrieval, and treatment of existing files; not changed during this low-risk remediation. |
| AUD-SEC-003 | Medium | PARTIAL | `firestore.rules:51-54` allows unauthenticated reads and writes under `/test/{docId}`; the client reads `test/connection` (`src/lib/firebase.ts:59-63`). Deployed rules/data were not verified. | Test namespace is permissive in source. No rule change without emulator tests and deployed-rule verification. |
| AUD-SEC-004 | Medium | PARTIAL | `firestore.rules:35-40` permits an authenticated owner to create/update order documents without field/state limits; the client writes order amount/status/payment method (`src/context/AppContext.tsx:901-908`). | Risk is limited to the Firebase client data path unless it is treated as authoritative; no Firebase-to-Flask authority bridge was verified. |
| AUD-SEC-005 | Medium | PARTIAL | `src/lib/firebase.ts:37-53` logs user ID, email, provider details, document path, and error text to the browser console. | Excessive client-side diagnostic detail; deployed logging/collection behavior was not verified. |
| AUD-SEC-006 | High | PARTIAL | `server.ts:27-45` and AI route handlers at `157,255,297,369,409,476,553,602,667,774` have no visible caller authentication; in-memory IP rate/concurrency limits are in `serverSecurity.ts:55-83`. | High only if the service is internet-accessible. Ingress/deployment topology was not verified; provider cost abuse is a possible impact. |
| AUD-AI-001 | Medium | PARTIAL | `src/components/AIAssistantDrawer.tsx:150-163` handles the failure path but does not add successful response text to the chat; a separate simulated response exists at `src/context/AppContext.tsx:1110-1152`. | User-facing AI result flow appears disconnected; no UI/provider integration test was run and no change was made. |
| AUD-SUPPLY-001 | Informational | PARTIAL | `.github/workflows/main_nexhaat.yml:40-42` selects the repository root for artifact upload and excludes only `antenv/`; tracked generated/developer-specific paths include `node_modules/`, `android/.gradle/`, `.playwright-mcp/`, and `android/local.properties`. Exact deployed artifact contents were not inspected. | Prepare a reviewed untracking/artifact-scope plan; no tracked files or deployment workflow were altered. |

**Finding counts:** 0 Critical, 2 High, 5 Medium, 1 Low, and 1 Informational. High/Medium findings include source-confirmed risks whose deployed reachability or authority remains unverified. **Confirmed fixes:** 1. **Regression tests added:** 1 test function with 5 payload variants.

### Finding reproduction and disposition details

- **AUD-AI-001:** Source-level reproduction is to submit a prompt through `AIAssistantDrawer` and follow the success path at `src/components/AIAssistantDrawer.tsx:150-163`; the result is not appended there. The separate simulated response is at `src/context/AppContext.tsx:1110-1152`. No live provider request was made. Root cause is a missing UI success-state connection; impact is that the user may not see the returned answer. Not fixed because a mock-provider UI regression test and fallback compatibility review are needed.
- **AUD-SUPPLY-001:** Reproduction/evidence is the tracked-file inventory and root artifact path at `.github/workflows/main_nexhaat.yml:40-42`. The exact artifact contents were not inspected. Root cause is broad packaging scope and already-tracked generated/local files. Potential impact is oversized or unintended deployment contents. Not fixed; no artifact was generated or deployment configuration changed.

## Verification and limitations

The full Python suite passed before the API guard was added (305 tests) and after it (306 tests). The targeted API regression suite and changed-file lint also passed after the change. Repository structure validation and `git diff --check` passed after the code change.

Authenticated GitHub/Azure run logs and deployed configuration were unavailable. Android tests, YAML/actionlint validation, current online dependency advisories, and live provider configuration were not verified. See `FULL_REPOSITORY_BLOCKED_ITEMS.md`.

No commit, push, merge, deployment, restart, GitHub/Azure setting change, or production data mutation occurred.
