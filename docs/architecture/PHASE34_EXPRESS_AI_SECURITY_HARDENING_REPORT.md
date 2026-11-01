# Phase 34 — Express AI Security Hardening

**Date:** 2026-11-01  
**Status:** PARTIAL — local hardening and checks passed; deployment and provider behavior remain unverified  
**Risk classification:** MEDIUM residual risk

## Baseline and compatibility boundary

The auxiliary Express service in [`server.ts`](../../server.ts) serves the
React application and Gemini/science endpoints on port 3000. Existing
[`AIAssistantDrawer.tsx`](../../src/components/AIAssistantDrawer.tsx) callers
use same-origin REST paths (`/api/gemini/*`, `/api/science/*`) and `/live`.
The image editor and animator send FileReader data URLs; transcription sends
audio data as a JSON data URL. These paths and response shapes were preserved.

The service did not have authentication middleware. The React callers do not
send a verified Flask session/CSRF credential or an established Express
identity token. The Phase 6 integration boundary explicitly keeps Express
auxiliary and cautions against changing its origin policy without verified
deployment origins. No second identity system or incompatible Flask-auth
requirement was added. **CORS is not authentication**; direct clients can
still call public endpoints, subject to the new resource controls.

No staging/production origins were available to verify. `EXPRESS_CORS_ORIGINS`
is an optional comma-separated process environment variable containing exact
HTTP(S) origins. Production has no permissive default; an unset value allows
same-origin service operation without granting cross-origin browser access.
Development additionally allows the explicit localhost origins on ports 3000
and 5173. Credentials are not enabled. The Express process reads
`process.env`; no `.env` loader or deployment setting was added.

## Changes

- Replaced unrestricted CORS with an exact-origin allowlist and explicit
  preflight policy. Invalid, wildcard, or URL-path configuration fails startup.
- Replaced the global 50 MB JSON parser with a 1 MB default, 16 MB for
  transcription, and 32 MB for image edit/animation. Route validation bounds
  text, message history, media data, coordinates, model names, and MIME types.
  Inline image types are checked against their data URL and file signature.
- Added per-endpoint in-memory IP rate limits and shared concurrency ceilings:
  eight provider operations overall and two image/video/music operations.
  Route limits are applied before JSON parsing: chat 30/minute; grounding
  12/minute; transcription 6/minute; image operations 5/minute; video and
  animation 2/minute; music 3/minute; PubChem 30/minute; product analysis
  5/minute. Buckets are bounded, expire, and do not trust forwarded IP headers.
- Set a 60-second default Gemini HTTP timeout. Existing video interactions
  retain their explicit 300-second timeout. PubChem calls now have a 10-second
  timeout and validate the returned compound identifier before the next fetch.
- Kept existing fallback models while redacting provider error text from API
  responses and logs. Clients receive stable generic errors; logs include only
  the error class and operation label.
- Limited Live WebSocket payloads to 64 KiB, incoming base64 audio messages to
  48,000 characters, active clients to eight, and buffered output to 1 MB.
  Configured origins and same-host browser origins are accepted; requests with
  no Origin header remain possible for non-browser clients.
- Added focused middleware tests and documented `EXPRESS_CORS_ORIGINS` in
  [`.env.example`](../../.env.example).

Rate-limit settings are code-defined, per process, and keyed by the direct
client IP because the deployment proxy chain is unknown. They are not a
distributed quota and may group users behind a proxy or reset on restart.
Trusted proxy configuration was intentionally not guessed.

## Verification

| Check | Result |
|---|---|
| `npm run test:server` | **PASS** — 8 tests: exact/denied CORS and preflight, origin configuration, JSON shape/size, rate/concurrency limits, and safe error redaction |
| `npx tsc --noEmit --target ES2022 --module ESNext --moduleResolution bundler --strict --skipLibCheck --allowImportingTsExtensions --esModuleInterop server.ts serverSecurity.ts` | **PASS** |
| `npm run lint` | **PASS** |
| `npm run build` | **PASS** — Vite emitted large-chunk warnings for the 1,017.94 kB main bundle and 471.78 kB Admin bundle |
| `python -m pytest -q tests/test_ai_features.py tests/test_ai_core.py tests/test_auth.py tests/test_api_foundation.py tests/test_orders.py tests/test_returns.py` | **PASS** — 126 passed; Python emitted a non-blocking editable-install `.pth` warning for a missing external Telegram source directory |
| `python -m ruff check .` | **PASS** |
| `python scripts/validate_repository_structure.py --fail-on-review` | **PASS** — no source deletion/rename review items, missing required config, or missing relative import targets |
| `git diff --check` | **PASS** |
| Live Gemini/PubChem calls, remote browser preflight, and provider timeout/fallback behavior | **NOT TESTED** — no approved staging/provider credentials; no external calls were made |

The Node tests exercise the shared security middleware with a local Express
fixture; they do not start `server.ts` or call a real provider. Existing
frontend route/payload usage was source-inspected, not verified end-to-end.

## Remaining risks and operator gates

- **MEDIUM:** AI and science routes remain unauthenticated. CORS limits browser
  reads, not direct HTTP access; IP limits can be bypassed across source IPs.
  A verified identity/session integration and provider budget/rate policy are
  required before externally exposing these routes.
- **MEDIUM:** The real ingress, public origins, proxy IP chain, WebSocket
  behavior, provider credentials/budgets, and staging app were unavailable.
  Set and verify the exact `EXPRESS_CORS_ORIGINS` values and ingress policy
  in an approved non-production environment before staging acceptance.
- **LOW:** In-memory throttles/concurrency controls are process-local and
  restart-reset; deployment-wide limits require a verified shared control
  boundary. None was introduced speculatively.
- Image payloads are size/type bounded and signature-checked but are not fully
  decoded or scanned; these AI-only inline payloads are not persisted by this
  service. The UI file picker still accepts `image/*`; unsupported formats
  receive a controlled validation error.

No frontend, Flask, database, Android, payment, OTP, GitHub, or deployment
configuration was changed. No provider request, real user action, commit,
push, merge, or deployment occurred.
