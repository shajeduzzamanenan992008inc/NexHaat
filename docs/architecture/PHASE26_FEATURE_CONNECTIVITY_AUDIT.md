# Phase 26 — End-to-End Feature Connectivity Audit

**Date:** 2026-11-01
**Registry:** Existing 22 feature IDs from `FEATURE_REGISTRY.json`
**Overall status:** PARTIAL — local contracts and tests are broad; live,
staging, device, and provider verification remain unavailable

## Audit method and safety

The repository guidance, AI Studio integration standards, Phase 5–25 reports,
registry, Flask routes/API/services/models, React adapters/context/pages,
Express service, Android Retrofit contract, and focused tests were inspected.
The audit traced request/response boundaries rather than treating a page or
endpoint name as proof of connectivity.

Only read-only public live GET requests were attempted against the supplied
Azure URL. `/`, `/health`, and `/api/v1/health` each timed out after 20
seconds. No login, OTP, upload, checkout, payment, webhook, account mutation,
or production record access was attempted. No real customer data or provider
credentials were used.

## Connectivity status legend

- **CONNECTED_AND_TESTED** — local request/handler/business path and relevant
  local tests pass.
- **CONNECTED_BUT_NOT_LIVE_VERIFIED** — source path and local evidence exist,
  but staging/live/provider verification is unavailable.
- **FRONTEND_ONLY** — UI exists without a verified authoritative backend path.
- **BACKEND_ONLY** — backend/server-rendered path exists without a verified
  React/Android connection.
- **PARTIALLY_CONNECTED** — only part of the requested journey is connected,
  or intentional local/mock overlap remains.
- **BLOCKED_BY_CONFIGURATION** — source path is present but required
  configuration/provider/environment is unavailable.
- **DUPLICATE_OR_OVERLAPPING** — preserved parallel boundaries require
  deliberate consolidation; no implementation was removed.
- **NOT_VERIFIED** — insufficient evidence for a stronger classification.

## Journey-by-journey trace

| # | Journey / registry IDs | Status | Traced evidence and connection boundary | Tests / failure point |
|---:|---|---|---|---|
| 1 | Guest browsing — `NEX-CUSTOMER-MARKETPLACE`, `NEX-CATALOG-SEARCH` | **PARTIALLY_CONNECTED** | `AppContext` effect calls `fetchMarketplaceCatalog()` → `src/lib/marketplaceApi.ts:fetchMarketplaceCatalog` → `GET /api/v1/categories` and `GET /api/v1/products`; Flask `catalog_api.list_categories/list_products` → `get_active_categories/get_catalog_products` → catalog models. Empty/error responses preserve local mock state. | `tests/test_catalog.py`, `tests/test_discovery.py` pass locally; supplied Azure public GETs timed out, so live response/UI hydration is not verified. |
| 2 | Registration and existing OTP — `NEX-AUTH-OTP` | **CONNECTED_BUT_NOT_LIVE_VERIFIED** | `flaskAuth.ts:startFlaskRegistration` → `POST /api/v1/auth/register`; `auth_api.register` creates a session-bound registration challenge and delegates email delivery; verification continues at `/auth/verify-registration` / `POST /api/v1/auth/register/verify`. Session cookie and CSRF are used for state-changing requests. | `tests/test_auth.py`, `tests/test_sms_service.py`; email/provider configuration and real delivery were not used. |
| 3 | Login/logout/session — `NEX-AUTH-OTP` | **CONNECTED_BUT_NOT_LIVE_VERIFIED** | `flaskAuth.ts:loginWithFlask/logoutFromFlask/getCurrentFlaskUser` → `/api/v1/auth/login`, `/logout`, `/me`; `auth_api.login/logout/me` → Flask session and `current_session_user`; `AppContext` initializes session state and retains Firebase as a separate capability. | `tests/test_auth.py`, `tests/test_accounts.py` pass; live cookie/CORS behavior timed out/unverified. |
| 4 | Search, filtering, categories — `NEX-CATALOG-SEARCH` | **CONNECTED_BUT_NOT_LIVE_VERIFIED** | Catalog UI uses server adapter and Flask `catalog_api.search_products/category_products/list_products`; query, price, rating, stock, variant, seller, sort, and pagination are validated before `services.catalog:get_catalog_products`. Android also calls `/api/v1/search`. | `tests/test_catalog.py`, `tests/test_catalog_phase3.py`, `tests/test_discovery.py`; no live browser/API check. |
| 5 | Product details and reviews — `NEX-PRODUCT-DETAILS-REVIEWS` | **PARTIALLY_CONNECTED** | Flask supports `GET /api/v1/products/<id>`, reviews, review submit/helpful/report through `catalog_api` and `services.reviews`. React `ProductDetailPage` uses `AppContext` product/review state and toggles wishlist, but no verified React call to product-detail/review endpoints was found in `marketplaceApi.ts`. | `tests/test_reviews.py`, `tests/test_review_trust.py`, `tests/test_catalog_media.py`; React detail-to-API review hydration is not verified. |
| 6 | Cart and wishlist — `NEX-CART-WISHLIST`, `NEX-CATALOG-CART` | **CONNECTED_BUT_NOT_LIVE_VERIFIED** | `AppContext:addToCart/updateCartQuantity/removeFromCart/toggleWishlist` call typed adapter functions for customer sessions → `/api/v1/cart/items` and `/api/v1/wishlist`; Flask `commerce_api`/`wishlist_api` enforce customer role, ownership, stock, and CSRF. Guest users retain local fallback. | `tests/test_wishlist.py`, `tests/test_orders.py`; authenticated browser hydration/multi-device behavior unverified. |
| 7 | Checkout and COD — `NEX-CHECKOUT-PAYMENTS`, `NEX-CHECKOUT-ORDERS` | **CONNECTED_BUT_NOT_LIVE_VERIFIED** | `CheckoutPage` → `AppContext:createMarketplaceOrder` → `submitMarketplaceCheckout` → `POST /api/v1/checkout` with `payment_method: cod`; `commerce_api.checkout` → `services.checkout:create_checkout_orders` → order/payment/catalog models; response maps back to UI and clears local cart. | `tests/test_orders.py`, `tests/test_promotions.py`; no live purchase or production record was created. |
| 8 | Online payment — `NEX-CHECKOUT-PAYMENTS` | **BLOCKED_BY_CONFIGURATION** | Flask HTML/API checkout supports `sslcommerz`, `begin_payment_attempt`, payment status/retry, and verified success/return/IPN callbacks in `app/routes/orders.py`; API returns `checkout_url`. React marketplace adapter currently submits COD only, so a complete React online-payment continuation is not connected. | `tests/test_payments.py`, `tests/test_returns.py` cover provider-safe logic; gateway credentials/configuration and real callbacks were not used. |
| 9 | Customer order history — `NEX-ORDERS-RETURNS`, `NEX-CHECKOUT-ORDERS` | **CONNECTED_BUT_NOT_LIVE_VERIFIED** | `AppContext` customer effect → `fetchMarketplaceOrders` → `GET /api/v1/orders`; `commerce_api.customer_orders` scopes by `Order.user_id` and serializes items/payment/refund state; `MyOrdersPage` consumes context state. | `tests/test_orders.py`; live authenticated session and status freshness unverified. |
| 10 | Cancellation and return — `NEX-ORDERS-RETURNS` | **CONNECTED_BUT_NOT_LIVE_VERIFIED** | `AppContext:cancelOrder/requestOrderReturn` → `POST /api/v1/orders/<order_number>/cancel|return`; `commerce_api` → `services.orders` / `services.payments.request_order_return`; order ownership and state/payment rules are checked, then response updates UI. | `tests/test_orders.py`, `tests/test_returns.py`; live provider reconciliation and browser path unverified. |
| 11 | Customer profile — `NEX-CUSTOMER-PROFILE` | **BACKEND_ONLY** | Flask `/account` and auth account handlers use `User`, `CustomerProfile`, `CustomerAddress`, and profile services. The registry and source inspection did not establish a React profile page or marketplace API adapter for this journey. | `tests/test_accounts.py`, `tests/test_auth.py`; server-rendered path is locally tested, React connection is absent/unverified. |
| 12 | Seller registration and dashboard — `NEX-SELLER-PORTAL` | **PARTIALLY_CONNECTED** | `/seller-application` → registration challenge with seller profile; `/seller/dashboard` guarded by `role_required("seller")` and approval state. React `SellerPortalPage` exists, but no verified React seller API adapter for dashboard data was found. | `tests/test_auth.py`, `tests/test_staff_accounts_and_product_form.py`; seller approval and live role session not verified. |
| 13 | Seller product management — `NEX-SELLER-PORTAL` | **BACKEND_ONLY** | Server-rendered `/seller/catalog`, `/seller/products/new`, edit, archive, variants; `approved_seller_required` and seller-owned queries lead to catalog models/media services. The React seller page does not establish a connected management API path. | `tests/test_catalog.py`, `tests/test_catalog_media.py`, `tests/test_staff_accounts_and_product_form.py`; live seller isolation not verified. |
| 14 | Admin dashboard and management — `NEX-ADMIN-PORTAL` | **BACKEND_ONLY** | `/admin` in `app/routes/portals.py` and admin order/product/customer/review routes in `app/routes/orders.py` use `admin_required`, audit services, and catalog/order/review models. `AdminPortalPage` is present, but privileged React endpoint connectivity is not established. | `tests/test_security_ops.py`, `tests/test_stage10_operations.py`, `tests/test_review_trust.py`; no live privileged action attempted. |
| 15 | Notifications and support — `NEX-NOTIFICATIONS-SUPPORT` | **PARTIALLY_CONNECTED** | React notifications use `/api/v1/notifications` and read endpoints → `notifications_api` → notification service/model. Support remains Flask `/support` with support models/notification service; no equivalent React support API path was verified. | `tests/test_notifications.py`, `tests/test_stage10_operations.py`; external delivery and live support flow unverified. |
| 16 | Flask AI features — `NEX-FLASK-AI` | **CONNECTED_BUT_NOT_LIVE_VERIFIED** | Server-rendered `/ai` routes and `app/ai/core`, marketplace/seller/admin/security tools apply role permissions, rate limits, guardrails, and audit boundaries. The Flask AI path is distinct from the Express client calls. | `tests/test_ai_core.py`, `tests/test_ai_features.py`; provider availability, cost, and adversarial prompt evaluation not live-tested. |
| 17 | Express/Node AI — `NEX-EXPRESS-AI` | **CONNECTED_BUT_NOT_LIVE_VERIFIED** | `AIAssistantDrawer` calls `/api/gemini/chat`, grounding, transcription, image/video/music, PubChem, product analysis, and WebSocket; `server.ts` handlers call server-side `GEMINI_API_KEY` provider. | `tests/test_ai_features.py` plus TypeScript lint/build; live Node process/provider credentials unavailable. Known risks remain broad CORS and 50 MB JSON limit. |
| 18 | Android API compatibility — `NEX-ANDROID-CLIENT`, `NEX-ANDROID-API` | **CONNECTED_BUT_NOT_LIVE_VERIFIED** | Retrofit `ApiService` maps auth, cart, categories, products, search, product detail, and banners to Flask `/api/v1`; `NetworkModule` creates the service and interceptors preserve cookies/CSRF. | Android `:app:test` passed previously; device/emulator, live API, and release signing were not tested. |
| 19 | Uploads and assets — `NEX-SECURITY-UPLOADS` | **PARTIALLY_CONNECTED** | Seller product forms call catalog media validation/storage in Flask; product media is serialized through catalog responses. No verified React upload adapter or live private-file delivery path was found. | `tests/test_catalog_media.py`, `tests/test_security_ops.py`; malware scanning/object storage and abuse cases are not live verified. |
| 20 | Privacy, security, account isolation — `NEX-AUTH-OTP`, `NEX-SECURITY-UPLOADS`, `NEX-FLASK-API-SERVICES` | **CONNECTED_BUT_NOT_LIVE_VERIFIED** | Flask sessions/CSRF in `flaskAuth.ts`; API routes use `current_session_user`, role checks, owner-scoped order/payment/wishlist queries, throttles, audit, and secure error envelopes. | Auth, wishlist ownership, returns, security operations, and API foundation tests passed; full staging CORS/session, browser, and production telemetry remain unverified. |
| 21 | Background jobs and external integrations — `NEX-INTEGRATIONS-BACKGROUND`, `NEX-BACKUP-DR` | **BLOCKED_BY_CONFIGURATION** | Outbox model/service, Telegram webhook modules, backup CLI/service, notification mail queue, and payment callbacks exist with local safeguards. Deployment scheduler/worker, Telegram/mail credentials, disposable restore target, and provider endpoints were not available. | `tests/test_telegram_bots.py`, `tests/test_security_ops.py`, `tests/test_stage10_operations.py`; live external execution intentionally not run. |

## Existing registry ID coverage

All existing registry entries are preserved. The previous broad IDs remain
compatibility records and are mapped to the detailed journey IDs below; no
new registry IDs were created in Phase 26.

| Existing registry ID | Journey coverage | Connectivity status |
|---|---|---|
| `NEX-AUTH-OTP` | Registration/OTP; login/logout/session; privacy/security | **CONNECTED_BUT_NOT_LIVE_VERIFIED** |
| `NEX-CATALOG-CART` | Guest browsing; catalog/search; cart/wishlist | **DUPLICATE_OR_OVERLAPPING** with the split catalog/cart IDs |
| `NEX-CHECKOUT-ORDERS` | COD checkout; order history; cancellation/returns | **DUPLICATE_OR_OVERLAPPING** with the split checkout/order IDs |
| `NEX-AI-ASSISTANTS` | Flask AI and Express AI | **DUPLICATE_OR_OVERLAPPING**; separate server boundaries are retained |
| `NEX-ANDROID-API` | Android API compatibility | **DUPLICATE_OR_OVERLAPPING** with `NEX-ANDROID-CLIENT` |
| `NEX-BACKUP-DR` | Background operations and backup/restore | **BLOCKED_BY_CONFIGURATION** for disposable restore/live operations |
| `NEX-CUSTOMER-MARKETPLACE` | Guest browsing | **PARTIALLY_CONNECTED** |
| `NEX-CATALOG-SEARCH` | Search, filtering, category navigation | **CONNECTED_BUT_NOT_LIVE_VERIFIED** |
| `NEX-PRODUCT-DETAILS-REVIEWS` | Product detail and reviews | **PARTIALLY_CONNECTED** |
| `NEX-CART-WISHLIST` | Cart and wishlist | **CONNECTED_BUT_NOT_LIVE_VERIFIED** |
| `NEX-CHECKOUT-PAYMENTS` | COD checkout and online payment | **BLOCKED_BY_CONFIGURATION** for online payment |
| `NEX-ORDERS-RETURNS` | Order history, cancellation, returns | **CONNECTED_BUT_NOT_LIVE_VERIFIED** |
| `NEX-CUSTOMER-PROFILE` | Customer profile | **BACKEND_ONLY** |
| `NEX-SELLER-PORTAL` | Seller registration/dashboard and product management | **PARTIALLY_CONNECTED** |
| `NEX-ADMIN-PORTAL` | Admin dashboard/management | **BACKEND_ONLY** for verified privileged management paths |
| `NEX-NOTIFICATIONS-SUPPORT` | Notifications and support | **PARTIALLY_CONNECTED** |
| `NEX-FLASK-AI` | Flask AI | **CONNECTED_BUT_NOT_LIVE_VERIFIED** |
| `NEX-EXPRESS-AI` | Express/Node AI | **CONNECTED_BUT_NOT_LIVE_VERIFIED** |
| `NEX-FLASK-API-SERVICES` | Shared Flask API/service boundary | **CONNECTED_BUT_NOT_LIVE_VERIFIED** |
| `NEX-ANDROID-CLIENT` | Android API compatibility | **CONNECTED_BUT_NOT_LIVE_VERIFIED** |
| `NEX-SECURITY-UPLOADS` | Uploads/assets; privacy/security | **PARTIALLY_CONNECTED** |
| `NEX-INTEGRATIONS-BACKGROUND` | Background jobs and external integrations | **BLOCKED_BY_CONFIGURATION** |

`BACKEND_ONLY` and `BLOCKED_BY_CONFIGURATION` in this table are journey
classifications, not deletion or acceptance decisions for registry entries.

## Cross-cutting findings

### Confirmed connections

- React auth and marketplace mutation adapters use credentialed cookies and
  CSRF headers through `src/lib/flaskAuth.ts` and
  `src/lib/marketplaceApi.ts`.
- Flask `/api/v1` blueprints are centrally registered in
  `app/api/__init__.py`.
- Server-side checkout, pricing, stock, payment, order, return, seller, and
  notification operations delegate into Flask services and database models.
- Android contracts point to the same versioned Flask API envelope.
- Express AI is a separate provider boundary and does not become the Flask
  identity or commerce authority.

### Incomplete or overlapping connections

- React local/mock state intentionally remains active for guest preview and
  fallback. It must not be interpreted as server-authoritative state.
- Product reviews, customer profile, seller management, admin operations, and
  support are not fully connected from the React pages to the corresponding
  Flask APIs; server-rendered Flask paths remain the verified owner.
- React online payment continuation is not represented in the marketplace
  adapter; the Flask HTML/API path is provider-gated.
- Firebase identity and Flask identity remain separate capabilities.
- Flask AI and Express AI remain separate capabilities and safety boundaries.

## Additive remediation plan

No remediation was implemented in this phase. Recommended next steps preserve
all existing paths:

1. Add contract-level React adapters only for profile, seller, admin, support,
   product reviews, and online-payment status after API contracts and
   authorization tests are approved.
2. Add browser/staging tests for credentialed CORS, session cookies, CSRF
   refresh, API response envelopes, and local-to-server reconciliation.
3. Add a provider-safe online-payment browser journey using sandbox callbacks,
   replay/idempotency tests, and explicit human approval.
4. Add Android integration tests against a disposable/staging Flask server.
5. Define worker/scheduler deployment and outbox/Telegram/restore runbooks
   before claiming external integrations are live.
6. Keep local fallback, Firebase, Flask/Jinja, Express, and Android paths until
   an evidence-based consolidation decision is approved.

## Local verification results

The following checks were run for this phase. The named feature test modules
were included in the complete Python suite; they were not separately rerun
with real external providers.

| Command | Result |
|---|---|
| `python scripts/validate_repository_structure.py --fail-on-review` | **PASS** — `repository_structure=PASS`; 190 registry paths checked; no source deletions/renames; no missing imports/config |
| `python -c "import json; d=json.load(open('docs\\architecture\\FEATURE_REGISTRY.json', encoding='utf-8')); ids=[f['id'] for f in d['features']]; assert len(ids)==22 and len(ids)==len(set(ids)); print('FEATURE_REGISTRY JSON PASS; entries=22; unique IDs PASS')"` | **PASS** |
| `npm run lint` | **PASS** — `tsc --noEmit`, exit code 0 |
| `npm run build` | **PASS with warning** — Vite production build succeeded; existing >500 kB chunks warning |
| `python -m pytest -q` | **PASS** — `305 passed in 745.89s`; Python emitted an environment `.pth` warning for a missing sibling `D:\FTP\Telegram-Bot\src` path |
| `.\android\gradlew.bat -p android :app:test --no-daemon --project-cache-dir $cache` where `$cache` is `%TEMP%\NexHaatPhase26GradleProjectCache` | **PASS with warnings** — `BUILD SUCCESSFUL in 10m 15s`; unsigned release configuration, SDK XML version mismatch, deprecated Android APIs/Gradle features |
| `git diff --check` | **PASS** |

These are local code/test results, not proof of production or staging
connectivity. Android device/emulator execution, live providers, and hosted
GitHub checks were not run.

## Phase 26 conclusion

| Area | Result |
|---|---|
| 21 requested journey traces | **PARTIAL** — source evidence recorded; several paths remain only partially connected |
| Local Flask/React/Express/Android tests | **PASS** — available local suites succeeded |
| Live Azure public GET checks | **BLOCKED / NOT VERIFIED** — all tested paths timed out |
| OTP, payment, external provider, webhook, upload, restore, and worker execution | **NOT TESTED / BLOCKED** |
| Feature deletion or disabling | **NO** |
| Large architectural remediation | **NOT DONE** |
