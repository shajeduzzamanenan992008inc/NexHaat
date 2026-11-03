# Phase 0 — Repository, Parity, and Risk Audit

**Date:** 3 November 2026
**Scope:** Read-only audit of the Website (Flask + React), the Android client, the Express AI
service, authentication, product media, motion, and delivery configuration.
**Local HEAD:** `0f7798d` (`main`, 2 commits behind `origin/main`)
**Owner-reported `main`:** `d9dfa2e`
**Status:** AUDIT ONLY. No product feature was implemented.

---

## 1. Method and evidence limits

Everything below was established by reading files in this working copy, plus the local checks
recorded in §8. The following were **not** available and are marked accordingly:

| Not available | Effect |
|---|---|
| GitHub Actions run logs / authenticated `gh` | Remote CI conclusions are **NOT VERIFIED**. Local CI repair is separate (§7). |
| A running Flask/Express server | No runtime HTTP behaviour was proven. All API statements are source-level. |
| A physical Android device or emulator | No on-device rendering, image loading, navigation, or motion was observed. |
| Provider consoles (Google, Microsoft, GitHub, Firebase, Gemini, Brevo, SSLCOMMERZ, S3, Telegram) | Provider readiness is **UNKNOWN**, not "working". |
| Azure portal / federated credentials | Production deployment state is **BLOCKED**. |

Labels used: **CONFIRMED** (source proves it), **PARTIAL** (some of the chain exists),
**NOT WIRED** (client calls something the server does not serve), **NOT VERIFIED**.

---

## 2. Runtime inventory (verified present)

| Surface | Evidence | Role |
|---|---|---|
| Flask backend | `app/__init__.py`, `app/routes/*`, `app/api/routes/*`, `run.py`, `wsgi.py` | Authoritative marketplace, session identity, `/api/v1` JSON API |
| Server-rendered UI | `app/templates/**`, `app/static/**` | OTP verification, portals, product forms |
| React client | `src/App.tsx`, view switch (no router), `src/pages/*` (13 pages) | Additional web experience |
| Express AI service | `server.ts`, `serverSecurity.ts` — 9 `/api/gemini/*` routes | Gemini proxy with server-side key |
| Android client | `android/app/src/main/java/com/nexhaat/app/**` (91 Kotlin files) | Compose client over `/api/v1` |
| Persistence | `app/models/*`, `migrations/versions/*` | Single Alembic head `20261103_01` |
| Deployment | `.github/workflows/main_nexhaat.yml`, `ci.yml`, `codeql.yml`, `sbom-provenance.yml`, `dependency-review.yml`, `config-validation.yml` | Azure App Service (Production slot) via OIDC |

React has **no URL router**: `App.tsx` switches on `currentView` from `AppContext`. Deep links,
refresh persistence, and shareable auth URLs therefore do not exist on the web client.

---

## 3. Confirmed findings

### F-01 — `POST /api/v1/auth/social-login` is an account-takeover endpoint (CRITICAL, CONFIRMED)

`app/api/routes/auth.py:411-447` accepts `{provider, email, display_name}` **from the client**,
looks the account up by that email, and calls `_start_authenticated_session(user)` after a
successful login-free path. No ID token, authorization code, issuer, audience, nonce, or
signature is checked. If the email does not exist, an account is auto-created with a random
password and a placeholder phone number (`+8801700000000`).

Consequences:

* Anyone who knows a customer/seller/rider email can obtain that account's session.
* The route keeps the ordinary CSRF requirement, so the attacker only needs a session of their
  own to mint a CSRF token — the CSRF layer does not mitigate this.
* Android exposes it (`ApiService.socialLogin`), so the client contract already assumes it works.

**This must be disabled or replaced before any social sign-in work proceeds.**

### F-02 — "2FA" is not server-side two-factor authentication (HIGH, CONFIRMED)

`app/api/routes/auth.py:450-525`:

| Expected | Actual |
|---|---|
| Secret stored server-side, encrypted at rest | `session["totp_pending_secret"]`, `session["totp_secret"]` — Flask sessions are **signed, not encrypted** cookies, so the shared secret is readable by the client |
| Backup codes hashed in the database | `session["totp_backup_codes"]` — plaintext list in the same cookie, and returned in the setup response |
| Code verified against the enrolled secret only | `verify_2fa` prefers a **client-supplied `secret`** (`payload.get("secret")`), so enrollment can be completed with a secret of the caller's choosing |
| Login requires the second factor | `login()` (`auth.py:165-185`) never checks 2FA; `_start_authenticated_session` (`app/routes/auth.py:79-91`) calls `session.clear()`, discarding every 2FA flag |
| Persistence across sessions/devices | No TOTP column on `User` (no `totp` reference anywhere in `app/models`) |
| Disable / regenerate / recovery management | No such routes |
| Attempt throttling | No counter or rate limit on `/2fa/verify` |

The Android `SecuritySettingsScreen` + `SecuritySettingsViewModel` are a complete, honest UI on
top of an enrolment that cannot gate a login. Today this feature is **cosmetic 2FA** and must not
be described as protecting accounts.

### F-03 — Android AI calls the Flask host with the Express contract (HIGH, NOT WIRED)

| Element | Value |
|---|---|
| Retrofit `baseUrl` | `BuildConfig.BASE_URL` — Flask, default `http://10.0.2.2:5000/` (`NetworkModule.kt`, `build.gradle.kts`) |
| Android call | `@POST("api/gemini/chat")` (`ApiService.kt:180`) → **Flask** `/api/gemini/chat` |
| Flask routes | `/ai/*` only (`app/routes/ai.py`); no `/api/gemini/*` handler exists in Flask |
| Real handler | Express `server.ts:158` `POST /api/gemini/chat`, which streams with `generateContentStream` (SSE) |
| Android response model | `AIChatResponseDto { reply?, text?, suggested_products }` — a JSON object, not SSE |
| Android history payload | `{role, parts}`; Express validation requires `{sender, text}` and rejects the request |

So the Android assistant cannot succeed against the current backend even if the Express service
is reachable. `AIAssistantViewModel` renders a canned hello and an apology string on failure, which
is why the screen *looks* present.

The web assistant (`src/components/AIAssistantDrawer.tsx`) calls the same-origin Express routes
and is the working reference implementation — but those routes carry **no application
authentication** (already recorded in `PHASE33_END_TO_END_INTEGRATION_AUDIT_REPORT.md`), so they
depend entirely on ingress protection.

### F-04 — Physical-device networking defaults to an emulator-only host (HIGH, CONFIRMED by configuration)

`build.gradle.kts` defaults `NEXHAAT_DEBUG_BASE_URL` to `http://10.0.2.2:5000/`. `10.0.2.2` is the
Android **emulator's** alias for the host loopback; a physical phone cannot resolve it. Unless
`NEXHAAT_DEBUG_BASE_URL` (and usually `NEXHAAT_MEDIA_BASE_URL`) are set in `android/local.properties`
or the environment, every request — catalog, images, auth — fails on the owner's real device.

This is the most probable root cause of "product images are missing in Android", together with:

* `ProductImage` resolves relative references against `MEDIA_BASE_URL`; when the media base is
  unset/placeholder the resolver **deliberately returns null** (`ImageUrlResolver.resolve`) and the
  UI falls back to a category image.
* Those fallbacks are remote `images.unsplash.com` URLs (`ImageUrlResolver.CATEGORY_FALLBACKS`,
  `app/models/catalog.py`), so a device with no internet shows "No image" even when the API works.
* Real uploads are absolute S3 URLs (`catalog_media._external_media_url`), so they are unaffected
  by media-base configuration — no runtime test was possible here.

### F-05 — Product media pipeline itself is sound (INFORMATIONAL, CONFIRMED)

`store_catalog_image` enforces size, quarantine, scanner, re-encode, and refuses to publish on
failure; `product_to_dict` returns both `image` and `display_image`. There is **no evidence** of a
server-side image bug. The gap is client configuration, not media storage.

### F-06 — Web has no Microsoft/GitHub sign-in and no server-verified social identity (HIGH, CONFIRMED)

* `FlaskAuthPanel.tsx` provides email/password login, registration, and sign-out only.
* `AppContext` also runs Firebase `signInWithPopup(googleProvider)` — a **client-only** Firebase
  session. It is never exchanged for a Flask session, so marketplace actions still require the
  Flask login. Two separate "signed in" states coexist.
* No Microsoft or GitHub client code exists anywhere in `src/` or `android/`.
* The only bridge to Flask identity for social login is F-01, which is unsafe.

### F-07 — Android has no social sign-in UI (MEDIUM, CONFIRMED)

`SignInScreen.kt` offers email/password, biometric unlock, sign-up, and forgot-password. No
Google/Microsoft/GitHub button exists; the repository method exists only as an unused API surface.

### F-08 — Motion system is uneven across platforms (MEDIUM, CONFIRMED)

| Surface | Evidence |
|---|---|
| Web | `src/index.css` ambient gradient with `prefers-reduced-motion` guard; 31 files use `transition`/`animate-*` utilities. No motion library dependency, no page-transition layer (view switch is instant). |
| Android | 5 of 91 Kotlin files reference `animate*`/`AnimatedVisibility`/`AnimatedContent`. `MainActivity` goes straight to `NexHaatNavGraph()`: no `SplashScreen` API, no `NavHost` enter/exit transitions, no splash theme in `res/values/themes.xml`. |

There is no documented motion token set (durations/easings) shared by both platforms.

### F-09 — No dedicated release configuration for Android (MEDIUM, CONFIRMED)

`versionCode = 1`, `versionName = "1.0.0"`, `isMinifyEnabled = false`, release signing is optional
and silently skipped when credentials are absent. `NEXHAAT_RELEASE_BASE_URL` defaults to
`https://RELEASE_BASE_URL_REPLACE_ME/`. A release APK built without configuration would be
unsigned and unable to reach any API.

---

## 4. Feature parity matrix

Status vocabulary: **CONFIRMED** (source proves the capability and its server contract),
**PARTIAL** (some of the chain is missing or unverified), **UI ONLY**, **NOT WIRED**, **ABSENT**.

| Feature | Flask/API | Website | Android | Verdict |
|---|---|---|---|---|
| Email/password sign-in | `POST /api/v1/auth/login` (throttle, CSRF) | `FlaskAuthPanel` + `flaskAuth.ts` | `SignInScreen` + `AuthRepository` | CONFIRMED (source); runtime NOT VERIFIED |
| Registration + email OTP | `/register`, `/register/verify` + server-rendered OTP | Panel redirects to Flask OTP page | `SignUpScreen` + `VerifyRegistrationScreen` | PARTIAL — web verification leaves the React app |
| Forgot / reset password | `/forgot-password`, `/reset-password` | Not present in React | `ForgotPasswordScreen` | PARTIAL — web gap |
| Session restore | `/auth/me` | `getCurrentFlaskUser` on load | `SessionViewModel.revalidateSession()` | CONFIRMED |
| Logout | `/auth/logout` | Panel sign-out | `SettingsViewModel` | CONFIRMED |
| Logout all devices / session list | `auth_version` exists | ABSENT | ABSENT | ABSENT |
| Google sign-in | None trustworthy (F-01) | Firebase popup, not linked to Flask | Button absent | NOT WIRED |
| Microsoft sign-in | None | ABSENT | ABSENT | ABSENT |
| GitHub sign-in | None | ABSENT | ABSENT | ABSENT |
| Safe account linking | None | — | — | ABSENT |
| 2FA enrolment (TOTP) | Present but ineffective (F-02) | ABSENT | `SecuritySettingsScreen` | UI ONLY |
| Backup codes | Cookie-only, plaintext | ABSENT | Displayed | UI ONLY |
| 2FA enforcement at login | None | — | — | ABSENT |
| 2FA disable / regenerate | None | ABSENT | ABSENT | ABSENT |
| Security activity / login alerts | `record_audit` writes records | No UI | No UI | PARTIAL (records exist, no surface) |
| Biometric app unlock | — | — | `BiometricPromptHelper`, Keystore-backed, correctly documented as local-only | CONFIRMED (local only) |
| Catalog / search / filters | `/api/v1/products`, `/search`, `/categories` | `CatalogPage`, `HomePage` | `HomeScreen`, `ProductsScreen`, `SearchScreen`, `CategoriesScreen` | CONFIRMED |
| Product images | `image` + `display_image` | `ProductCard`, `ProductDetailPage` | `ProductImage` + resolver | PARTIAL — device config (F-04) |
| Variants | `variants[]` in serializer | Product detail | `ProductDto` | PARTIAL — Android variant selection unverified |
| Cart | `/api/v1/cart*` (guest cart supported) | `CartDrawer` | `CartScreen` | CONFIRMED |
| Wishlist | `/api/v1/wishlist*` | `WishlistPage` | `WishlistScreen` | CONFIRMED |
| Checkout + payment | `/checkout/preview`, `/checkout`, SSLCOMMERZ | `CheckoutPage` | `CheckoutScreen` | PARTIAL — payment continuation unverified on both |
| Orders / order detail / cancel / return | `/api/v1/orders*` | `MyOrdersPage` | `OrdersScreen` | CONFIRMED |
| Order timeline | `order_events` migration, `order_timeline.py` | `MyOrdersPage` | Not present | PARTIAL — Android gap |
| Notifications | `/api/v1/notifications*` | `NotificationsPage` | `NotificationsScreen` | CONFIRMED |
| Reviews / Q&A | `/api/v1` review services | `ProductReviewsSection` | ABSENT | PARTIAL — Android gap |
| Seller portal | `/api/v1/seller/dashboard`, `/orders` | `SellerPortalPage` (partly demo state) | `PortalsScreen` | PARTIAL |
| Rider / Admin portals | Flask routes | React pages (partly demo) | `PortalsScreen` | PARTIAL |
| Support cases | Flask support routes | `SupportPage` | ABSENT | PARTIAL |
| AI assistant | Express `/api/gemini/*` (9 routes, streaming) | `AIAssistantDrawer` (chat, grounding, media) | `AIAssistantScreen` | NOT WIRED (F-03) |
| AI streaming | SSE on Express | Consumed | Not consumed | PARTIAL |
| Profile / account settings | `profiles` service | ABSENT (no page) | `SettingsScreen` | PARTIAL |
| Addresses | Checkout collects inline | Inline | Inline | ABSENT as a managed feature |
| Dark theme | — | Tailwind `dark:` classes | `NexHaatTheme` light/dark | CONFIRMED |
| Localization | EN/BN/HI/AR + `translations/` | `t()` helper, EN/BN strings | `values-bn/strings.xml` | PARTIAL — Android strings exist, locale switching unverified |
| Motion system | — | CSS transitions + reduced-motion | ~5% of screens animated | PARTIAL |
| Startup experience | — | Instant view switch | No splash API / no nav transitions | PARTIAL |

---

## 5. Risk register

| ID | Risk | Severity | Status | Recommended action |
|---|---|---|---|---|
| R-01 | `social-login` grants a session from an unverified email | Critical | CONFIRMED | Disable the route behind a flag; implement real token verification before re-enabling |
| R-02 | TOTP secret + backup codes live in a client-readable signed cookie | Critical | CONFIRMED | Move to encrypted/at-rest database storage; invalidate existing sessions |
| R-03 | 2FA is not required at login | High | CONFIRMED | Add a challenge step between credential check and session start |
| R-04 | Client can submit its own TOTP secret | High | CONFIRMED | Verify only against the server-stored pending secret |
| R-05 | Android AI points at the wrong service and contract | High | CONFIRMED | Route to Express origin with a JSON (or SSE) contract both sides share |
| R-06 | Physical device cannot reach `10.0.2.2` | High | CONFIRMED (config) | Document LAN base URL in `android/local.properties`; fail loudly when unset |
| R-07 | Express AI routes have no application auth | Medium | CONFIRMED | Require a session/proxy gate before public exposure |
| R-08 | Two unlinked identity states on web (Firebase + Flask) | Medium | CONFIRMED | Decide one authoritative identity; remove or explicitly link the other |
| R-09 | Partial features (rider/admin/seller demos, payment continuation) can be mistaken for complete | Medium | CONFIRMED | Keep status labels; harden incrementally |
| R-10 | Release APK is unsigned/placeholder by default | Medium | CONFIRMED | Treat as expected; require configuration in the release runbook |
| R-11 | Android back-stack/session behaviour after expiry | Low | NOT VERIFIED | Device test |

---

## 6. Recommended implementation order (bounded slices)

Ordered by risk reduction per unit of change; each slice is independently reviewable.

1. **Slice A — Close the auth holes.** Disable `POST /api/v1/auth/social-login` (or gate it), and
   remove the client-supplied `secret` from `verify_2fa`. No schema change; tests exist in
   `tests/test_auth.py`. This is the only item that should be treated as urgent.
2. **Slice B — Real 2FA.** Schema + migration for an encrypted TOTP secret, hashed backup codes,
   and enabled-at timestamp; login challenge; attempt limits; disable/regenerate. Then the existing
   Android screen becomes truthful, and a web security page can reuse the same API.
3. **Slice C — Device connectivity and image proof.** Document and validate
   `NEXHAAT_DEBUG_BASE_URL` / `NEXHAAT_MEDIA_BASE_URL` for a physical phone; surface a visible
   configuration error instead of a generic fallback image. Small, and unblocks every other
   Android observation (including F-03 testing).
4. **Slice D — One AI contract.** Pick the transport (SSE with an event parser, or a
   non-streaming JSON endpoint on Express), point Android at the Express origin, and align the
   DTO with the server validator. Add application auth on the Express routes at the same time.
5. **Slice E — One identity.** Decide whether Firebase remains (and is only linked through a
   verified token exchange) or is retired; then implement Google/Microsoft/GitHub on the server and
   expose the same flows on both clients.
6. **Slice F — Parity gaps in shopping.** Order timeline, reviews, profile/addresses, support on
   Android; password recovery and security pages on web.
7. **Slice G — Motion system.** Document duration/easing tokens, add Android splash + nav
   transitions, then page transitions on web, guarded by reduced-motion.

---

## 7. CI and delivery state observed during the audit

* The working copy had an **uncommitted, malformed** `.github/workflows/ci.yml` in which the
  `pytest` step and the whitespace step had been merged into one block (duplicated comment lines,
  no step boundary). It was restored to the committed content (`Run Python test suite` →
  `python -m pytest -q`, then `Reject whitespace errors` → `git diff --check`). `git diff` is now
  empty for that file and `git diff --check` exits 0.
* Local `main` is 2 commits **behind** `origin/main`; the reported failing commit `d9dfa2e` is not
  present locally, so its exact diff could not be examined.
* The whitespace step as committed (`git diff --check`, no arguments) inspects the working tree of
  a fresh checkout, which is normally empty — it cannot detect whitespace in the commit being
  built. Whether the reported failure came from the commit content or from the malformed workflow
  is **NOT VERIFIED** without the run log.
* `.github/workflows/main_nexhaat.yml` deploys on every push to `main` with `environment:
  production` and OIDC secrets. Azure federated-credential trust and the current deployment state
  were not verified.

---

## 8. Local verification executed for this audit

| Check | Command | Result |
|---|---|---|
| Python test suite | `python -m pytest -q` | **PASS** — 316 passed in 372.48s |
| Python lint | `python -m ruff check .` | **PASS** — all checks passed |
| Migration heads | `python -m flask --app run.py db heads` | **PASS** — single head `20261103_01` |
| Whitespace | `git diff --check` | **PASS** — exit 0 |
| Web build / typecheck | `npm run build` | **NOT RUN** (not required for a read-only audit) |
| Android build / unit tests | `./gradlew :app:testDebugUnitTest` | **NOT RUN** (needs configured base URL/JDK; not required here) |
| Browser, device, provider, Azure | — | **NOT TESTED / BLOCKED** |

---

## 9. What this document does not claim

It does not claim that any provider is configured, that any screen works at runtime, that the
Azure deployment is healthy, or that the parity matrix is complete beyond the routes and files
read. Items marked NOT VERIFIED require a browser, a device, provider credentials, or
authenticated GitHub/Azure access.
