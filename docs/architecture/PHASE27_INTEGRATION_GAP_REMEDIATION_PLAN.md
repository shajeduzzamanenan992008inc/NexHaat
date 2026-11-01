# Phase 27 - Integration Gap Remediation Plan

**Status:** PLAN ONLY - no remediation implemented
**Basis:** `PHASE26_FEATURE_CONNECTIVITY_AUDIT.md`, the existing 22-entry
`FEATURE_REGISTRY.json`, Phase 23-25 reports, repository guidance, and source
contracts inspected for this phase.

## Scope and guardrails

This plan follows the exact 21 journeys and Phase 26 classifications. Paths
and endpoints below describe existing contracts only. An absent React adapter
is not treated as an absent Flask capability. No endpoint is proposed as
already existing unless Phase 26 or the inspected source established it.
Where a future API contract is needed, it must be designed and reviewed before
implementation.

No source, route, feature, workflow, schema, registry entry, or user change was
deleted, disabled, merged, or modified. Intentional Flask/Jinja, React/local,
Firebase, Flask AI, Express AI, and Android overlaps remain intact. Priority
does not assert that a vulnerability exists: P0 items are validation gates
for security-sensitive flows.

## Exact Phase 26 journey status baseline

| # | Journey | Existing feature ID(s) | Phase 26 status | Planning reference |
|---:|---|---|---|---|
| 1 | Guest browsing | `NEX-CUSTOMER-MARKETPLACE`, `NEX-CATALOG-SEARCH` | PARTIALLY_CONNECTED | G1 |
| 2 | Customer registration and existing OTP verification | `NEX-AUTH-OTP` | CONNECTED_BUT_NOT_LIVE_VERIFIED | G0 |
| 3 | Customer login/logout/session handling | `NEX-AUTH-OTP` | CONNECTED_BUT_NOT_LIVE_VERIFIED | G0 |
| 4 | Product search, filtering, category navigation | `NEX-CATALOG-SEARCH` | CONNECTED_BUT_NOT_LIVE_VERIFIED | G1 |
| 5 | Product details and reviews | `NEX-PRODUCT-DETAILS-REVIEWS` | PARTIALLY_CONNECTED | G1 |
| 6 | Cart and wishlist | `NEX-CART-WISHLIST`, `NEX-CATALOG-CART` | CONNECTED_BUT_NOT_LIVE_VERIFIED | G0 |
| 7 | Checkout and COD | `NEX-CHECKOUT-PAYMENTS`, `NEX-CHECKOUT-ORDERS` | CONNECTED_BUT_NOT_LIVE_VERIFIED | G0 |
| 8 | Online payment integration status | `NEX-CHECKOUT-PAYMENTS` | BLOCKED_BY_CONFIGURATION | G3 |
| 9 | Customer order history | `NEX-ORDERS-RETURNS`, `NEX-CHECKOUT-ORDERS` | CONNECTED_BUT_NOT_LIVE_VERIFIED | G0 |
| 10 | Order cancellation and return | `NEX-ORDERS-RETURNS` | CONNECTED_BUT_NOT_LIVE_VERIFIED | G0 |
| 11 | Customer profile | `NEX-CUSTOMER-PROFILE` | BACKEND_ONLY | G2 |
| 12 | Seller registration and dashboard | `NEX-SELLER-PORTAL` | PARTIALLY_CONNECTED | G4 |
| 13 | Seller product management | `NEX-SELLER-PORTAL` | BACKEND_ONLY | G4 |
| 14 | Admin dashboard and management | `NEX-ADMIN-PORTAL` | BACKEND_ONLY | G5 |
| 15 | Notifications and support | `NEX-NOTIFICATIONS-SUPPORT` | PARTIALLY_CONNECTED | G6 |
| 16 | Flask AI features | `NEX-FLASK-AI`, `NEX-AI-ASSISTANTS` | CONNECTED_BUT_NOT_LIVE_VERIFIED | G9 |
| 17 | Express/Node AI features | `NEX-EXPRESS-AI`, `NEX-AI-ASSISTANTS` | CONNECTED_BUT_NOT_LIVE_VERIFIED | G9 |
| 18 | Android API compatibility | `NEX-ANDROID-CLIENT`, `NEX-ANDROID-API` | CONNECTED_BUT_NOT_LIVE_VERIFIED | G10 |
| 19 | Uploads and asset handling | `NEX-SECURITY-UPLOADS` | PARTIALLY_CONNECTED | G7 |
| 20 | Privacy, security, and account-data isolation | `NEX-AUTH-OTP`, `NEX-SECURITY-UPLOADS`, `NEX-FLASK-API-SERVICES` | CONNECTED_BUT_NOT_LIVE_VERIFIED | G0 |
| 21 | Background jobs and external integrations | `NEX-INTEGRATIONS-BACKGROUND`, `NEX-BACKUP-DR` | BLOCKED_BY_CONFIGURATION | G8 |

Phase 26 local checks are historical evidence, not tests rerun by this plan:
its report records the full Python suite (305 passed), frontend lint/build,
Android `:app:test`, strict structure validation, registry uniqueness, and
`git diff --check` as passing. It does not record an authenticated staging
browser run, live provider transaction, device run, or restore rehearsal.

## Prioritized gaps and additive remediation

### G0 - P0: prove auth, CSRF, tenant isolation, and server authority at integration boundaries

1. **Journey and ID:** Journeys 2, 3, 6, 7, 9, 10, 11-14, 18, and 20;
   `NEX-AUTH-OTP`, `NEX-CART-WISHLIST`, `NEX-CHECKOUT-PAYMENTS`,
   `NEX-ORDERS-RETURNS`, `NEX-CUSTOMER-PROFILE`, `NEX-SELLER-PORTAL`,
   `NEX-ADMIN-PORTAL`, `NEX-ANDROID-CLIENT`, `NEX-SECURITY-UPLOADS`,
   `NEX-FLASK-API-SERVICES`.
2. **Current status:** Phase 26 statuses are listed above; no cross-tenant
   vulnerability was confirmed by that audit.
3. **Frontend:** `src/lib/flaskAuth.ts`, `src/lib/marketplaceApi.ts`,
   `src/context/AppContext.tsx`; Android `ApiService.kt`, `NetworkModule.kt`,
   `CsrfInterceptor.kt`, and `PersistentCookieJar.kt`.
4. **Client/endpoints:** Existing auth adapter calls `/api/v1/auth/csrf`,
   `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/logout`,
   `/api/v1/auth/me`. Marketplace mutation adapters use credentialed requests
   and `X-CSRFToken`; see the existing calls in `marketplaceApi.ts`.
5. **Backend/model:** `app/api/routes/auth.py`, `commerce.py`, `wishlist.py`,
   `admin.py`; `app/security.py`; shared services and `app/models/`.
   Existing commerce routes scope customer orders and seller products by the
   authenticated user; `_admin()` requires an Admin session.
6. **Authentication/session/CSRF:** Flask session cookie and Flask-WTF CSRF
   are the authority. All state-changing browser/mobile requests must use the
   existing CSRF contract; authorization must remain server-side.
7. **Exact gap:** Local unit/integration evidence does not establish deployed
   cross-origin cookie, SameSite, CORS/preflight, CSRF refresh, or denied
   cross-customer/cross-seller behavior for every connected client path.
8. **Evidence/tests:** Phase 26 rows 2, 3, 6, 7, 9, 10, 18, 20;
   `tests/test_auth.py`, `tests/test_accounts.py`, `tests/test_orders.py`,
   `tests/test_returns.py`, `tests/test_wishlist.py`,
   `tests/test_security_ops.py`. These cover local behavior; not all are
   client-to-live-server tests.
9. **User impact:** A failed boundary can prevent sign-in or expose/misapply
   account-specific data; this is a risk statement, not a confirmed defect.
10. **Security/privacy risk:** Cross-account IDOR, CSRF rejection, stale
    session, client-supplied role/price/payment state, or accidental use of
    guest/local fallback as an authoritative result.
11. **Additive remediation:** Add focused denied-owner and role-negative
    contract tests for the existing API; add browser and Android contract
    tests against an isolated staging API. Preserve all fallback and auth
    surfaces. Do not add a competing identity/OTP implementation.
12. **Dependencies:** Approved staging URL/origins, disposable customer and
    seller accounts, synthetic data, owner-approved credentialed CORS and
    cookie policy, and a resettable staging database.
13. **Safe local tests:** Extend existing Flask test-client cases with
    synthetic users and cross-owner IDs; test missing/invalid CSRF and role
    denials. No live credentials or records.
14. **Staging-only verification:** Browser cookie persistence, CSRF token
    refresh, login/logout/session expiry, customer and seller ownership,
    admin denial, Android session behavior, and no leakage across roles.
15. **Rollback:** Tests are additive and can be reverted independently.
    Any adapter behavior change must be behind a reviewed flag or retained
    compatibility path until staging acceptance.

### G1 - P1: complete React catalog detail and review data path

1. **Journey and ID:** Journeys 1, 4, and 5; `NEX-CUSTOMER-MARKETPLACE`,
   `NEX-CATALOG-SEARCH`, `NEX-PRODUCT-DETAILS-REVIEWS`, and preserved
   `NEX-CATALOG-CART`.
2. **Current status:** Partially connected / connected but not live verified /
   partially connected, respectively, per Phase 26.
3. **Frontend:** `src/pages/CatalogPage.tsx`, `src/pages/ProductDetailPage.tsx`,
   `src/context/AppContext.tsx`.
4. **Client/endpoints:** `src/lib/marketplaceApi.ts` fetches catalog through
   `GET /api/v1/categories` and `GET /api/v1/products`; Phase 26 did not find
   a React detail/review adapter. Existing Flask detail/review routes are
   described in Phase 26; do not infer client use from endpoint existence.
5. **Backend/model:** `app/api/routes/catalog.py`,
   `app/services/catalog.py`, `app/services/reviews.py`; Product, Category,
   Review, ReviewVote, and ReviewReport models.
6. **Authentication/session/CSRF:** Catalog reads are public. Review
   submission/helpful/report operations require the existing Flask role,
   ownership/purchase rules and CSRF on mutations.
7. **Exact gap:** React detail/review state is not shown to hydrate from the
   detail/review API. The catalog mapping also defaults review count/rating
   locally; Phase 26 did not establish authoritative review summary hydration.
8. **Evidence/tests:** Phase 26 journeys 1, 4, 5; `tests/test_catalog.py`,
   `tests/test_catalog_phase3.py`, `tests/test_discovery.py`,
   `tests/test_reviews.py`, `tests/test_review_trust.py`.
9. **User impact:** Detail freshness, variant/review availability, or review
   eligibility feedback can differ between preview state and Flask data.
10. **Security/privacy risk:** Do not allow local state to represent an
    eligible/published review or override the server's purchase verification.
11. **Additive remediation:** Add typed detail/review response mapping to
    the existing marketplace adapter only after matching the Flask response
    envelope; retain the current page/design and fallback behavior. Keep
    review writes server-authoritative.
12. **Dependencies:** Confirm serializer shape, locale behavior, error
    envelopes, pagination, and API route contracts before adapter work.
13. **Safe local tests:** Flask tests for public detail, unavailable product,
    verified-purchase restriction, duplicate review, and denial cases; add
    adapter mapping tests using fixtures without credentials.
14. **Staging-only verification:** Compare API detail/review state with the
    rendered React page using synthetic products and an eligible test order.
15. **Rollback:** Remove only the new adapter call/mapping/test behind a
    feature flag or compatibility branch; retain Flask endpoints and existing
    React views.

### G2 - P1: additive customer profile connection

1. **Journey and ID:** Journey 11; `NEX-CUSTOMER-PROFILE`.
2. **Current status:** BACKEND_ONLY.
3. **Frontend:** No verified React profile page or profile adapter was found
   in Phase 26; preserve existing navigation and Flask templates.
4. **Client/endpoint:** Existing server-rendered `/account` workflow is
   present; Phase 26 did not verify a customer-profile JSON endpoint or a
   React caller. Do not invent an endpoint.
5. **Backend/model:** Flask account/auth handlers, profile services,
   `User`, `CustomerProfile`, and `CustomerAddress`.
6. **Authentication/session/CSRF:** Customer session required; all profile
   writes must be CSRF-protected and scoped to the current account.
7. **Exact gap:** No verified React-to-API path for profile/address reads and
   writes.
8. **Evidence/tests:** Phase 26 journey 11; `tests/test_accounts.py` and
   `tests/test_auth.py` cover Flask account behavior, not a React profile
   round trip.
9. **User impact:** React customers may need the existing Flask account
   surface or may not find profile management in that client.
10. **Security/privacy risk:** Address and account data require strict
    current-user scoping and must not be stored in public/local fallback state.
11. **Additive remediation:** First define an API contract reusing profile
    services; then add a small adapter/view that preserves the current
    server-rendered flow and brand.
12. **Dependencies:** API contract review, ownership/negative tests, product
    decision on navigation and profile fields.
13. **Safe local tests:** Synthetic customer profile/address read, valid
    update, malformed input, missing session, and cross-user denial.
14. **Staging-only verification:** Browser save/read after login, session
    expiry, mobile/narrow viewport, and isolation between two synthetic users.
15. **Rollback:** Disable only the additive React entry/adapter; keep
    existing Flask account routes and data unchanged.

### G3 - P1: online payment handoff and sandbox verification

1. **Journey and ID:** Journey 8; `NEX-CHECKOUT-PAYMENTS` and preserved
   `NEX-CHECKOUT-ORDERS`.
2. **Current status:** BLOCKED_BY_CONFIGURATION for online payment.
3. **Frontend:** `src/pages/CheckoutPage.tsx` explicitly limits the current
   safe React bridge to COD and displays an approved-staging-configuration
   notice.
4. **Client/endpoint:** The React checkout adapter submits COD; it does not
   establish an online-payment continuation.
5. **Backend/model:** Flask payment routes in `app/routes/orders.py`,
   `app/api/routes/commerce.py`, and `app/services/sslcommerz.py`,
   `app/services/payments.py`; Payment, PaymentRefund, Order, and ledger
   models.
6. **Authentication/session/CSRF:** Customer session and CSRF for checkout;
   provider callbacks must use the existing server verification and
   idempotency rules, not browser success state.
7. **Exact gap:** React lacks a verified hosted-checkout redirect/return/
   status continuation; staging/provider configuration and sandbox callback
   behavior are unverified.
8. **Evidence/tests:** Phase 26 journey 8; `tests/test_payments.py`,
   `tests/test_returns.py`, `tests/test_orders.py`; tests are local and do
   not prove live gateway credentials or callbacks.
9. **User impact:** React users can use the current COD path, but online
   payment cannot be claimed available in that flow.
10. **Security/privacy risk:** Forged redirect success, duplicate/replayed
    callbacks, wrong amount/currency, or unsafe payment retries.
11. **Additive remediation:** Define a React continuation using existing
    Flask payment contracts only after serializer/callback contract review;
    retain COD and server-rendered payment support. Never expose provider
    secrets or trust client totals.
12. **Dependencies:** Approved disposable staging URL, provider sandbox
    credentials, callback allowlisting, idempotency/replay tests, human
    approval of any external provider configuration.
13. **Safe local tests:** Mock gateway create/validate/refund calls; test
    duplicate, malformed, amount-mismatch, timeout, replay, and state
    transition behavior without sending requests to the provider.
14. **Staging-only verification:** Sandbox checkout, verified callback/IPN,
    cancellation/refund reconciliation, and no production payment methods.
15. **Rollback:** Disable only the new online-payment UI entry; leave COD,
    existing Flask routes, payment records, and provider callbacks intact.

### G4 - P2: React seller onboarding, dashboard, and product management

1. **Journey and ID:** Journeys 12 and 13; `NEX-SELLER-PORTAL`.
2. **Current status:** PARTIALLY_CONNECTED for registration/dashboard;
   BACKEND_ONLY for verified product management.
3. **Frontend:** `src/pages/SellerPortalPage.tsx`; registration UI and
   `src/lib/flaskAuth.ts` registration adapter are separate existing paths.
4. **Client/endpoint:** Registration uses `POST /api/v1/auth/register` and
   the existing verification redirect. Seller dashboard/product API calls
   from the React page were not verified in Phase 26. Existing Flask API
   contracts include `/api/v1/seller/dashboard`, `/seller/products`,
   `/seller/orders`, and seller product/order mutation routes.
5. **Backend/model:** `app/api/routes/commerce.py`, Flask seller routes and
   registration/auth services; `SellerProfile`, `Product`, variants,
   translations, Category, and Order.
6. **Authentication/session/CSRF:** Seller registration challenge, then
   authenticated seller role; approved-seller policy gates catalog actions.
   Mutations require CSRF; ownership is enforced server side.
7. **Exact gap:** React dashboard and product management are not verified
   against seller APIs, and registration-to-approved-role dashboard handoff
   is not staging tested.
8. **Evidence/tests:** Phase 26 journeys 12-13; `tests/test_auth.py`,
   `tests/test_staff_accounts_and_product_form.py`, `tests/test_catalog.py`,
   `tests/test_catalog_media.py`.
9. **User impact:** Sellers may complete registration but use Flask
   server-rendered management rather than the React portal.
10. **Security/privacy risk:** Seller ownership/approval must remain
    authoritative; client role selection or product IDs cannot grant access.
11. **Additive remediation:** Add typed seller API adapters and incremental
    React panels to the existing portal after contract tests; keep the Flask
    pages and registration/OTP flow available.
12. **Dependencies:** G0 security tests, exact API DTOs, approval lifecycle
    and product moderation status contract.
13. **Safe local tests:** Non-approved seller denial, approved seller own
    product CRUD, other-seller denial, pending moderation, price/stock bounds,
    CSRF rejection.
14. **Staging-only verification:** Synthetic seller registration, no real
    email/SMS, manually approved disposable seller, product moderation
    lifecycle, cross-seller isolation.
15. **Rollback:** Hide only additive React management entry if needed; retain
    all existing seller routes, APIs, forms, and records.

### G5 - P2: React Admin management contracts and role-denial paths

1. **Journey and ID:** Journey 14; `NEX-ADMIN-PORTAL`.
2. **Current status:** BACKEND_ONLY for verified privileged management paths.
3. **Frontend:** `src/pages/AdminPortalPage.tsx`; Phase 26 did not verify
   privileged API wiring from this page.
4. **Client/endpoint:** Existing Flask routes include
   `/api/v1/admin/dashboard`, `/users`, `/sellers`, `/categories`,
   `/products`, `/orders`, `/reviews`, `/payments`, and `/refunds` subpaths.
   Do not assume the React portal calls them.
5. **Backend/model:** `app/api/routes/admin.py`, audit/mail/notification/
   order/payment services; User, SellerProfile, Category, Product, Order,
   Review, Payment, PaymentRefund.
6. **Authentication/session/CSRF:** `_admin()` requires authenticated
   `admin` role; mutations use session CSRF and audit records. Keep any
   super-admin/support role distinctions explicit.
7. **Exact gap:** React admin data and actions do not have a verified typed
   connection to these protected APIs.
8. **Evidence/tests:** Phase 26 journey 14; `tests/test_security_ops.py`,
   `tests/test_stage10_operations.py`, `tests/test_review_trust.py`.
9. **User impact:** Admin users may use Flask management screens; React
   visual presence alone does not demonstrate operational functionality.
10. **Security/privacy risk:** Privileged mutation exposure, role confusion,
    unaudited actions, or displaying customer data beyond least privilege.
11. **Additive remediation:** Connect one read-only Admin dashboard panel
    first, then separately approved audited mutations with typed adapter,
    explicit permission UX, and denial handling. Preserve Flask Admin routes.
12. **Dependencies:** G0 denial tests, API response schemas, role matrix,
    audit event review, human approval for each consequential action.
13. **Safe local tests:** Customer/seller/support role denied; admin allowed;
    audit event emitted; invalid/unauthorized object and CSRF failure paths.
14. **Staging-only verification:** Test with synthetic accounts and
    non-financial records; verify role boundaries and audit trail.
15. **Rollback:** Remove/disable only the additive React integration; leave
    server Admin routes, audit data, and existing portal behavior untouched.

### G6 - P2: React support connection; preserve existing notifications

1. **Journey and ID:** Journey 15; `NEX-NOTIFICATIONS-SUPPORT`.
2. **Current status:** PARTIALLY_CONNECTED.
3. **Frontend:** `src/pages/SupportPage.tsx`; existing React notifications
   view and AppContext notification state.
4. **Client/endpoint:** Phase 26 verified React notification requests to
   `/api/v1/notifications`; it did not verify a React support API adapter.
   Support is the existing server-rendered `/support` workflow.
5. **Backend/model:** `app/api/routes/notifications.py`,
   `app/routes/support.py`, notification/support services; Notification,
   SupportConversation, and SupportMessage.
6. **Authentication/session/CSRF:** Notifications require current-user
   scoping; support create/reply requires customer or staff role; mutations
   use Flask CSRF. Existing support case lookup scopes customer ownership.
7. **Exact gap:** React support form/replies are not established as connected
   to a JSON API. External email/Telegram notifications are not delivery
   verified.
8. **Evidence/tests:** Phase 26 journey 15; `tests/test_notifications.py`,
   `tests/test_stage10_operations.py`, and support cases in
   `tests/test_security_ops.py` where relevant.
9. **User impact:** Support from React may not create or display a durable
   support case; notification delivery may be in-app only.
10. **Security/privacy risk:** Cross-customer case disclosure, staff status
    spoofing, and accidental exposure of AI transcripts as support records.
11. **Additive remediation:** Define a JSON support contract reusing current
    support services/models and ownership rules, then add a React adapter;
    retain the server-rendered support flow and current notification adapter.
12. **Dependencies:** API envelope and case-state contract, role policy,
    PII retention/disclosure review, notification delivery ownership.
13. **Safe local tests:** Synthetic customer case create/read/reply,
    cross-owner 404/denial, staff-only state change, closed-case behavior,
    notification creation without external send.
14. **Staging-only verification:** Disposable accounts, email/SMS sinks or
    disabled external sends, case ownership, in-app notification read state.
15. **Rollback:** Disable only new React support path; existing Flask
    support, case history, and notification API remain.

### G7 - P0: upload/asset staging gate before connecting new clients

1. **Journey and ID:** Journey 19; `NEX-SECURITY-UPLOADS`.
2. **Current status:** PARTIALLY_CONNECTED.
3. **Frontend:** Seller HTML product form is established; Phase 26 found no
   verified React upload adapter. React image display consumes catalog media
   URLs returned by the API.
4. **Client/endpoint:** Do not infer a React upload endpoint. Existing
   server-rendered form is the verified upload caller.
5. **Backend/model:** `app/services/catalog_media.py`; product/seller
   models and seller route handling. The service uses private quarantine,
   scanner, Pillow decode/re-encode, and S3-compatible storage.
6. **Authentication/session/CSRF:** Approved seller role, CSRF on form
   mutation, size/type/signature checks, private quarantine, and safe public
   URL constraints.
7. **Exact gap:** Actual scanner binary, bucket, object permissions,
   public URL/CDN, and cleanup policy are not verified in staging; React
   upload path is absent from Phase 26 evidence.
8. **Evidence/tests:** Phase 26 journey 19; `tests/test_catalog_media.py`,
   `tests/test_security_ops.py`. Source shows smoke check performs a
   temporary external upload and deletion only with
   `--confirm-external-write`.
9. **User impact:** Seller images may be unavailable or uploads fail closed
   when scanner/storage is not configured.
10. **Security/privacy risk:** Malware, decompression abuse, public exposure,
    unsafe object URL, or retained quarantine object.
11. **Additive remediation:** First complete scanner/object-store checks in
    a disposable staging bucket; only then design any React adapter to reuse
    the same service and validation pipeline. Never add browser direct-to-
    bucket credentials.
12. **Dependencies:** Disposable isolated bucket/prefix, ClamAV service,
    short-lived least-privilege storage credentials, test images only,
    operator approval for the smoke check's external write/delete.
13. **Safe local tests:** Existing synthetic upload tests, scanner
    unavailable/rejected cases, MIME/signature mismatch, oversized image,
    traversal/public URL validation; no real media upload.
14. **Staging-only verification:** EICAR or provider-approved harmless
    scanner fixture only under the scanner operator's documented policy;
    valid synthetic image through quarantine and object store; verify
    metadata/access and cleanup in disposable bucket.
15. **Rollback:** Disable only new upload entry points; retain existing
    secure server form and media records. Clean only known synthetic objects
    from the disposable staging prefix.

### G8 - P2: background task and external-provider operations

1. **Journey and ID:** Journey 21; `NEX-INTEGRATIONS-BACKGROUND`,
   `NEX-BACKUP-DR`.
2. **Current status:** BLOCKED_BY_CONFIGURATION.
3. **Frontend:** In-app notification surfaces exist; no verified client
   scheduler/worker control surface is in scope.
4. **Client/endpoint:** Existing task entry points are Flask CLI commands,
   not a verified browser API. Do not invent a worker endpoint.
5. **Backend/model:** Flask CLI in `app/__init__.py`; mail/Telegram,
   notification digest, outbox, backup, payment reconciliation services and
   associated models. `.github/runbooks/backup-restore.md` describes
   operator practice.
6. **Authentication/session/CSRF:** Operator/hosting identity and least
   privilege govern scheduled commands; webhooks must use existing
   signature/secret validation and idempotent handlers.
7. **Exact gap:** No staging scheduler/worker deployment, queue-age
   monitoring, provider credentials, disposable restore target, or
   delivery/reconciliation evidence was established.
8. **Evidence/tests:** Phase 26 journey 21; `tests/test_telegram_bots.py`,
   `tests/test_security_ops.py`, `tests/test_stage10_operations.py`,
   `tests/test_notifications.py`. Phase 18 marks restore rehearsal blocked.
9. **User impact:** Delayed/retried email, alerts, digests, webhook
   consumption, or recovery operations may not run automatically.
10. **Security/privacy risk:** Duplicate delivery, unsafe retry of
    financial operations, webhook replay, sensitive logs, or unbounded
    background processing.
11. **Additive remediation:** Inventory each scheduled command and
    idempotency contract, then configure an approved staging scheduler with
    bounded batches, logs, and retry visibility. Keep CLI manual operations.
12. **Dependencies:** Hosting/scheduler access, synthetic database, test
    provider endpoints, runbook owner, queue/outbox reconciliation policy,
    isolated restore destination.
13. **Safe local tests:** Mock providers and invoke bounded commands using
    synthetic data; test duplicate/retry behavior and restore only to a
    disposable target. No external send or restore is part of this phase.
14. **Staging-only verification:** Test provider sandbox delivery, duplicate
    webhook, worker retry/age, scheduler overlap behavior, and backup restore
    to an approved isolated database.
15. **Rollback:** Disable only the new staging schedule/worker; preserve
    queued records for reconciliation. Do not run restore over active data.

### G9 - P3: preserve separate Flask and Express AI boundaries; improve contract evidence

1. **Journey and ID:** Journeys 16 and 17; `NEX-FLASK-AI`,
   `NEX-EXPRESS-AI`, preserved `NEX-AI-ASSISTANTS`.
2. **Current status:** Both CONNECTED_BUT_NOT_LIVE_VERIFIED.
3. **Frontend:** Flask AI template/client and React AI drawer/pages are
   distinct surfaces.
4. **Client/endpoint:** Flask AI uses its `/ai` route family;
   `server.ts` provides Express `/api/gemini/*` and related routes. Do not
   treat one provider/client contract as the other.
5. **Backend/model:** `app/ai/core`, `app/ai/marketplace_tools.py`,
   `app/routes/ai.py`; Express `server.ts` and Google GenAI SDK.
6. **Authentication/session/CSRF:** Flask AI derives customer/seller/admin
   scope server-side and rate-limits. Express AI has a separate caller
   boundary; no Flask session equivalence is established.
7. **Exact gap:** Live provider configuration, cost/rate controls and
   staging failure behavior are unverified. Phase 24/26 notes broad Express
   CORS and a 50 MB JSON limit as review risks; these are not silently changed
   here.
8. **Evidence/tests:** Phase 26 journeys 16-17; `tests/test_ai_core.py`,
   `tests/test_ai_features.py`, plus web lint/build. No live provider calls
   in this phase.
9. **User impact:** Optional assistant features may be unavailable or return
   provider errors; core commerce must remain usable.
10. **Security/privacy risk:** Prompt injection, unrestricted origin/large
    requests, provider cost, secrets, or confusing AI output with authoritative
    commerce data.
11. **Additive remediation:** Keep services separate; document per-client
    capability and graceful fallback, test limits, and handle CORS/request
    bounds in a separately reviewed change with tests.
12. **Dependencies:** Provider sandbox/approved budget, origin allowlist
    decision, request-size/timeout policy, privacy review.
13. **Safe local tests:** Mock provider responses/errors/timeouts and
    untrusted prompts; assert no provider key exposure or commerce mutation.
14. **Staging-only verification:** Only synthetic prompts and approved
    provider sandbox; verify origin, usage limits, fallback, latency and
    server logs contain no secrets or unnecessary personal data.
15. **Rollback:** Disable only an optional AI entry or revert additive
    capability handling; never remove Flask/Express routes or provider
    adapters as part of this plan.

### G10 - P2: Android contract/environment compatibility

1. **Journey and ID:** Journey 18; `NEX-ANDROID-CLIENT`,
   `NEX-ANDROID-API`.
2. **Current status:** CONNECTED_BUT_NOT_LIVE_VERIFIED.
3. **Frontend:** Android Retrofit and Compose sources under
   `android/app/src/main/`.
4. **Client/endpoint:** `ApiService.kt` targets the existing `/api/v1`
   auth/catalog/cart/search/banner contracts; `NetworkModule.kt` supplies
   base URL, cookie jar and CSRF interceptor.
5. **Backend/model:** Flask API registration and the corresponding auth,
   catalog and commerce routes/services.
6. **Authentication/session/CSRF:** In-process `PersistentCookieJar`;
   `CsrfInterceptor` sends the token for mutating methods when available.
7. **Exact gap:** Android unit tests do not establish device/emulator TLS,
   release API URL, cookie persistence across app restart, or live response
   compatibility.
8. **Evidence/tests:** Phase 26 Android `:app:test` passed; `NetworkModule`,
   `ApiService`, `PersistentCookieJar`, and `CsrfInterceptor` inspected.
9. **User impact:** A release build with placeholder URL or incompatible
   cookies may not authenticate against the intended environment.
10. **Security/privacy risk:** Wrong-origin credentials, insecure transport,
    cross-account cookies on shared devices, or BODY logs leaking user data.
11. **Additive remediation:** Add explicit staging build configuration only
    after the staging host is approved; add contract coverage without
    changing existing debug/release defaults or API DTOs.
12. **Dependencies:** Approved staging base URL, test device/emulator,
    Android release configuration review, test accounts.
13. **Safe local tests:** Existing `:app:test`, URL configuration tests,
    DTO parsing tests with synthetic payloads.
14. **Staging-only verification:** Debug/staging build against non-prod
    server, login/logout, cookie/CSRF, catalog and cart with synthetic data;
    no release signing or production endpoint.
15. **Rollback:** Retain the last known working debug/release URL contract;
    remove only any newly added staging flavor/properties if verified
    incompatible.

## Dependency order and exit criteria

1. Close G0 policy/negative-test gaps before wiring customer, seller, or Admin
   mutations.
2. Confirm staging isolation and configuration from Phase 28 before any
   browser/device/provider test.
3. Implement G1-G7 as separate, reviewable increments; API contracts and
   permission tests precede React mutations.
4. G8 depends on isolated data, provider sandboxes, and observable
   idempotency; G9 is optional and must not gate browse/cart/checkout.
5. G10 requires the approved environment URL and a non-production device
   run.
6. Close a gap only with local tests plus its specified staging evidence.
   No item in this document authorizes implementation, external writes,
   remote settings changes, or deployment.

## Phase 27 disposition

**Plan produced; implementation intentionally not performed.** No new API
endpoint or provider setting is assumed to exist. Exact staging and local
verification state is recorded separately in
`PHASE28_SAFE_STAGING_READINESS_REPORT.md`.

## Verification run for this phase

| Command | Result |
|---|---|
| `python scripts\validate_repository_structure.py --fail-on-review` | **PASS** - required docs `6/6`, 190 registry paths checked, no missing imports/config, no source deletion/rename findings. Worktree review counts include pre-existing changes. |
| `python -c "import json; from pathlib import Path; p=Path('docs/architecture/FEATURE_REGISTRY.json'); d=json.loads(p.read_text(encoding='utf-8')); ids=[f['id'] for f in d['features']]; assert len(ids)==22 and len(ids)==len(set(ids)); print(f'FEATURE_REGISTRY JSON PASS; entries={len(ids)}; unique IDs PASS')"` | **PASS** - 22 entries, unique IDs. |
| `npm run lint` | **PASS** - `tsc --noEmit`, exit code 0. |
| `npm run build` | **PASS with warning** - Vite build succeeded; existing chunks exceed the 500 kB advisory threshold. |
| `python -m pytest -q` | **PASS** - 305 passed in 370.81s. Python emitted an environment `.pth` warning for a missing sibling `D:\FTP\Telegram-Bot\src`; it did not fail the suite. |
| `$cache = Join-Path $env:TEMP 'NexHaatPhase28GradleProjectCache'; & .\android\gradlew.bat -p android :app:test --no-daemon --project-cache-dir $cache` | **PASS with warnings** - `BUILD SUCCESSFUL` in 5m 41s; unsigned release, Android SDK XML compatibility, deprecated Android/Gradle APIs, and kapt processor-option warnings. |
| `git diff --check` | **PASS** for tracked/staged diff. New untracked report whitespace was separately checked. |

These are local checks only. They do not close any staging/provider/operator
gate in this plan.
