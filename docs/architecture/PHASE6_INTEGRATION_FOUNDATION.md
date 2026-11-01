# Phase 6 — Zero-Loss Integration Foundation

**Date:** 2026-10-31  
**Scope:** Read-only architecture, API-contract, authentication, and rollout
design. No application source, dependency manifest, database schema, migration,
production setting, or deployment target was changed for this phase.

## Status summary

| Area | Status | Evidence / boundary |
| --- | --- | --- |
| Current Flask architecture and `/api/v1` registration | **PASS** | [`app/__init__.py`](../../app/__init__.py), [`app/api/__init__.py`](../../app/api/__init__.py) |
| React/Vite marketplace inventory | **PASS** | [`src/App.tsx`](../../src/App.tsx), [`src/context/AppContext.tsx`](../../src/context/AppContext.tsx), Phase 5 report |
| Copilot-preferred OTP lifecycle | **PASS** | [`app/api/routes/auth.py`](../../app/api/routes/auth.py), [`app/routes/auth.py`](../../app/routes/auth.py), OTP templates/services/tests |
| Flask as marketplace authority | **PASS** | Server-side catalog, cart, checkout, order, payment, seller, admin, and role checks |
| React connected to Flask marketplace APIs | **FAIL** | React currently consumes mock data and Firebase Auth; no verified Flask API client exists |
| Secure Firebase-to-Flask identity bridge | **BLOCKED** | No verified token exchange, account-linking policy, or migration approval |
| Android API contract preservation | **PASS** | Retrofit `/api/v1` client, cookie jar, CSRF interceptor, and DTOs are present |
| React-to-Flask live integration | **NOT TESTED** | Requires approved staging origin, CORS/CSRF policy, and disposable data |
| Real email/SMS/payment/provider behavior | **NOT TESTED** | Must use approved test providers; production side effects are out of scope |
| Any source/dependency/schema/production change | **NEEDS APPROVAL** | This phase intentionally created only this report |

## 1. Verified current architecture

### Flask marketplace and identity authority

The Flask application factory registers server-rendered blueprints and a
versioned, frontend-independent JSON API at `/api/v1`. The API reuses the same
SQLAlchemy models and services as the server-rendered marketplace; it is not a
mock or second database. The relevant registration points are
[`app/__init__.py`](../../app/__init__.py) and
[`app/api/__init__.py`](../../app/api/__init__.py).

Flask owns:

- user identity, server-side session, roles, active-account checks, and audit;
- customer/seller/admin/rider authorization;
- categories, products, variants, stock, catalog moderation, and search;
- session-backed customer cart and multi-seller checkout;
- COD and SSLCOMMERZ payment states, retries, and order records;
- orders, returns, wishlist, notifications, reviews, banners, and seller/admin
  operations;
- the existing registration, admin-login, password-reset, and phone OTP
  workflows.

All JSON responses use a stable envelope from
[`app/api/responses.py`](../../app/api/responses.py):

```json
{"success": true, "data": {}, "message": "Success"}
```

Paginated collections add `pagination: { "page", "limit", "total" }`.
Controlled failures use:

```json
{"success": false, "error": {"code": "VALIDATION_ERROR", "message": "..."}}
```

The API error handlers are defined in
[`app/api/errors.py`](../../app/api/errors.py), including an explicit
`CSRF_ERROR` response.

### React/Vite and Firebase surface

The preferred AI Studio marketplace UI is the React/Vite application under
[`src/`](../../src/). [`src/App.tsx`](../../src/App.tsx) selects the existing
marketplace views and shared components. The primary state boundary is
[`src/context/AppContext.tsx`](../../src/context/AppContext.tsx), which
currently contains local/mock catalog, cart, order, review, promotion,
notification, role, and Prime state.

[`src/lib/firebase.ts`](../../src/lib/firebase.ts) initializes Firebase Auth
and Firestore. `AppContext` uses Google popup authentication and writes a
Firestore `users/{uid}` document. This is an existing capability and must
remain available until an approved additive bridge or retention decision is
implemented. It is not currently proven to establish a Flask session.

### Express/Node auxiliary service

[`server.ts`](../../server.ts) is an Express service for Gemini chat, search and
maps grounding, transcription, image/video/music generation, PubChem/product
analysis, and a Gemini Live WebSocket. It is complementary to Flask and must
not become the source of truth for products, prices, stock, orders, payments,
roles, or OTP. Its current `app.use(cors())` is broad and requires a separately
approved production-origin policy before cross-origin deployment.

### Android client

The Android client uses Retrofit through
[`android/app/src/main/java/com/nexhaat/app/data/remote/ApiService.kt`](../../android/app/src/main/java/com/nexhaat/app/data/remote/ApiService.kt).
`BuildConfig.BASE_URL` is the base origin. The client persists cookies and adds
`X-CSRFToken` to state-changing requests through
[`android/app/src/main/java/com/nexhaat/app/data/remote/interceptor/CsrfInterceptor.kt`](../../android/app/src/main/java/com/nexhaat/app/data/remote/interceptor/CsrfInterceptor.kt).
Its generic DTO in
[`android/app/src/main/java/com/nexhaat/app/data/remote/dto/ApiResponse.kt`](../../android/app/src/main/java/com/nexhaat/app/data/remote/dto/ApiResponse.kt)
matches the Flask success, pagination, and error envelopes.

## 2. Target additive architecture

The zero-loss target keeps the existing boundaries:

```text
React/Vite AI Studio UI ── HTTPS session + CSRF ──> Flask marketplace/API
       │                                             │
       ├── HTTPS/WebSocket ──> Express AI service   ├── SQLAlchemy/database
       │                                             ├── mail/SMS/payment adapters
       │                                             └── existing server-rendered routes
       │
Android ── HTTPS cookies + CSRF ────────────────────> Flask /api/v1
```

- **React/Vite:** preferred customer-facing visual/UI layer; preserve all
  current pages, animations, local fallback behavior, and AI components while
  adding a typed Flask adapter incrementally.
- **Flask:** authoritative identity, authorization, catalog, pricing, stock,
  cart, checkout, order, payment, OTP, and marketplace data boundary.
- **Express:** existing AI/science/WebSocket capabilities only; keep provider
  keys server-side and do not duplicate marketplace business rules.
- **Android:** continue the existing cookie/CSRF `/api/v1` contract. Any
  contract extension must be additive and regression-tested.
- **Database/migrations:** no migration is required for the foundation. Any
  later schema change must use an additive Alembic migration and a disposable
  database verification gate.

The React UI must not switch to production data until server-authoritative
prices, inventory, order state, and authorization are verified in staging.
Mock/Firebase behavior remains preserved behind an explicit integration
boundary rather than being silently deleted.

## 3. Copilot OTP integration contract

The existing Flask OTP implementation remains canonical. The React client
must call these Flask endpoints through the same session and CSRF model; it
must not implement a competing browser OTP provider or expose code secrets.

### Registration

| Operation | Method and endpoint | Request | Response / behavior |
| --- | --- | --- | --- |
| Start registration | `POST /api/v1/auth/register` | JSON: `role` (`customer`/`seller`), `email`, `full_name`, `phone`, `password`; seller additionally `store_name`, optional `business_address` | `202`, `data: {email, expires_at}` and `message`; creates a server-side challenge and session-bound challenge id |
| Verify registration | `POST /api/v1/auth/register/verify` | JSON: `{code: "123456"}` | `201`, `data` is the authoritative `user`; invalid/expired/locked codes return controlled `400/429` errors |
| Browser OTP UI | Existing templates/static assets | No replacement | Preserve [`app/templates/auth/verify_registration.html`](../../app/templates/auth/verify_registration.html), [`app/static/js/otp-verification.js`](../../app/static/js/otp-verification.js), and [`app/static/css/otp-verification.css`](../../app/static/css/otp-verification.css) |

Verified controls are a six-digit code, ten-minute expiry, sixty-second resend
cooldown, and five failed attempts. The server stores a digest, not a raw code.
The existing server-rendered resend route remains available; the versioned API
does not invent a separate resend schema.

### Admin login

| Operation | Method and endpoint | Request | Response / behavior |
| --- | --- | --- | --- |
| Request admin code | `POST /api/v1/auth/admin/code` | JSON: `{email}` | `202` with non-enumerating success message for normal requests; rate limits and denies non-admin accounts |
| Verify admin code | `POST /api/v1/auth/admin/verify` | JSON: `{code: "123456"}` | `200`, authoritative admin `user`; invalid/expired code returns `400`, throttling returns `429` |

The admin challenge is session-bound, expires after the existing configured
TTL, and is consumed on success. The preferred admin OTP template and
server-rendered routes remain unchanged.

### Other existing OTP flows

Password reset and phone verification are implemented in the server-rendered
auth flow and services, including expiry, attempt/rate controls, hashed codes,
and provider adapters. Their exact browser form contracts should be reused in
a later API-adapter phase only after a dedicated contract test confirms the
request/response shape. **Status: BLOCKED for React wiring; NOT TESTED as a
live provider flow.**

## 4. Authentication, session, CSRF, and origin design

### Existing behavior to preserve

- Flask `nexhaat_session` is an HttpOnly, `SameSite=Lax` server-side session
  cookie with a configured twelve-hour lifetime; production secure-cookie
  behavior is controlled by configuration.
- `GET /api/v1/auth/csrf` returns `{success:true,data:{csrf_token}}`.
- State-changing API calls must send the returned value in `X-CSRFToken`.
- `GET /api/v1/auth/me` is the session-authoritative identity check.
- `POST /api/v1/auth/login` accepts `{email,password}` and establishes the
  Flask session for active customer, seller, or rider accounts.
- `POST /api/v1/auth/logout` clears the Flask login and session.
- Admin access requires the separate OTP step and server-side `role == admin`.
- React `currentRole` and Firebase claims are never authorization evidence.

### Proposed bridge

1. Deploy React and Flask on explicitly approved HTTPS origins.
2. The React API client uses `credentials: "include"` for Flask requests.
3. On boot, obtain a CSRF token, then call `/auth/me`; do not infer identity
   from Firebase or local state.
4. Use the existing Flask login and OTP endpoints for marketplace sign-in.
5. Refresh the CSRF token on a CSRF failure through the normal error path; do
   not disable CSRF or place session secrets in localStorage.
6. Configure a narrow allowed-origin policy and verify cookie behavior in
   staging. If the deployment is cross-site, cookie `SameSite`, CORS
   credentials, TLS, and CSRF origin checks must be validated together.
7. Keep Firebase Google Auth/Firestore as an explicitly isolated existing
   feature until the owner approves one of: (a) retention as a separate
   non-marketplace identity, or (b) a reviewed server-side account-linking
   flow. No silent migration or automatic account merge is permitted.

The current Flask security headers set `connect-src 'self'`; a separate
cross-origin React deployment therefore requires a reviewed CSP/origin change
before live use. That change is **NEEDS APPROVAL** and is not included here.

## 5. Verified React-to-Flask API mapping

All paths below are absolute from the Flask origin and use the envelope above.
Protected state-changing operations require a Flask session and CSRF header
unless the endpoint is an external provider callback explicitly exempted by the
existing implementation.

| React capability | Flask API contract | Auth/role | Current React state |
| --- | --- | --- | --- |
| Auth/session | `GET /api/v1/auth/csrf`, `POST /auth/register`, `POST /auth/register/verify`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, admin code/verify | Session; admin endpoint requires admin OTP | Firebase/mock; **FAIL** |
| Categories/products/search | `GET /api/v1/categories`, `/categories/{slug}`, `/products`, `/products/{id}`, `/products/{id}/recommendations`, `/search`, `/deals`, `/stores/{slug}` | Public reads; approved/active catalog filtering is server-side | Mock data; **NOT WIRED** |
| Product query parameters | `/products`: `page`, `limit` (1–100), `q`, `category_id`, `min_price`, `max_price`, `sort` (`featured`, `relevance`, `newest`, `price_asc`, `price_desc`), `seller_id`, `in_stock`, `variant_value`, `brand_name`, `min_rating`, `discount` | Public reads; validated server-side | Mock filters; **NOT WIRED** |
| Reviews | `GET /products/{id}/reviews`; `POST /products/{id}/reviews`; helpful/report POST routes | Customer session for write/vote/report; moderation and purchase rules server-side | Local reviews; **NOT WIRED** |
| Banners | `GET /api/v1/banners?page=&limit=` | Public read | Existing UI capability; API adapter pending |
| Cart | `GET /cart`; `POST /cart/items` with `{product_id,variant_id?,quantity}`; `PATCH/DELETE /cart/items/{cart_key}`; `DELETE /cart` | Customer session; CSRF for mutations | Local cart; **NOT WIRED** |
| Checkout | `POST /checkout/preview` with optional `{promotion_code}`; `POST /checkout` with customer contact/address, `payment_method`, optional promotion | Customer session; server recalculates price/stock/discount | Local order creation; **NOT WIRED** |
| Payment | `GET /payments/{checkout_group}`; `POST /payments/{checkout_group}/retry` | Owning customer session | Local order state; **NOT WIRED** |
| Orders/returns | `GET /orders`, `GET /orders/{order_number}`, `POST /orders/{order_number}/cancel`, `POST /orders/{order_number}/return` | Owning customer session | Local orders; **NOT WIRED** |
| Wishlist | `GET /wishlist`, `POST /wishlist/items` with `{product_id}`, `DELETE /wishlist/items/{product_id}` | Customer session; CSRF for mutations | Local wishlist; **NOT WIRED** |
| Notifications | `GET /notifications`, `POST /notifications/read-all`, `POST /notifications/{id}/read` | Signed-in user; CSRF for mutations | Local notifications; **NOT WIRED** |
| Seller | `GET /seller/orders`, `/seller/dashboard`, `/seller/products`; seller product POST/PATCH/DELETE; seller order PATCH | Approved seller; server ownership checks | React seller UI is local/mock; **NOT WIRED** |
| Admin | `/admin/dashboard`, `/users`, `/sellers`, `/categories`, `/products`, `/orders`, `/reviews`, `/payments`, and approved mutation endpoints | Admin session plus CSRF | React admin UI is local/mock; **NOT WIRED** |
| Rider and support | Existing server-rendered rider/support routes; no equivalent complete versioned React contract was verified | Role-specific server checks | React rider/support presentation exists; **BLOCKED** for API mapping |
| AI assistant | Express `/api/gemini/*`, `/api/science/*`, WebSocket; Flask `/ai/*` also exists | Provider/service-specific; must not authorize commerce mutation | React drawer exists; route selection requires approval |

The exact commerce response shapes are defined by
[`app/api/routes/commerce.py`](../../app/api/routes/commerce.py) and
[`app/api/serializers.py`](../../app/api/serializers.py). Money is serialized
as fixed-precision strings. The React adapter must preserve this rather than
converting client-provided numeric totals into authoritative values.

## 6. Firebase and Express conflict analysis

| Conflict | Finding | Safe decision |
| --- | --- | --- |
| Firebase identity vs Flask identity | Firebase popup user and Firestore document do not establish Flask `user_id`, role, or session | Do not merge silently; retain existing Firebase feature until approved bridge |
| React role state vs authorization | `currentRole` is client state | Never use it for protected actions; Flask role checks remain authoritative |
| React mock data vs database | Products, cart, orders, promotions, reviews, and notifications are local/mock in `AppContext` | Add an adapter and feature-flagged migration path; do not delete fallback behavior prematurely |
| Express CORS | `app.use(cors())` allows broad origins | Narrow origins/credentials only through a separately approved deployment change |
| Express AI vs commerce | Express has AI/science routes, not verified marketplace ownership rules | Keep AI auxiliary; Flask remains commerce authority |
| Provider output trust | Gemini output is untrusted and may contain arbitrary text | Validate output, bound requests, and never let it directly mutate price, stock, role, payment, or orders |

## 7. Android compatibility matrix

| Surface | Existing contract | Compatibility result |
| --- | --- | --- |
| Base origin | `BuildConfig.BASE_URL` | **PASS**; environment-specific value must point to Flask |
| Envelope | `ApiResponse<T>` with `success`, `data`, `message`, `pagination`, `error` | **PASS** |
| Session | Persistent cookie jar | **PASS** in source; live expiry/logout verification **NOT TESTED** |
| CSRF | `GET /api/v1/auth/csrf`, then `X-CSRFToken` for POST/PATCH/DELETE | **PASS** in source; staging network test **NOT TESTED** |
| Auth | Login, logout, current user | **PASS** contract |
| Catalog | Categories, products, search, product detail, banners | **PASS** contract; pagination/empty/error UI **NOT TESTED** |
| Cart | Get/add/update/remove | **PASS** contract; authenticated disposable-server test **NOT TESTED** |
| OTP | No complete Android registration/admin/password-reset OTP surface was verified in `ApiService.kt` | **BLOCKED**; requires explicit Android scope and contract work |
| Payment/orders/seller/admin/rider | No complete Retrofit surface was verified for all workflows | **BLOCKED** for expansion; do not break existing server API |

## 8. Security and reliability considerations

1. Keep session cookies HttpOnly and secure in production; never store session
   secrets or OTP values in localStorage, Firestore, logs, or analytics.
2. Use a single approved HTTPS origin policy. Do not combine wildcard CORS with
   credentialed cookies.
3. Keep CSRF enabled for browser/API session mutations. Preserve webhook
   exemptions only for their verified signature-protected provider callbacks.
4. Treat every product price, discount, stock quantity, payment status, role,
   seller id, and order transition as server-authoritative.
5. Preserve OTP hashing, expiry, cooldown, attempt limits, session binding,
   non-enumerating responses, and provider adapters.
6. Add request IDs, bounded timeouts, rate limits, and safe error handling to
   any new React/Express client path without leaking provider or database
   details.
7. Validate Gemini and retrieved content as untrusted input. Keep AI optional
   so browse/cart/checkout remain usable when Express or a model is unavailable.
8. Use staging/disposable data for contract, concurrency, duplicate webhook,
   payment, and Android tests. Never use production credentials or customer
   records.

## 9. Exact future implementation file list

No file in this list was changed in Phase 6.

### First implementation slice: authentication bridge

- New React API client near [`src/lib/`](../../src/lib/) (exact filename to be
  approved).
- [`src/context/AppContext.tsx`](../../src/context/AppContext.tsx) — additive
  Flask-session state, preserving Firebase/mock state until cutover approval.
- Auth/OTP UI integration points in [`src/components/`](../../src/components/)
  or [`src/pages/`](../../src/pages/), without replacing the existing Flask OTP
  assets.
- Flask CORS/CSP/configuration only after an approved staging origin is known.
- New contract tests under [`tests/`](../../tests/) and React tests in the
  repository's approved test location.

### Subsequent slices

- Product/catalog adapter and page integration.
- Cart/wishlist adapter.
- Checkout/payment/order adapter.
- Customer account, notifications, and reviews.
- Seller/admin/rider adapters, only where matching Flask contracts exist.
- Express AI client policy and origin configuration.
- Android OTP/API extensions only after a written compatibility contract.

No dependency, migration, production setting, or existing route should be
changed merely to make the React UI appear connected.

## 10. Phased execution roadmap, tests, and rollback

### A — Authentication and OTP bridge

- **Change:** additive typed client for CSRF, login, `/me`, logout, registration,
  and existing OTP endpoints.
- **Risk:** cookie/CORS/CSRF mismatch; accidental Firebase account merge.
- **Tests:** API envelope, CSRF rejection, session establishment/expiry, wrong/
  expired/locked OTP, resend cooldown, duplicate requests, role boundaries.
- **Rollback:** feature-flag the client path off; preserve the current React
  Firebase/mock path and all Flask routes.

### B — Catalog and product discovery

- **Change:** map React catalog/product pages to public Flask reads while
  retaining mock fallback until parity is proven.
- **Risk:** response-field/media/pagination mismatch.
- **Tests:** filters, sort, empty/error/loading states, media URLs, localized
  fields, cache isolation.
- **Rollback:** disable the API-read flag; no schema or route removal.

### C — Cart, wishlist, checkout, and orders

- **Change:** route authenticated mutations to Flask and display fixed-precision
  server totals.
- **Risk:** duplicate submits, stale stock, cross-seller allocation, payment
  state confusion.
- **Tests:** concurrency/idempotency, stock rejection, promotion allocation,
  COD, payment retry/expiry, cancel/return authorization.
- **Rollback:** disable each workflow flag while preserving server records and
  existing UI.

### D — Customer, seller, admin, and rider surfaces

- **Change:** integrate only verified endpoint groups with role-gated views.
- **Risk:** client role leakage or seller cross-tenant access.
- **Tests:** every role matrix, ownership checks, audit events, unauthorized
  responses, responsive/accessibility regression.
- **Rollback:** retain existing server-rendered route and React presentation.

### E — Express AI and Android compatibility

- **Change:** narrow Express origin policy and add optional typed AI client;
  extend Android only from verified contracts.
- **Risk:** provider outage, broad CORS, mobile breaking change.
- **Tests:** provider timeout/fallback, payload limits, API backward-compatibility,
  Android debug tests against disposable Flask.
- **Rollback:** disable optional AI integration; keep existing `/api/v1` and
  Android client behavior unchanged.

### F — Staging release gate

- **Required:** `npm ci`, React build/lint, Flask full suite, migration test
  against disposable SQLite/PostgreSQL-compatible environment, browser
  contract tests, Android debug tests, security/CORS/CSRF checks, and payment/
  provider mocks.
- **Promotion:** only an identified artifact, after owner approval, with the
  prior artifact and configuration retained for rollback.
- **Production:** no restart, redeploy, configuration, database, or provider
  change is authorized by this report.

## 11. Blockers and decisions requiring approval

1. **NEEDS APPROVAL:** choose whether Firebase Google Auth remains a separate
   optional identity or whether a reviewed server-side account-linking flow is
   desired. No automatic migration is safe from current evidence.
2. **NEEDS APPROVAL:** approve the Flask-session React bridge and its staging
   origins, cookie policy, CORS policy, and CSP changes.
3. **NEEDS APPROVAL:** approve feature-flagged replacement of React mock reads
   with Flask reads while preserving fallback and current UI.
4. **NEEDS APPROVAL:** decide whether React should call Flask AI routes,
   Express AI routes, or both by capability; do not duplicate provider logic.
5. **NEEDS APPROVAL:** define Android OTP scope and whether Android should
   receive additive registration/password-reset/phone-verification endpoints.
6. **BLOCKED:** Azure App Service runtime, Kudu/Log Stream, startup command,
   and live staging behavior remain unverified without authorized Azure access.
7. **NOT TESTED:** real email/SMS delivery, live Firebase, SSLCOMMERZ, payment
   callbacks, production database, and Android live service.

## 12. Phase 6 completion boundary

**PASS:** current architecture, responsibilities, OTP contract, session/CSRF
design, API mapping, conflict analysis, Android matrix, implementation files,
roadmap, tests, and rollback strategy are documented from source evidence.

**NOT IMPLEMENTED:** no React-to-Flask bridge, Firebase migration, API rewrite,
dependency change, schema/migration change, production configuration, restart,
redeploy, commit, or push was performed.

The next step requires explicit approval of the authentication/session bridge,
staging origins, Firebase decision, Android scope, and test environment before
any application source is edited.
