# Phase 28 - Safe Staging Readiness Report

**Status:** PARTIAL for source-level readiness; staging execution BLOCKED
**Scope:** Read-only configuration and operational readiness inspection.
No secret values were read or printed.

## Safety and evidence boundary

Inspected source and deployment material includes `app/config.py`,
`.env.example`, `src/lib/flaskAuth.ts`, `src/lib/marketplaceApi.ts`,
`server.ts`, Android Gradle/network configuration, Flask health routes,
production readiness checks, CI/deployment workflow definitions, and the
production-release and backup/restore runbooks.

The local process had none of the checked deployment environment variables.
No repository-root `.env` file was present. `.env.example` is present and
contains development defaults and blank provider placeholders. The file
`android/local.properties` is present; its contents were not read. A
key-name-only check found no Android URL, media URL, or signing variables
from the names used by `app/build.gradle.kts` in that file. No staging URL,
approved test credentials, staging database, Azure environment settings, or
provider dashboard were available to verify. This is not evidence that
remote staging settings are absent.

No OTP/message, payment, upload, migration, backup/restore, webhook, account
action, production read/write, Azure change, deployment, or service restart
was performed. Historical public Azure GETs in Phase 26 timed out; they were
not repeated.

## Source-level configuration findings

| Boundary | Verified source behavior | Local/staging value status |
|---|---|---|
| Flask environment and secrets | `app/config.py` defaults `APP_ENV` to development, uses a development-only default secret, loads local `.env`, and deliberately refuses unsafe production JSON settings; production readiness checks validate secret length and related settings. | Local process `APP_ENV`/secret absent; root `.env` absent. Staging and Azure values **UNVERIFIED**. |
| Database | Local default is SQLite; production readiness requires PostgreSQL and TLS (`sslmode=require` or stronger). Migration history is Alembic/Flask-Migrate. | No local deployment `DATABASE_URL`; staging database, backup, migration head, and TLS **UNVERIFIED**. No migration run. |
| Flask cookies/CSRF | Session cookie is HttpOnly, SameSite Lax; Secure defaults true for production. Flask-WTF CSRF is initialized; React obtains `/api/v1/auth/csrf` and sends `X-CSRFToken` with credentialed requests. | Source **PASS**; deployed cookie/CORS/preflight flow **BLOCKED** pending approved staging origins. |
| CORS and frontend origin | `VITE_FLASK_API_ORIGIN` is optional; React defaults to same-origin and uses `credentials: include`. No Flask application CORS allowlist configuration was found in the inspected source. `server.ts` calls broad `cors()` without an explicit origin list. | `.env.example` has no frontend-origin setting; process variable absent. Deployed proxy/CORS policy **UNVERIFIED**. Separate-origin staging must not proceed until credentialed CORS is explicitly approved. |
| Email and OTP | Flask config supports Brevo API key/sender and mail timeout; `.env.example` has blank mail placeholders. Registration/OTP delivery is an external side effect. | Local mail settings absent; staging provider/sink and OTP delivery **UNVERIFIED**. No message sent. |
| SMS | SMS is disabled by default in source; provider/key/sender fields are supported. Example settings are disabled/blank. | Local settings absent; staging SMS provider **UNVERIFIED**. No SMS sent. |
| Online payment | Flask supports SSLCOMMERZ; `SSLCOMMERZ_SANDBOX` defaults true in source and the example. Production-readiness rejects missing credentials and sandbox mode. React checkout currently exposes COD only pending approved staging configuration. | Local payment values absent; staging sandbox merchant/callback setup **UNVERIFIED**. No payment initiated. |
| Upload storage/scanning | Catalog media requires a private quarantine, available scanner, safe image decode/re-encode, configured bucket and public base URL; production readiness checks storage URL and scanner. The smoke check writes and deletes a temporary object only with explicit confirmation. | Local bucket/public URL absent from process and no `.env`; scanner availability **NOT TESTED**. Staging bucket, access policy and scanner **UNVERIFIED**. No upload. |
| Flask AI | AI is disabled by default; provider, key, model, base URL, timeout and request limits are configurable. | Local AI variables absent; provider credentials/settings **UNVERIFIED**. No provider call. |
| Express AI | `server.ts` constructs a Google GenAI client from server-side `GEMINI_API_KEY`; Express uses broad `cors()` and a 50 MB JSON parser. | Local `GEMINI_API_KEY` absent; staging provider/origin/request limits **UNVERIFIED**. No provider call. |
| Android | `build.gradle.kts` reads debug/release URL, media URL and signing properties from environment or `android/local.properties`; debug defaults to emulator localhost and release defaults to a placeholder URL. No separate staging flavor was established in the inspected build file. | `android/local.properties` present, not read; key-name check says expected NEXHAAT URL/media/signing keys absent there. Staging URL/build **BLOCKED**. |
| Health and readiness | Flask exposes `/health/live` (no DB dependency), `/health`, `/health/db`, `/health/ready` (DB probe), and `/api/v1/health` (API response). | Source **PASS**; staging health, DB readiness and routing **NOT TESTED**. |
| Logging/monitoring | Flask uses Python logging; health readiness logs DB failure. Express uses console logging. No configured metrics/tracing/alert pipeline was verified. | Runtime log collection, redaction, telemetry, retention and alert routes **UNVERIFIED**. |
| Background operations | Flask CLI exposes bounded retry/digest/expiry and readiness/smoke commands; outbox and provider services exist. A deployed scheduler/worker and queue monitoring were not established in inspected evidence. | Scheduler, worker, credentials, retry visibility **UNVERIFIED**. No task invoked. |
| Backup/rollback | Backup and release runbooks exist; restore command overwrites the database configured for that process and requires `--confirm-target`. Phase 18 says isolated restore rehearsal is blocked. | Staging backup retention, isolated restore target, artifact retention and rollback rehearsal **BLOCKED / UNVERIFIED**. |
| Deployment boundary | CI workflow has PR/push/manual triggers and read-only contents permissions. Production workflow is bounded to successful CI push from `main` or confirmed manual dispatch on `main`, exact tested SHA, `production` environment, OIDC on deploy job. | Local workflow source **PASS**. No staging workflow/environment was found in the inspected files; GitHub/Azure environment settings **UNVERIFIED**. No workflow triggered. |

## Staging verification matrix

`Expected` describes the result required before a staging acceptance decision.
`Actual` reflects only safe local source/file inspection. Remote runtime values
remain unknown unless explicitly stated.

| Check | Required environment | Safe procedure | Expected result | Actual result | Status | Responsible component | Evidence |
|---|---|---|---|---|---|---|---|
| Environment separation | Approved staging app and isolated settings | Administrator confirms staging hostname, environment name, separate credentials and non-production database; compare names/presence only | No production DB/provider credentials in staging; staging clearly identified | No `.env`; process deployment variables absent; Azure settings not accessible | **BLOCKED** | Hosting/operator | `app/config.py`; `.env.example`; production workflow |
| Flask secret/session/database configuration | Staging Flask runtime | Run the existing production/readiness checks against staging configuration without printing values; verify DB hostname/backend/TLS class without credentials | Unique strong secret; secure cookies; isolated TLS PostgreSQL; no secret output | Defaults/checks are present in source; staging values **UNVERIFIED** | **BLOCKED** | Flask/hosting | `app/config.py`; `app/services/review.py`; `production-check` |
| Frontend origin, cookies, CSRF | React and Flask staging origins | With disposable users, inspect preflight, Set-Cookie attributes, CSRF fetch and rejected missing-token mutation in browser | Explicit approved origin, credentials supported, HttpOnly/Secure cookie, CSRF rejection works | Adapter contract exists; deployment CORS and cross-origin behavior **NOT TESTED** | **BLOCKED** | React/Flask/ingress | `src/lib/flaskAuth.ts`; `src/lib/marketplaceApi.ts`; `app/extensions.py` |
| Database migration compatibility | Disposable staging database | Snapshot/backup first; inspect Alembic heads; apply only reviewed migrations under operator approval; verify row/schema invariants | One expected head, backward-compatible deployment order, restore path available | Alembic tooling exists; no staging DB inspected and no migration applied | **NOT TESTED** | Database/Flask | `migrations/`; Phase 18 report |
| Registration OTP and mail | OTP sandbox or test sink | Use only disposable account and a provider sandbox/sink; inspect challenge expiry and denial paths | Test message only, single-use/expiry enforced, no production destination | Source and local tests exist; provider setup/delivery not verified; no message sent | **BLOCKED** | Auth/mail | `app/api/routes/auth.py`; `app/services/mail.py`; `tests/test_auth.py` |
| SMS provider | SMS sandbox or disabled test mode | Keep disabled unless sandbox and test recipient are approved; run adapter mocks locally | No real recipient; bounded retry and safe error output | Source default disabled; no provider call | **BLOCKED** | Auth/SMS | `app/config.py`; `app/services/sms.py`; `tests/test_sms_service.py` |
| Payment sandbox and callbacks | Isolated merchant sandbox | Use sandbox-only merchant; approved callback URL; synthetic order; test duplicate/invalid callbacks and reconcile | Provider-verified amount/currency/state; idempotent callbacks; COD unchanged | Local tests/source only; credentials/callbacks absent or unverified; no payment | **BLOCKED** | Commerce/payment | `app/services/sslcommerz.py`; `app/routes/orders.py`; `tests/test_payments.py` |
| Catalog uploads and media | Disposable bucket/prefix and scanner | Before any external write, operator confirms target; use synthetic image and the existing explicit smoke-check gate; verify and clean only test key | Scanner available; sanitized object; private credentials; predictable cleanup; no public sensitive data | Source pipeline verified; actual scanner/bucket not tested. Smoke command not run | **BLOCKED** | Catalog/storage | `app/services/catalog_media.py`; `tests/test_catalog_media.py` |
| Flask AI provider | Provider sandbox/approved budget | Keep disabled or mock locally; if approved, use synthetic prompts, bounded rate/cost, inspect redacted logs | Optional AI failure does not block commerce; provider key stays server-side | Source defaults disabled; no provider call | **BLOCKED** | Flask AI/provider | `app/config.py`; `app/ai/`; `tests/test_ai_core.py` |
| Express Gemini provider | Provider sandbox/approved budget | Validate approved origins and request limits; use synthetic prompt and mocked errors before staging call | Key server-side, bounded payload/cost/timeout, no CORS wildcard for credentialed private APIs | `GEMINI_API_KEY` absent in local process; no staging call. Source currently uses broad CORS and 50 MB JSON body limit | **BLOCKED** | Express/provider | `server.ts`; `tests/test_ai_features.py` |
| Android staging API URL/session | Approved staging API and test device | Build debug/staging only with approved URL; test synthetic account cookie, CSRF, catalog and logout | Correct HTTPS non-production origin; session behavior documented; no production signing material | No staging flavor established; local.properties values not read; expected URL keys absent | **BLOCKED** | Android | `android/app/build.gradle.kts`; `NetworkModule.kt`; Phase 26 |
| Health/readiness and routing | Staging app and DB | GET liveness and readiness from authorized staging runner; do not issue mutation requests | Liveness independent of DB; readiness fails closed when DB unavailable | Route implementations inspected; staging requests not made | **NOT TESTED** | Flask/hosting | `app/routes/main.py`; `app/api/routes/health.py` |
| Logging, metrics, alerts | Staging telemetry stack | Generate synthetic request/error; verify request correlation, redaction, dashboards and alert route | Useful signals without tokens/PII; actionable owner and runbook | Source logging inspected; deployed observability/alert wiring not verified | **NOT TESTED** | Operations | Flask logging; `server.ts`; runbooks |
| Scheduled tasks and outbox | Staging scheduler/worker and mock provider | Start one bounded task with synthetic data; verify idempotency, retry cap, queue age and stop behavior | Exactly documented retry/reconciliation behavior; no production sends | CLI entry points exist; deployed worker/scheduler unknown; no task invoked | **BLOCKED** | Operations/integrations | `app/__init__.py`; `app/services/`; Phase 26 |
| Backup and isolated restore | Separate disposable staging DB/storage | Take approved backup; restore only to separate target; validate schema, counts and synthetic commerce state | Restore verified without overwriting active staging/production; duration recorded | Phase 18 records restore rehearsal blocked; target unavailable in this phase | **BLOCKED** | Database/operations | `.github/runbooks/backup-restore.md`; Phase 18 report |
| CI and deployment separation | GitHub repository access | Review exact CI and deployment triggers, permissions, SHA and Environment gate; require remote checks only after authenticated review | PR CI cannot deploy; production remains gated; staging does not use production settings | Local workflow definitions inspected; remote Actions/environment settings unavailable | **PARTIAL** | Release/hosting | `.github/workflows/ci.yml`; `.github/workflows/main_nexhaat.yml`; Phase 25 |
| Privacy and tenant isolation | Synthetic customer/seller/Admin accounts | Run owner/role-denial tests in local client tests then staging browser/device | No cross-account records; explicit role denial; no customer data in logs | Relevant local test suites passed in Phase 26; staging denial run absent | **BLOCKED** | Identity/API | Phase 26; `tests/test_auth.py`; `tests/test_wishlist.py`; `tests/test_returns.py` |

## Staged rollout plan

1. **Approve isolation:** an authorized operator identifies separate staging
   app, database, object-storage bucket/prefix, provider sandboxes, test
   accounts, and log/telemetry access. Do not copy production customer data.
2. **Inventory settings safely:** record required key names and
   present/absent/unverified states only. Confirm staging cannot resolve to
   production database, mail/SMS, payment, AI, Telegram, or storage resources.
3. **Prepare compatible schema:** review migration head, lock/compatibility
   impact, backup and recovery path. Apply migrations only in the isolated
   staging DB with explicit operator approval; this phase performed none.
4. **Deploy approved artifact to staging only:** bind the exact reviewed
   commit/artifact to the staging target through an authorized process. No
   workflow/settings were changed here.
5. **Start with read-only checks:** liveness/readiness, API health, catalog,
   product details, and safe asset reads. Verify logs do not disclose secrets.
6. **Exercise synthetic identity and commerce:** disposable registration/
   OTP sink, login/logout, CSRF, role/ownership denials, cart, COD checkout,
   order history/cancel/return. Do not use production accounts or payment.
7. **Exercise optional providers separately:** payment sandbox, mail/SMS
   sink, AI provider sandbox, Telegram test bot, and disposable-media bucket
   only after each provider owner approves the target and cost/side effect.
8. **Verify workers/recovery:** bounded synthetic jobs, duplicate/retry
   scenarios, queue age, and restore into a different isolated DB. Record
   RPO/RTO observations without claiming production DR readiness.
9. **Release decision:** owner reviews exact results, unresolved risks,
   monitoring, rollback artifact, and production approval requirements.
   Staging success does not authorize or imply production deployment.

## Rollback checklist

- Stop or disable only the staging rollout/feature flag/scheduler introduced
  for the approved test; do not touch production services.
- Retain logs and audit evidence with secrets/PII redacted; record artifact
  SHA and test data ownership.
- If an additive schema change is later tested, prefer a forward-compatible
  rollback/roll-forward strategy. Do not reverse destructive migrations or
  restore over active data.
- Restore only into a verified disposable target. Confirm source and target
  are distinct before invoking the restore command's explicit confirmation.
- Disable sandbox callback registration or test credentials through the
  authorized provider owner; do not rotate/change production credentials.
- Clean only explicitly identified synthetic objects/records in the
  disposable staging namespace after retaining required audit evidence.
- Re-run staging health, migration-head, and contract checks after rollback.
- Obtain separate explicit approval for any production-facing action.

## Phase 28 disposition

| Area | Result |
|---|---|
| Source configuration and local template inspection | **PASS** |
| Local secret-value handling | **PASS** - values not read or printed |
| Dedicated staging configuration/runtime | **BLOCKED / UNVERIFIED** |
| React/Flask CORS, cookies, CSRF in deployed environment | **BLOCKED** |
| OTP, SMS, payment, AI, media and Telegram providers | **BLOCKED / NOT TESTED** |
| Android staging compatibility | **BLOCKED / NOT TESTED** |
| Database migration/restore rehearsal | **BLOCKED / NOT TESTED** |
| Health, monitoring, scheduled workers, and alerting | **NOT TESTED** |
| Production configuration/data/settings or services changed | **NO** |

No credentials were created or changed. No OTP/message, payment, upload,
migration, restore, deployment, restart, production data/configuration change,
or GitHub setting change occurred.

## Local validation evidence

| Command | Result |
|---|---|
| `python scripts\validate_repository_structure.py --fail-on-review` | **PASS** - required docs `6/6`, 190 registry paths checked, no missing imports/config, no source deletion/rename findings. Worktree review counts include pre-existing changes. |
| `python -c "import json; from pathlib import Path; p=Path('docs/architecture/FEATURE_REGISTRY.json'); d=json.loads(p.read_text(encoding='utf-8')); ids=[f['id'] for f in d['features']]; assert len(ids)==22 and len(ids)==len(set(ids)); print(f'FEATURE_REGISTRY JSON PASS; entries={len(ids)}; unique IDs PASS')"` | **PASS** - 22 entries, unique IDs. |
| `npm run lint` | **PASS** - `tsc --noEmit`, exit code 0. |
| `npm run build` | **PASS with warning** - Vite build succeeded; existing chunks exceed the 500 kB advisory threshold. |
| `python -m pytest -q` | **PASS** - 305 passed in 370.81s. Python emitted an environment `.pth` warning for a missing sibling `D:\FTP\Telegram-Bot\src`; it did not fail the suite. |
| `$cache = Join-Path $env:TEMP 'NexHaatPhase28GradleProjectCache'; & .\android\gradlew.bat -p android :app:test --no-daemon --project-cache-dir $cache` | **PASS with warnings** - `BUILD SUCCESSFUL` in 5m 41s; unsigned release, Android SDK XML compatibility, deprecated Android/Gradle APIs, and kapt processor-option warnings. |
| `git diff --check` | **PASS** for tracked/staged diff. New untracked report whitespace was separately checked. |

The local checks validate source and existing automated tests. They do not
establish staging runtime configuration, service health, provider delivery,
device behavior, or restore readiness.
