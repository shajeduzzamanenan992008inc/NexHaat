# Full Repository Remediation Log

**Date:** 2026-11-02
**Status:** PARTIAL

## Applied

### REM-001 — Reject non-object JSON at the API boundary

- **Finding:** `AUD-API-001` / `SEC-007`, Low severity.
- **Files:** `app/api/__init__.py`, `tests/test_api_foundation.py`.
- **Change:** Added a parent API blueprint `before_request` guard. If a JSON request decodes to a non-null value other than an object, the existing `ApiError` handling returns a controlled 422 validation envelope. Form-based requests remain unaffected.
- **Regression coverage:** One test function exercises empty and non-empty arrays, string, number, and boolean payloads through `/api/v1/auth/login`.
- **Verification:** Targeted API tests: 17 passed. Full Python suite: 306 passed in 731.80 seconds. Ruff on changed files: passed. Repository structure validation and `git diff --check`: passed; see `FULL_REPOSITORY_TEST_RESULTS.md`.

## Deferred / not changed

- **SEC-001:** Production deployment ref/environment restrictions require GitHub and Azure administrator evidence. No workflow or remote settings were changed.
- **SEC-002:** Delivery proof privacy remediation requires private storage, an authorization-checked retrieval contract, and an existing-file migration plan. No files or storage settings were changed.
- **SEC-003:** Firebase test-collection permissions were left unchanged pending deployed-rule evidence and emulator tests.
- **SEC-004 / SEC-005:** Firebase order-field rules and client diagnostic logging were left unchanged pending deployed-rule and logging-flow verification.
- **SEC-006:** Express AI route authentication was left unchanged pending verification of public ingress and upstream controls.
- **AUD-AI-001:** The React AI success-response path was left unchanged pending a mock-provider UI regression test and confirmation of intended fallback behavior.
- **AUD-SUPPLY-001:** Tracked vendor/generated/developer-local files and deployment artifact scope need a reviewed untracking and packaging plan. No files were removed or untracked.
- Dependency upgrades, Android changes, production changes, and workflow changes were not made.

## Git and production state

No files were staged. No commit, push, merge, deployment, restart, production data change, GitHub/Azure configuration change, or secret access occurred.
