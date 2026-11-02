# Full Repository Security Report

**Date:** 2026-11-02
**Status:** PARTIAL

This report distinguishes source-confirmed issues from external configuration that could not be inspected. It is not a certification or a claim that every tracked file was security-reviewed.

## Findings

### SEC-001 — Production deployment ref/environment guard

- **Severity:** High
- **Confidence:** 8/10
- **Status:** PARTIAL; source configuration confirmed, effective remote exploitability not verified.
- **File / lines:** `.github/workflows/main_nexhaat.yml:11,50-75`
- **Evidence:** The workflow includes `workflow_dispatch`; the deployment job requests `id-token: write`, performs Azure OIDC login, and deploys to the Production slot. The job does not declare a protected GitHub environment or an explicit source-ref condition.
- **Reproduction steps:** Select a non-approved ref in the manual-dispatch UI and inspect whether the deployment job can authenticate and run. This was not attempted; effective behavior depends on external OIDC trust and repository controls.
- **Root cause:** Production deployment authorization is not visibly constrained in the workflow itself. Azure federated identity trust, repository rules, and environment settings could add controls but were not inspected.
- **Impact:** If external trust permits a manually selected non-approved ref, a workflow user with dispatch permission could cause unreviewed source to reach Production.
- **Fix:** None. Require repository/Azure administrators to verify current branch/ref restrictions, environment reviewers, and exact OIDC subject trust before authorizing a workflow change.
- **Regression test / verification:** No workflow change was made. GitHub run logs, repository environment configuration, and Azure federated credentials were unavailable. YAML validation was not run because no validator was installed.

### SEC-002 — Delivery proof images served from public static storage

- **Severity:** Medium
- **Confidence:** 9/10
- **Status:** PARTIAL; source exposure confirmed, live deployment behavior not independently exercised.
- **Files / lines:** `app/config.py:200`; `app/routes/portals.py:148-181`; `app/security.py:411-412`; Flask static setup in `app/__init__.py:22`.
- **Evidence:** Rider delivery proof images are written beneath the configured static upload directory and their names include the order identifier. The default Flask static route does not require the order owner or rider authorization.
- **Reproduction steps:** Source-level trace: upload a delivery proof through the rider flow, observe the stored filename/path, then request the corresponding static URL without an authenticated session. This trace was reviewed in source; no live upload or production URL was requested.
- **Root cause:** Sensitive proof-of-delivery media shares publicly served static storage instead of a private, authorization-checked delivery path.
- **Impact:** A person who can determine or guess an image URL may access proof that contains a recipient, home, or delivery details.
- **Fix:** None. A safe remediation requires private storage and an authenticated, order-authorized retrieval path, plus a migration/review plan for existing uploads. This is not a low-risk file-path-only change.
- **Regression test / verification:** No upload/storage behavior was changed. No live deployment or media object was accessed.

### SEC-003 — Public Firebase test collection

- **Severity:** Medium
- **Confidence:** 7/10
- **Status:** PARTIAL observation, not classified as a confirmed application vulnerability.
- **File / lines:** `firestore.rules:51-54`
- **Evidence:** The rules allow unauthenticated read/write under `/test/{docId}`. The reviewed React client reads a connection-probe document; no business-data consumer was found.
- **Reproduction steps:** In an authorized Firebase Emulator/rules test, attempt unauthenticated read and write operations beneath `/test/{docId}`. No emulator or deployed rules test was run.
- **Root cause / impact:** The rule is permissive for that test namespace. Impact depends on whether deployed rules match the source and whether the collection contains anything beyond the probe.
- **Fix:** None. Deployed Firebase rules and data were unavailable; changing rules without emulator/rules-test coverage could break an existing capability.
- **Regression test / verification:** Firebase emulator/rules tests were unavailable and not run.

### SEC-004 — Firebase order document integrity

- **Severity:** Medium
- **Confidence:** 8/10
- **Status:** PARTIAL; source rules and client writes confirmed, deployed authority not verified.
- **Files / lines:** `firestore.rules:35-40`; `src/context/AppContext.tsx:901-908`.
- **Evidence:** An authenticated owner can create/update their order document without field or state-transition restrictions; the client writes amount, status, and payment method.
- **Reproduction steps:** In an authorized Firebase Emulator/rules test, authenticate as the document owner and attempt to change protected financial/state fields. No emulator or deployed rules test was run.
- **Root cause:** Firestore owner-write rules do not constrain protected order fields or transitions.
- **Impact:** A client can tamper with its own Firebase order representation. The repository identifies Flask as the authoritative commerce backend; no evidence showed these writes can mutate Flask orders or payment status.
- **Fix:** None. Verify whether the deployed Firebase path is used for authoritative display or operations, then add a rules test and least-privilege field restrictions if compatible.
- **Regression test / verification:** Firebase emulator/rules tests and deployed integration checks were unavailable.

### SEC-005 — Client console contains user identifiers and provider diagnostics

- **Severity:** Medium
- **Confidence:** 8/10
- **Status:** PARTIAL; source confirmed, downstream collection not verified.
- **File / lines:** `src/lib/firebase.ts:37-53`.
- **Evidence:** Browser console error details include user ID, email, provider details, document path, and error text.
- **Reproduction steps:** Trigger a Firebase operation failure in an authorized local test and inspect browser console output. No live Firebase request was made.
- **Root cause:** Error logging includes user/provider context and document details in client diagnostics.
- **Impact:** Personal identifiers and implementation details may be exposed to anyone with access to the browser console or any downstream console collection tooling.
- **Fix:** None. Minimize diagnostic fields and avoid logging unnecessary personal data after reviewing support/debugging needs.
- **Regression test / verification:** No logging change or browser test was made; deployed console collection was not checked.

### SEC-006 — Paid AI routes have no visible caller authentication

- **Severity:** High if internet-accessible
- **Confidence:** 7/10
- **Status:** PARTIAL; route middleware inspected, public reachability unknown.
- **Files / lines:** `server.ts:27-45,157,255,297,369,409,476,553,602,667,774`; IP-based limits in `serverSecurity.ts:55-83`.
- **Evidence:** The reviewed Gemini-backed handlers have rate/concurrency controls but no visible authentication middleware. Those limits are in-memory and keyed by IP.
- **Reproduction steps:** In an authorized non-production environment, request a provider-backed route without credentials and inspect whether it reaches the provider. No live or provider call was made.
- **Root cause:** Caller authentication is not visible in the reviewed Express request path; reachability and any upstream gateway controls are unknown.
- **Impact:** If public, unauthenticated callers may consume paid provider quota or trigger resource use, subject to current IP limits.
- **Fix:** None. Verify ingress/auth configuration and service exposure before considering authentication changes.
- **Regression test / verification:** No provider-route integration test or deployed ingress check was run.

### SEC-007 — Malformed non-object API JSON

- **Severity:** Low
- **Confidence:** 9/10
- **Status:** PASS; locally fixed and regression-tested.
- **File / lines:** `app/api/__init__.py:30-39` (blueprint `before_request` guard); `tests/test_api_foundation.py:72-77` (non-object payload test).
- **Evidence:** Route handlers read fields from parsed request payloads. Arrays and scalar JSON values do not provide the mapping contract expected by these handlers.
- **Reproduction steps:** `POST /api/v1/auth/login` with a JSON array or scalar. The regression test now verifies the API returns a controlled 422 validation response for five non-object values; no pre-fix live request was made.
- **Root cause / impact:** No common API-boundary validation ensured the JSON root was an object, allowing malformed payloads to reach field access.
- **Fix:** A shared API guard returns the existing JSON 422 validation envelope for non-null JSON values that are not objects. Form-based routes are unaffected.
- **Regression test / verification:** One new test function covers empty/non-empty arrays, a string, a number, and a boolean. Targeted API tests and Ruff passed; the post-change full test result is in `FULL_REPOSITORY_TEST_RESULTS.md`.

## Security checks not verified

- GitHub Actions logs, repository Code Scanning availability, protected environments, branch protections, and Azure OIDC federated credentials.
- Deployed Firebase rules and Firestore contents.
- Online/current dependency advisories and a dedicated Python vulnerability scanner.
- Android build/test execution and YAML/actionlint validation.
- Production storage access controls and actual delivery proof objects.

No security setting, credential, production resource, or workflow was changed. No deployment or production test occurred.
