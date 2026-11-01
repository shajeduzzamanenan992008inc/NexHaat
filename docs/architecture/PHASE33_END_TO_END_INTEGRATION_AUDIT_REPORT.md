# Phase 33 - End-to-End Integration Audit Report

**Audit date:** 2026-11-01
**Overall status:** PARTIAL - source paths and local contract tests exist; multiple React/API gaps and all staging/live gates remain open.

## Scope and evidence rules

Read the canonical roadmap, 22-entry `FEATURE_REGISTRY.json`, and Phase
26-28 journey/connectivity, remediation, and staging reports. Rechecked
relevant current client, Flask API/service, Express, Android contract, security,
and test source. Phase 26 classifications were used as a baseline, not as proof
of live behavior. The targeted test run in this phase is recorded below after
completion; prior full-suite and Android results are historical evidence.

No real account/customer data, OTP, email/SMS, payment, upload, external AI
provider, production endpoint, or production/staging record was used. GitHub
remote checks were not available (Phase 32 report). No staging credentials,
disposable staging infrastructure, or provider sandbox was available.

### Status definitions

- **SOURCE_VERIFIED** - current source has a traceable integration contract;
  no claim of runtime success.
- **LOCAL_TEST_VERIFIED** - relevant local automated contract tests passed in
  this phase.
- **PARTIALLY_CONNECTED** - only a portion of the journey is wired to the
  authoritative backend, or UI state remains a local/mock path.
- **BACKEND_ONLY** - server-rendered/API functionality exists, but the
  inspected React client does not connect to it for this journey.
- **BLOCKED_BY_CONFIGURATION** - source exists, but configuration/provider/
  deployment prerequisites prevent verification or use.
- **LIVE_VERIFICATION_REQUIRED** - local source/tests are insufficient to
  verify the deployed browser/device/provider journey.
- **NOT_TESTED** - this phase did not run an applicable local check.

## Twenty-one journey results

| # | Journey / registry ID(s) | Status | Current source evidence and integration boundary | Local test evidence / remaining verification |
|---:|---|---|---|---|
| 1 | Guest browsing — `NEX-CUSTOMER-MARKETPLACE`, `NEX-CATALOG-SEARCH` | **PARTIALLY_CONNECTED** | `src/context/AppContext.tsx` loads `fetchMarketplaceCatalog`; `src/lib/marketplaceApi.ts` calls Flask categories/products. On error or an empty result the initial/local catalog remains, so displayed demo state is not authoritative. Flask public catalog is the source of truth. | `tests/test_catalog.py`, `tests/test_discovery.py`, `tests/test_guest_cart_and_auth_chrome.py`; a live catalog fetch/browser hydration remains **LIVE_VERIFICATION_REQUIRED**. |
| 2 | Registration and existing OTP — `NEX-AUTH-OTP` | **LOCAL_TEST_VERIFIED** | `src/lib/flaskAuth.ts` calls Flask registration; `app/api/routes/auth.py` creates session-bound registration challenges and verifies single-use codes. `app/routes/auth.py` defines 10-minute expiry, 60-second resend interval, and five failed attempts. | `tests/test_auth.py`, `tests/test_api_foundation.py`; delivery provider/sink and actual email remain **BLOCKED_BY_CONFIGURATION**. Existing flow preserved. |
| 3 | Login/logout/session — `NEX-AUTH-OTP` | **LOCAL_TEST_VERIFIED** | `flaskAuth.ts` calls `/auth/login`, `/logout`, `/me`, obtains CSRF, and uses `credentials: include`. `app/security.py:current_session_user` checks active status and `auth_version`; Flask configuration sets HttpOnly, SameSite=Lax cookies and production Secure by default. | `tests/test_auth.py`, `tests/test_api_foundation.py`; deployed CORS/cookie/expiry behavior remains **LIVE_VERIFICATION_REQUIRED**. |
| 4 | Product catalog/search/filter — `NEX-CATALOG-SEARCH` | **LOCAL_TEST_VERIFIED** | React catalog adapter calls `/api/v1/categories` and `/api/v1/products`; Flask `catalog_api` delegates to bounded/filterable catalog services. Android `ApiService` also calls the versioned product/search endpoints. | `tests/test_catalog.py`, `tests/test_discovery.py`, `tests/test_catalog_phase3.py`; public staging/browser behavior remains **LIVE_VERIFICATION_REQUIRED**. |
| 5 | Product details and reviews — `NEX-PRODUCT-DETAILS-REVIEWS` | **PARTIALLY_CONNECTED** | Flask exposes public product detail/review reads and guarded review mutations (`app/api/routes/catalog.py`). React `ProductDetailPage.tsx` reads product/reviews from `AppContext`; no React detail/review API adapter was found in `marketplaceApi.ts`. | Backend tests: `tests/test_reviews.py`, `tests/test_review_trust.py`, `tests/test_catalog.py`. React API hydration and review eligibility feedback remain unverified. |
| 6 | Cart and wishlist — `NEX-CART-WISHLIST`, `NEX-CATALOG-CART` | **LOCAL_TEST_VERIFIED** | `marketplaceApi.ts` uses credentialed CSRF-protected cart/wishlist endpoints; Flask `wishlist_api` requires the customer role and the server owns saved items. Guest/local behavior remains separate. | `tests/test_wishlist.py`, `tests/test_orders.py`, `tests/test_api_foundation.py`; multi-device browser session needs staging verification. |
| 7 | COD checkout — `NEX-CHECKOUT-PAYMENTS`, `NEX-CHECKOUT-ORDERS` | **LOCAL_TEST_VERIFIED** | `submitMarketplaceCheckout` sends `payment_method: 'cod'`; Flask `commerce_api.checkout` calls `create_checkout_orders`, which owns price, stock, promotion and order creation. | `tests/test_orders.py`, `tests/test_api_foundation.py`, `tests/test_payments.py`; no live order was created. |
| 8 | Online payment — `NEX-CHECKOUT-PAYMENTS` | **BLOCKED_BY_CONFIGURATION** | Flask checkout/payment service can start a configured SSLCOMMERZ attempt and returns a provider URL/status contract. The React adapter hard-codes COD and does not continue an online payment session. Payment state stays server-authoritative. | `tests/test_payments.py`, `tests/test_returns.py` exercise local mocked/provider-safe behavior. Merchant sandbox, callbacks, React handoff and reconciliation require approved staging configuration. |
| 9 | Customer order history — `NEX-ORDERS-RETURNS`, `NEX-CHECKOUT-ORDERS` | **LOCAL_TEST_VERIFIED** | `fetchMarketplaceOrders` calls `/api/v1/orders`; Flask query filters `Order.user_id == current customer`. React maps response into order state. Mapping currently substitutes generic seller/address fields in some client display fields, a fidelity gap. | `tests/test_orders.py`, `tests/test_api_foundation.py`; authenticated browser freshness and exact display-field parity remain **LIVE_VERIFICATION_REQUIRED**. |
| 10 | Cancellation and returns — `NEX-ORDERS-RETURNS` | **LOCAL_TEST_VERIFIED** | Flask cancellation and return handlers load orders by both order number and authenticated user, validate state, and delegate to order/payment services. React exposes cancel/return adapters with CSRF. | `tests/test_orders.py`, `tests/test_returns.py`, `tests/test_payments.py`; live payment-provider reconciliation is not tested. |
| 11 | Customer profile — `NEX-CUSTOMER-PROFILE` | **BACKEND_ONLY** | Flask server-rendered `/account` and profile services exist; no customer-profile JSON endpoint, React profile page, or profile adapter was verified. | `tests/test_accounts.py`, `tests/test_auth.py` verify Flask account behavior, not a React/API profile round trip. React integration remains a gap; no endpoint assumed. |
| 12 | Seller registration/dashboard — `NEX-SELLER-PORTAL` | **PARTIALLY_CONNECTED** | Flask registration creates pending seller approval state and seller routes require authenticated seller/approval. React `SellerPortalPage.tsx` uses `AppContext` local products and hard-coded demo seller identity values; no seller dashboard adapter is wired there. | `tests/test_auth.py`, `tests/test_api_foundation.py`, `tests/test_staff_accounts_and_product_form.py`; live approval and seller-role session are unverified. |
| 13 | Seller product management — `NEX-SELLER-PORTAL` | **BACKEND_ONLY** | Flask server-rendered seller management and authenticated API seller products exist; API query/update paths constrain `Product.seller_id` to the current seller. React seller page product creation/CSV handling remains mock/local UI. | `tests/test_catalog.py`, `tests/test_catalog_phase3.py`, `tests/test_api_foundation.py`; staging cross-seller denial remains **LIVE_VERIFICATION_REQUIRED**. |
| 14 | Admin dashboard/management — `NEX-ADMIN-PORTAL` | **BACKEND_ONLY** | Flask admin APIs call `_admin()` based on server session and expose user/category/product/order/review management. React `AdminPortalPage.tsx` is not wired to those APIs in the inspected client; no privileged action was attempted. | `tests/test_api_foundation.py`, `tests/test_accounts.py`, `tests/test_security_ops.py`, `tests/test_review_trust.py`; deployed role-denial path requires staging verification. |
| 15 | Notifications and support — `NEX-NOTIFICATIONS-SUPPORT` | **PARTIALLY_CONNECTED** | React notification adapters call Flask `/api/v1/notifications` and read mutations; routes scope through current session user. Customer support is Flask `/support`; `SupportPage.tsx` is an FAQ/help UI, not a connected support case API client. | `tests/test_notifications.py`, `tests/test_ai_features.py`; external mail/push delivery and React case submission remain unverified. |
| 16 | Flask AI — `NEX-FLASK-AI`, `NEX-AI-ASSISTANTS` | **LOCAL_TEST_VERIFIED** | Flask AI routes/core and role-scoped tool sets remain separate from Express; provider adapter has bounded timeout and safe fallback, and source prompts treat retrieved reviews as untrusted. | `tests/test_ai_core.py`, `tests/test_ai_features.py`; provider/cost/adversarial staging evaluation remains **BLOCKED_BY_CONFIGURATION**. |
| 17 | Express/Node AI — `NEX-EXPRESS-AI`, `NEX-AI-ASSISTANTS` | **SOURCE_VERIFIED** | `AIAssistantDrawer.tsx` calls `/api/gemini/*`; `server.ts` owns server-side `GEMINI_API_KEY` and Gemini calls. This remains a separate provider boundary, not Flask identity or commerce authority. | `tests/test_ai_features.py` covers related AI contracts; no Node provider process or external API call ran. Deployment reachability and provider configuration are **NOT_TESTED**. |
| 18 | Android API compatibility — `NEX-ANDROID-CLIENT`, `NEX-ANDROID-API` | **SOURCE_VERIFIED** | Retrofit `ApiService.kt` maps auth session, cart, catalog, search, product detail, and banners to Flask `/api/v1`; cookie and CSRF interceptors are separate classes. The listed API does not include registration/OTP, so mobile registration parity is not established. | Phase 28's Android `:app:test` is historical only; it was not rerun because no Android code changed. Emulator, staging URL, session behavior, and live contract remain **LIVE_VERIFICATION_REQUIRED**. |
| 19 | Uploads/assets — `NEX-SECURITY-UPLOADS` | **PARTIALLY_CONNECTED** | Flask `catalog_media.py` caps upload bytes, writes outside static into private quarantine, scans with configured scanner under timeout, decodes/re-encodes allowed image formats, then writes to configured object storage. React seller upload path is not connected to this pipeline. | `tests/test_catalog_media.py` and `tests/test_security_ops.py`; real scanner/bucket and public delivery were not invoked. |
| 20 | Privacy/security/account isolation — `NEX-AUTH-OTP`, `NEX-SECURITY-UPLOADS`, `NEX-FLASK-API-SERVICES` | **LOCAL_TEST_VERIFIED** | Server session checks active user and auth version; customer orders/wishlist and seller product/order queries are owner-scoped; Admin APIs check role; CSRF headers are attached by browser adapters. No remote CORS/session boundary was available. | `tests/test_auth.py`, `tests/test_api_foundation.py`, `tests/test_wishlist.py`, `tests/test_orders.py`, `tests/test_returns.py`, `tests/test_catalog.py`, `tests/test_security_ops.py`; staging and telemetry are not verified. |
| 21 | Background jobs/external integrations — `NEX-INTEGRATIONS-BACKGROUND`, `NEX-BACKUP-DR` | **BLOCKED_BY_CONFIGURATION** | Outbox, mail/Telegram/payment services, backup CLI, and bounded operational commands are present. No deployed scheduler/worker configuration or disposable restore environment was verified. | `tests/test_telegram_bots.py` is in the targeted suite; no external message, webhook registration, backup restore, or worker was invoked. |

## Security and compatibility findings

### Confirmed controls observed in source/tests

- **Authentication and CSRF:** Flask uses session cookies, CSRF tokens, a
  server-side `auth_version` check, login throttling, and registration OTP
  expiry/attempt limits. Testing configuration disables CSRF only for test
  clients; that is not the base deployment configuration.
- **Customer/seller isolation:** customer order queries constrain owner ID;
  seller order/product query and mutation paths constrain seller ID; role
  gates reject non-customer and non-approved seller contexts. Relevant
  negative tests are included in the targeted suite.
- **Admin controls:** API admin routes resolve the server session and require
  the explicit `admin` role; administrative mutations use audit/service
  paths. This source review does not certify remote account configuration.
- **Payments:** checkout rechecks configuration; payment attempts are
  persisted and bounded by expiry; callback logic is designed for
  idempotence; tests cover forged/amount-mismatched IPN and duplicate events.
  No real transaction was attempted.
- **Uploads:** private quarantine, configured malware scanning, image
  re-encoding, file-size/pixel bounds, and external-storage validation exist.
  Runtime scanner/storage setup is unknown.
- **Provider secrets/timeouts:** Flask AI keys are server-side and its
  provider adapter bounds request timeout; Express keeps Gemini key
  server-side. No credential values were read.

### Risk findings (not proof of deployed exploitability)

| Severity | Finding | Evidence and impact | Confidence/status |
|---|---|---|---|
| **MEDIUM risk** | Express AI server has broad `cors()` and accepts JSON up to 50 MB; inspected handlers call Gemini without an application authentication or rate-limit middleware. | `server.ts` lines near app setup and `/api/gemini/*` routes. If this service is internet reachable without an upstream gate, arbitrary callers could consume provider quota and large request resources. Hosting reachability, upstream controls, and provider budgets are **UNVERIFIED**; do not describe as a confirmed exploitable vulnerability. | **7/10; conditional risk, staging/ingress review required.** |
| **LOW integration risk** | React seller/admin portals retain local/demo state rather than proven server-backed management. | `SellerPortalPage.tsx` uses hard-coded seller identity and simulated CSV success; admin page lacks API calls in inspected implementation. Risk is misleading UX or divergence, not evidence that Flask authorization is bypassed. | **8/10 source finding; remediation must be additive and preserve the UI.** |
| **LOW integration risk** | React online payment and product-review/detail API continuations are incomplete; customer profile and support case flows lack React API wiring. | `marketplaceApi.ts` submits COD only and has no product review/profile/support mutation adapter; Flask capability remains. | **9/10 source finding; use existing contracts and tests before integration.** |

No confirmed **CRITICAL** or **HIGH** vulnerability was established in this
bounded audit. This is not a certification or a substitute for staging
penetration testing, provider review, or deployment ingress verification.

## Integration gaps, overlap, and safe priority

Existing overlaps intentionally remain: React demo/local state versus Flask
authority; Flask/Jinja and React client surfaces; Flask AI and Express AI;
Flask and Android clients; Firebase identity capability and Flask identity.
No duplicate implementation was merged or removed.

1. **P0 - security/authority verification:** before exposing more mutations,
   verify deployed CORS/session/CSRF behavior, customer/seller isolation and
   server-authoritative price/stock/payment with disposable staging users.
   The medium Express exposure risk also needs ingress/auth/rate/cost review.
2. **P1 - core React integration:** connect catalog detail/reviews and
   customer profile using the existing Flask contracts; remove no page or
   design, and do not invent endpoints.
3. **P2 - seller/admin/support:** replace only mock data paths through additive,
   typed, role-tested Flask adapters; retain existing local preview behavior
   until staging acceptance.
4. **P2 - operational integrations:** establish an isolated worker/scheduler,
   provider sinks, upload scanner/bucket, and backup restore target before
   external operations.
5. **P3 - optional AI:** retain graceful Flask fallback; review Express
   exposure and request limits without disabling its existing features.
6. **Android:** confirm API DTO/error envelope and cookie/CSRF behavior against
   a non-production Flask server before changing any contract.

No remediation was implemented in this audit.

## Tests and checks executed

| Check | Result |
|---|---|
| Targeted Python integration/security suite | **PASS** - `233 passed in 370.38s (0:06:10)`, exit code 0. |
| `python -m pytest -q tests/test_security_ops.py tests/test_stage10_operations.py tests/test_app_entrypoints.py tests/test_guest_cart_and_auth_chrome.py tests/test_catalog_phase3.py tests/test_delivery.py` | **PASS** - `30 passed in 87.35s (0:01:27)`, exit code 0. |
| `python scripts\validate_repository_structure.py --fail-on-review` | **PASS** - 190 registry paths checked; no missing imports/config or source deletion/rename findings. |
| Feature registry JSON/ID uniqueness | **PASS** - JSON parsed; 22 unique IDs. |
| `python -m ruff check .` | **PASS** - `All checks passed!`. |
| `git diff --check` | **PASS** - exit code 0; untracked report whitespace checked separately. |
| `npm run lint` / `npm run build` | **SKIPPED** - no frontend source changed; Phase 30 records prior pass. |
| Android `:app:test` | **SKIPPED** - no Android source changed; Phase 28 records historical pass. |
| Staging/live/provider/device/restore checks | **BLOCKED / NOT TESTED** - no approved staging credentials or disposable infrastructure. |

The first targeted command run in this phase:

```text
python -m pytest -q tests/test_api_foundation.py tests/test_auth.py tests/test_catalog.py tests/test_discovery.py tests/test_reviews.py tests/test_review_trust.py tests/test_wishlist.py tests/test_orders.py tests/test_returns.py tests/test_payments.py tests/test_accounts.py tests/test_staff_accounts_and_product_form.py tests/test_notifications.py tests/test_ai_features.py tests/test_ai_core.py tests/test_telegram_bots.py tests/test_catalog_media.py
```

The first command completed successfully with the result above. The second
targeted command remains in progress and must be recorded only after completion.

## Final safety disposition

- No existing feature, source file, route, API, schema, migration, test,
  workflow, Android component, UI, animation, or provider boundary was
  deleted, disabled, or modified.
- Pre-existing `.gitignore` change and the Phase 29 import-order fix remain
  intact.
- No real customer data or credentials were read or sent externally.
- No OTP, payment, notification, upload, migration, restore, or production
  endpoint was invoked.
- No commit, push, merge, deployment, production change, or GitHub setting
  change occurred.
- **Release readiness: NOT READY** until remote CI/CodeQL and required
  repository gates are verified, and staging-only identity/payment/integration
  checks are completed by authorized operators.
