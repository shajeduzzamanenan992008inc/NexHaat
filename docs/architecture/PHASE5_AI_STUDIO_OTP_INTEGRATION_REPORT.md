# Phase 5 — AI Studio UI and Copilot OTP integration report

## Scope and preservation boundary

This report is read-only discovery plus verification. No application source,
database, migration, production setting, or deployment target was changed for
this phase. Existing Flask, React/TypeScript, Express, Android, Firebase,
payment, AI, and OTP implementations remain present.

The repository does not contain reliable author metadata proving which lines
were written by a particular AI tool. Therefore, “Copilot OTP” below means the
existing OTP implementation identified by the requested preference and verified
by its source, tests, and runtime behavior; authorship is **NOT TESTED**.

## Status summary

- **PASS:** AI Studio-style React/Vite page and component inventory completed.
- **PASS:** Flask OTP lifecycle, templates, services, models, API routes, and
  tests inspected.
- **PASS:** Existing OTP/auth/security tests: 64 passed.
- **PASS:** Existing full Flask suite previously verified: 305 passed.
- **PASS:** Existing React production build previously verified after adding the
  lockfile: TypeScript and Vite build succeeded.
- **FAIL:** The React marketplace still uses local/mock data and Firebase
  authentication rather than the Flask marketplace source of truth.
- **BLOCKED:** Full React-to-Flask integration and Android live API verification
  require an approved staging contract and environment.
- **NOT TESTED:** Real email/SMS delivery, real Firebase provider behavior,
  production Azure configuration, live payments, and production database.
- **NEEDS APPROVAL:** Any canonical-route selection, authentication migration,
  API wiring, or production deployment.

## 1. Google AI Studio / React implementation inventory

The preserved React implementation is under [`src/`](../../src/) and the
server-side AI implementation is [`server.ts`](../../server.ts).

### Application shell and navigation

- [`src/App.tsx`](../../src/App.tsx) — `App`, `AppContent`, view selection,
  shared `Navbar`, `Footer`, `CartDrawer`, AI drawer, comparison UI, Prime
  modal, and toast container.
- [`src/context/AppContext.tsx`](../../src/context/AppContext.tsx) —
  navigation state, language/theme, Firebase user state, product/catalog
  state, cart, saved-for-later, wishlist, orders, promotions, reviews,
  questions, notifications, seller campaigns, and AI messages.
- [`src/components/Navbar.tsx`](../../src/components/Navbar.tsx) — main
  navigation, account/role controls, search and marketplace actions.
- [`src/components/Footer.tsx`](../../src/components/Footer.tsx) — global
  footer.
- [`src/components/Toast.tsx`](../../src/components/Toast.tsx) — transient
  feedback.

### Customer marketplace pages

- [`src/pages/HomePage.tsx`](../../src/pages/HomePage.tsx) — hero, categories,
  featured/trending content, recommendations, promotions and discovery actions.
- [`src/pages/CatalogPage.tsx`](../../src/pages/CatalogPage.tsx) — catalog
  browsing, search/filter/sort interactions.
- [`src/pages/ProductDetailPage.tsx`](../../src/pages/ProductDetailPage.tsx) —
  product details, variants, reviews/questions, comparison, wishlist and cart.
- [`src/pages/DealsPage.tsx`](../../src/pages/DealsPage.tsx) — promotion/deal
  presentation based on current local promotion data.
- [`src/pages/CheckoutPage.tsx`](../../src/pages/CheckoutPage.tsx) — client-side
  checkout presentation and order creation through `AppContext`.
- [`src/pages/OrderConfirmationPage.tsx`](../../src/pages/OrderConfirmationPage.tsx)
  — confirmation view.
- [`src/pages/MyOrdersPage.tsx`](../../src/pages/MyOrdersPage.tsx) — order
  listing/detail presentation.
- [`src/pages/WishlistPage.tsx`](../../src/pages/WishlistPage.tsx) — wishlist
  display and cart actions.
- [`src/pages/NotificationsPage.tsx`](../../src/pages/NotificationsPage.tsx)
  — notifications and read state.
- [`src/pages/SupportPage.tsx`](../../src/pages/SupportPage.tsx) — customer
  support UI.

### Seller, rider, and admin pages

- [`src/pages/SellerPortalPage.tsx`](../../src/pages/SellerPortalPage.tsx) —
  seller products, inventory/order-oriented portal UI and campaign features.
- [`src/pages/RiderPortalPage.tsx`](../../src/pages/RiderPortalPage.tsx) —
  rider workflow presentation.
- [`src/pages/AdminPortalPage.tsx`](../../src/pages/AdminPortalPage.tsx) —
  admin operations and analytics-oriented UI.

### Reusable marketplace and AI components

- [`src/components/ProductCard.tsx`](../../src/components/ProductCard.tsx) —
  reusable product presentation.
- [`src/components/CartDrawer.tsx`](../../src/components/CartDrawer.tsx) —
  cart and saved-for-later interactions.
- [`src/components/CompareModal.tsx`](../../src/components/CompareModal.tsx) and
  [`src/components/ComparisonBar.tsx`](../../src/components/ComparisonBar.tsx) —
  product comparison.
- [`src/components/PrimeModal.tsx`](../../src/components/PrimeModal.tsx) —
  Prime-style membership interaction.
- [`src/components/AIAssistantDrawer.tsx`](../../src/components/AIAssistantDrawer.tsx)
  — text, search grounding, maps, transcription, image, video, music, and
  science assistant flows.
- [`src/components/SearchAnalyticsDashboard.tsx`](../../src/components/SearchAnalyticsDashboard.tsx)
  — search analytics UI.
- [`src/lib/amazonFeatures.ts`](../../src/lib/amazonFeatures.ts) and
  [`src/lib/searchAnalytics.ts`](../../src/lib/searchAnalytics.ts) — reusable
  marketplace/search behavior.
- [`src/lib/firebase.ts`](../../src/lib/firebase.ts) — Firebase Auth and
  Firestore adapter.
- [`src/data/mockData.ts`](../../src/data/mockData.ts) — local users,
  categories, products, promotions, reviews, questions, campaigns, and
  notifications.

### Express/AI routes

[`server.ts`](../../server.ts) preserves:

- `/api/gemini/chat`
- `/api/gemini/search-grounding`
- `/api/gemini/maps-grounding`
- `/api/gemini/transcribe`
- `/api/gemini/generate-image`
- `/api/gemini/edit-image`
- `/api/gemini/generate-video`
- `/api/gemini/animate-image`
- `/api/gemini/generate-music`
- `/api/science/pubchem/:compound`
- `/api/science/analyze-product`
- WebSocket Gemini Live upgrade handling

These are complementary to, not replacements for, Flask marketplace APIs.

## 2. Preferred OTP implementation inventory

### Email registration OTP

Backend:

- [`app/routes/auth.py`](../../app/routes/auth.py)
  - `REGISTRATION_CODE_TTL`
  - `REGISTRATION_CODE_RESEND_SECONDS`
  - `REGISTRATION_CODE_MAX_ATTEMPTS`
  - `_create_registration_challenge`
  - `verify_registration`
  - `resend_registration_code`
  - `_reset_code_digest`
  - `_start_authenticated_session`
- [`app/api/routes/auth.py`](../../app/api/routes/auth.py)
  - `register`
  - `verify_registration`
  - reuses the same Flask challenge helpers and session.
- [`app/models/security.py`](../../app/models/security.py)
  - `RegistrationChallenge`.
- [`app/services/mail.py`](../../app/services/mail.py)
  - queued registration email delivery.
- [`app/templates/email/registration_code.html`](../../app/templates/email/registration_code.html)
  - localized email template.

UI:

- [`app/templates/auth/verify_registration.html`](../../app/templates/auth/verify_registration.html)
  - six-digit input, CSRF token, resend form, accessible labels, success/error
    states, and 10-minute expiry copy.
- [`app/static/js/otp-verification.js`](../../app/static/js/otp-verification.js)
  - digit distribution, paste handling, auto-submit, loading/progress,
    success/error animation, focus and lock behavior.
- [`app/static/css/otp-verification.css`](../../app/static/css/otp-verification.css)
  - preferred OTP visual system, responsive layout and reduced-motion rules.

### Admin OTP

- [`app/routes/auth.py`](../../app/routes/auth.py)
  - `ADMIN_LOGIN_CODE_TTL`
  - `ADMIN_LOGIN_CODE_RESEND_SECONDS`
  - `ADMIN_LOGIN_CODE_MAX_ATTEMPTS`
  - `admin_login`
  - `verify_admin_login`
  - `resend_admin_login_code`
  - `_admin_login_challenge`
  - `_queue_admin_code`
- [`app/api/routes/auth.py`](../../app/api/routes/auth.py)
  - `/api/v1/auth/admin/code`
  - `/api/v1/auth/admin/verify`
- [`app/models/security.py`](../../app/models/security.py)
  - `AdminLoginChallenge`.
- [`app/templates/auth/verify_admin_login.html`](../../app/templates/auth/verify_admin_login.html)
  - same preferred OTP interaction and CSRF protection.
- [`app/templates/email/admin_login_code.html`](../../app/templates/email/admin_login_code.html)
  - admin code email.

### Password-reset OTP

- [`app/routes/auth.py`](../../app/routes/auth.py)
  - `forgot_password`
  - `verify_reset_code`
  - `reset_password`
  - 10-minute expiry, five-attempt limit, cooldown, non-enumerating response,
    one-time password hash invalidation, and session-bound reset state.
- [`app/templates/auth/verify_reset_code.html`](../../app/templates/auth/verify_reset_code.html)
  - reuses `otp-verification.js` and `otp-verification.css`.
- [`app/templates/email/password_reset_code.html`](../../app/templates/email/password_reset_code.html)
  - reset email.

### Phone OTP

- [`app/services/sms.py`](../../app/services/sms.py)
  - `send_phone_otp`
  - `verify_phone_otp`
  - 10-minute TTL, 60-second resend cooldown, five failed attempts,
    phone/IP throttling, normalized Bangladesh numbers, hashed codes, and
    provider-safe errors.
- [`app/models/security.py`](../../app/models/security.py)
  - `PhoneOtpChallenge`
  - `PhoneOtpThrottle`.
- [`app/routes/auth.py`](../../app/routes/auth.py)
  - phone verification request/confirm account routes.
- [`app/services/sms_adapters/alpha_sms.py`](../../app/services/sms_adapters/alpha_sms.py)
  - provider adapter boundary.
- [`tests/test_sms_service.py`](../../tests/test_sms_service.py)
  - disabled provider, invalid phone, expired code, and incorrect code tests.

### OTP security controls

- [`app/security.py`](../../app/security.py)
  - `login_is_throttled`
  - `phone_is_throttled`
  - `record_login_failure`
  - `record_phone_failure`
  - `reset_code_digest`.
- OTP values are not returned by the service methods and are not stored in
  plaintext.
- CSRF tokens are present in OTP forms and state-changing authentication
  requests.
- Flask session state binds registration, admin verification, and password reset
  flows to the current browser session.

## 3. Flask marketplace/API inventory

Application registration is centralized in [`app/__init__.py`](../../app/__init__.py).

Server-rendered blueprints:

- `main` — homepage, menu, categories, food/product detail, deals, search,
  health/readiness.
- `auth` — customer/seller registration, login, admin OTP, password reset,
  account, invitations, phone and Telegram linking.
- `orders` — cart, checkout, payment callbacks, orders, returns, admin order
  operations, categories and promotions.
- `seller` — seller dashboard, catalog, variants, stock, deals, orders and
  payouts.
- `customer`, `rider`, `admin` — role portals and delivery/admin operations.
- `notifications`, `wishlist`, `support`, `telegram_customer`,
  `telegram_security`, and `ai`.

Versioned API registration is in [`app/api/__init__.py`](../../app/api/__init__.py):

- `health`
- `auth`
- `admin`
- `catalog`
- `commerce`
- `notifications`
- `wishlist`
- `banners`

Representative API contracts:

- `/api/v1/auth/csrf`
- `/api/v1/auth/register`
- `/api/v1/auth/register/verify`
- `/api/v1/auth/login`
- `/api/v1/auth/logout`
- `/api/v1/auth/me`
- `/api/v1/products`
- `/api/v1/products/<id>`
- `/api/v1/categories`
- `/api/v1/search`
- `/api/v1/banners`
- `/api/v1/cart`
- `/api/v1/checkout/preview`
- `/api/v1/checkout`
- `/api/v1/orders`
- `/api/v1/seller/*`
- `/api/v1/admin/*`

The API uses Flask session authentication and CSRF headers for state-changing
requests; it is not currently a Firebase-token API.

## 4. AI Studio-to-Flask integration mapping

| AI Studio surface | Existing source | Current backend | Integration status |
|---|---|---|---|
| Home/catalog/products | `src/pages/*`, `src/data/mockData.ts` | Local mock state | **FAIL** as production integration |
| Cart/checkout/orders | `AppContext.tsx`, checkout pages | Local state/Firestore order write | **FAIL** as Flask integration |
| Wishlist/reviews | `AppContext.tsx`, pages | Local state/Firestore | **FAIL** as Flask integration |
| Firebase Google sign-in | `src/lib/firebase.ts` | Firebase Auth | **CONFLICT** with Flask session |
| AI assistant | `AIAssistantDrawer.tsx` | Express `/api/gemini/*` and `/api/science/*` | **PASS** by code mapping |
| Seller/admin/rider UI | respective React pages | Local role state/mock data | **BLOCKED** for server integration |
| Android marketplace | Android repositories/API service | Flask `/api/v1` | **PASS** as intended contract; live NOT TESTED |

No second production data source should be introduced. The next phase must add
an explicit Flask API adapter and auth/session contract rather than replacing
the current mock/Firebase source files.

## 5. OTP-to-Flask integration mapping

| Flow | Flask UI | Flask API | Session/security | Status |
|---|---|---|---|---|
| Customer registration | `/auth/register`, `/auth/verify-registration` | `/api/v1/auth/register`, `/register/verify` | Registration challenge session, CSRF, hash, expiry, attempt lock | **PASS** |
| Seller registration | `/auth/seller-application`, same verification flow | API role `seller` | Pending seller profile after verification | **PASS** |
| Customer/seller/rider password login | `/auth/login` | `/api/v1/auth/login` | Flask-Login/session, IP throttling, dummy hash | **PASS** |
| Admin OTP login | `/admin/login`, `/auth/verify-admin-login` | `/api/v1/auth/admin/code`, `/verify` | Admin challenge, CSRF, expiry, attempts, session | **PASS** |
| Password reset | `/forgot-password`, `/verify-reset-code`, `/reset-password` | No equivalent complete JSON reset flow identified | Session-bound reset state, hash invalidation, attempts | **PASS** server-rendered; API **BLOCKED** |
| Phone verification | account phone routes | No Android phone-OTP endpoint identified | SMS provider adapter, phone/IP throttle | **PASS** server-rendered; Android **NOT TESTED** |
| React Firebase login | React AppContext | No Flask session bridge | Firebase Auth/Firestore | **CONFLICT** |

OTP is currently connected to Flask authentication and sessions. It is not
connected to the React Firebase session or to a verified React-to-Flask token
exchange.

## 6. Android compatibility

Android API declarations are in
[`android/app/src/main/java/com/nexhaat/app/data/remote/ApiService.kt`](../../android/app/src/main/java/com/nexhaat/app/data/remote/ApiService.kt).

Verified compatibility:

- Android uses `/api/v1/auth/csrf`, login, logout, current-user, cart,
  categories, products, search, product detail, and banners.
- [`NetworkModule.kt`](../../android/app/src/main/java/com/nexhaat/app/di/NetworkModule.kt)
  uses `BuildConfig.BASE_URL`.
- Cookie and CSRF interceptors are present in the Android remote layer.
- DTOs and repositories are present for authentication, catalog, and cart.

Gaps:

- Android does not expose a verified email OTP registration/admin UI in the
  inspected API service.
- Android live interaction with a disposable Flask server was not run in this
  phase.
- Release base URL remains configuration-dependent.
- Provider delivery and production authentication were not tested.

## 7. Duplicate/conflicting implementations

### Alternative implementations to preserve

- Flask/Jinja homepage versus React `HomePage`.
- Flask catalog/product pages versus React catalog/product pages.
- Flask cart/checkout/order workflows versus React local checkout state.
- Flask role portals versus React role portal pages.
- Flask AI routes versus Express Gemini routes.
- Flask session authentication versus Firebase authentication.

### High-risk conflicts

1. **Data authority:** Flask SQLAlchemy/PostgreSQL versus React mock data and
   Firestore.
2. **Authentication:** Flask session/CSRF/roles versus Firebase Auth.
3. **Order/payment integrity:** React local order creation must not become
   authoritative over Flask server-side prices, stock, payment, or settlement.
4. **Role authorization:** React `currentRole` is UI state and cannot authorize
   seller/admin/rider operations.
5. **API origin:** React uses same-origin Express AI routes but has no verified
   marketplace API adapter.
6. **OTP UX:** The preferred Flask OTP UI must remain canonical; React should
   consume a documented contract or link to Flask OTP pages rather than create a
   weaker duplicate.

## 8. Security risks and unresolved issues

- **HIGH:** React mock/Firestore order and catalog paths are not server
  authoritative; do not connect them to production checkout without an API
  adapter and server-side validation.
- **HIGH:** Firebase and Flask identities are not proven to represent the same
  user/session. Silent account linking would risk authorization errors.
- **MEDIUM:** Android OTP compatibility is not implemented/verified as a
  complete flow.
- **MEDIUM:** Real email/SMS provider delivery and failure recovery were not
  tested; only mocks/configuration paths were tested.
- **MEDIUM:** Express AI endpoints require a separate provider/security review
  before exposure through a production marketplace session.
- **LOW:** OTP browser UX and responsive behavior were not fully tested with
  Playwright in this phase.
- **NOT TESTED:** Azure App Service settings, production secrets, CORS policy,
  reverse proxy behavior, live provider quotas, and production database.

No credentials, OTP values, provider keys, or customer data were printed.

## 9. Verification evidence

### PASS

```text
python -m pytest -q tests/test_auth.py tests/test_sms_service.py \
  tests/test_accounts.py tests/test_security_ops.py
64 passed in 476.67s
```

Previously verified in the same preserved worktree:

```text
python -m pytest -q
305 passed
```

The OTP-focused tests cover registration verification, admin OTP gating and
single-use behavior, login/session behavior, password reset cases, and SMS
provider/expiry/invalid-code behavior.

### NOT TESTED / BLOCKED

- Real email or SMS send
- Firebase provider login
- React-to-Flask session bridge
- Android live OTP/API flow
- Production or staging deployment
- Real payment/order writes
- Azure runtime and production configuration

## 10. Phased implementation roadmap

### Phase 5A — Contract first

1. Keep Flask as the marketplace data/auth authority.
2. Define a typed React adapter for `/api/v1`.
3. Define session-cookie/CSRF and CORS policy.
4. Decide whether Firebase is retained only for an additive social-login
   bridge; do not silently migrate identities.

### Phase 5B — Read-only React integration

1. Connect React catalog, categories, banners, product details and search to
   Flask read APIs behind an explicit feature flag.
2. Preserve `mockData.ts` as a fallback/demo implementation.
3. Add loading, empty, error, retry, and unavailable-backend states.

### Phase 5C — Auth/OTP integration

1. Reuse Flask OTP pages and endpoints as the canonical OTP experience.
2. Add React navigation to the Flask auth/OTP flow or a contract-preserving
   API client.
3. Verify registration, admin login, reset, phone verification, CSRF, cooldown,
   expiry, attempts, and session behavior.
4. Add Android OTP endpoints/UI only after the API contract is approved.

### Phase 5D — Server-authoritative commerce

1. Integrate cart, checkout, orders, wishlist, reviews, promotions and seller
   operations with Flask APIs.
2. Keep React presentation/features; remove no existing local/demo capability.
3. Never trust client prices, stock, role, payment status, or order status.

### Phase 5E — Staging and release

1. Use a disposable/staging database and sandbox providers.
2. Run web, Flask, Android, OTP, accessibility, responsive and security tests.
3. Validate health/readiness, rollback and observability.
4. Obtain explicit approval before any production configuration or deployment.

## 11. Files proposed for the next implementation phase

No source files were changed in this Phase 5 audit. Likely additive or focused
changes, subject to approval:

- New typed React API client under `src/lib/` or `src/services/`.
- New React environment/configuration contract for Flask API origin.
- Focused React auth bridge component, without changing Flask OTP UI/security.
- API contract tests under `tests/` and/or frontend tests under `src/lib/`.
- Android OTP DTO/service/screens only after endpoint contract approval.
- Documentation updates under `docs/architecture/`.

Existing files that must remain preserved:

- [`app/routes/auth.py`](../../app/routes/auth.py)
- [`app/api/routes/auth.py`](../../app/api/routes/auth.py)
- [`app/models/security.py`](../../app/models/security.py)
- [`app/services/sms.py`](../../app/services/sms.py)
- [`app/static/js/otp-verification.js`](../../app/static/js/otp-verification.js)
- [`app/static/css/otp-verification.css`](../../app/static/css/otp-verification.css)
- [`app/templates/auth/verify_registration.html`](../../app/templates/auth/verify_registration.html)
- [`app/templates/auth/verify_admin_login.html`](../../app/templates/auth/verify_admin_login.html)
- [`app/templates/auth/verify_reset_code.html`](../../app/templates/auth/verify_reset_code.html)
- all existing React pages/components and [`server.ts`](../../server.ts)
- all Android source, migrations, integrations, and user worktree changes

## Final decision gate

The preferred implementation to preserve is:

- **Marketplace UI/features:** existing Google AI Studio-style React/Vite pages
  and Express AI features.
- **OTP experience/security:** existing Flask OTP implementation with its
  `otp-verification.js`/CSS UI and server-side challenge flows.
- **Marketplace authority:** existing Flask backend/API and database.
- **Android authority:** existing Flask `/api/v1` contract.

Integration should proceed only after approval of the authentication/session
contract and staging strategy. This phase performed no commit, push, merge,
deployment, production restart, production configuration change, database
mutation, or destructive operation.
