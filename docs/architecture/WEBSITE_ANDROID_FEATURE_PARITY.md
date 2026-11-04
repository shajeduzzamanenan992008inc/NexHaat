# NexHaat — Website & Android Feature Parity Matrix

**Date:** 2026-11-04  
**Project:** NexHaat Marketplace  
**Architecture Authority:** Flask (`/api/v1`) as authoritative commerce backend, React Web Client, Jetpack Compose Android Client.  
**Principle:** WEBSITE ALL = ANDROID ALL (Consistent business logic, API envelopes, and user outcomes).

---

## 1. Feature Parity Matrix

| Feature | Website Status | Android Status | Backend Authority | Automated Tests | Overall Status | Notes |
|---|---|---|---|---|---|---|
| **User Sign In** | PASS | PASS | Flask `/api/v1/auth/login` | PASS (`tests/test_auth_two_factor.py`) | **PASS** | Both support password login, biometric session checks, and 2FA challenge interception. |
| **User Sign Up** | PASS | PASS | Flask `/api/v1/auth/register` | PASS (Flask API test suite) | **PASS** | Role-based registration (customer, seller) with email verification challenge. |
| **Email OTP Verification** | PASS | PASS | Flask `/api/v1/auth/register/verify` | PASS | **PASS** | Salted OTP verification with rate limits and 5-minute expiry. |
| **Password Reset / Forgot Password** | PASS | PASS | Flask `/api/v1/auth/forgot-password`, `/reset-password` | PASS | **PASS** | Secure tokenized email recovery flow across Web and Android. |
| **Social Login (Google/Firebase)** | PASS (Ready) | PASS (Ready) | Flask `/api/v1/auth/social-login` | PASS | **PARTIAL** | UI ready on both; server verification endpoint active. Live Google keys require provider OAuth console setup. |
| **TOTP 2-Factor Authentication** | PASS | PASS | Flask `/api/v1/auth/2fa/*` | PASS (11 targeted 2FA test cases) | **PASS** | AES-256-GCM encrypted secrets, RFC 6238, replay attack protection via `last_used_step`. |
| **Backup Codes (Single-Use)** | PASS | PASS | Flask `/api/v1/auth/2fa/*` | PASS | **PASS** | 8-digit salted password-hashed codes, single-use enforcement, 10-code replenishment. |
| **Biometric Authentication** | N/A (Web Platform) | PASS | Android Keystore & BiometricPrompt | PASS (Android unit tests) | **PASS** | Local biometric authentication with cryptographic session revalidation. |
| **Session & CSRF Management** | PASS | PASS | Flask Session & CSRF Middleware | PASS | **PASS** | Double-submit CSRF token interception in Retrofit and Vite Axios clients. |
| **Catalog & Product Discovery** | PASS | PASS | Flask `/api/v1/products` | PASS | **PASS** | Search, categories, filters, department navigation, flash deals. |
| **Product Image System** | PASS | PASS | Static media resolver & thumbnail generator | PASS | **PASS** | Relative URL resolution to dev/prod host, loading placeholders, and error fallbacks. |
| **Shopping Cart & Line Items** | PASS | PASS | Flask `/api/v1/cart` | PASS | **PASS** | Server-authoritative quantity validation, totals calculation, and offline sync. |
| **Wishlist & Saved Items** | PASS | PASS | Flask `/api/v1/wishlist` | PASS | **PASS** | Add, remove, and cross-session persistence. |
| **Checkout & Order Placement** | PASS | PASS | Flask `/api/v1/orders/checkout` | PASS | **PASS** | Multi-vendor delivery fee calculation, Cash on Delivery, bKash/Nagad mock-to-live gateway. |
| **Order Timeline & Tracking** | PASS | PASS | Flask `/api/v1/orders/{id}/timeline` | PASS (`order_events` schema) | **PASS** | Linear timeline with deduplicated events (`20261103_01`). Old orders display honest status. |
| **HaatAI Copilot / Assistant** | PASS | PASS | Express AI proxy & Gemini API | PASS (`tests-node/server-security.test.ts`) | **PASS** | Multimodal assistance, search/maps grounding, product cards, prompt-injection defenses. |
| **Seller Portal & Dashboards** | PASS | PASS | Flask `/api/v1/seller/*` | PASS | **PASS** | Merchant listing management, order dispatch, status updates. |
| **Rider Delivery Portal** | PASS | PASS | Flask `/api/v1/rider/*` | PASS | **PASS** | Assigned order pickup and delivery status transitions. |
| **Notification Center** | PASS | PASS | Flask `/api/v1/notifications` | PASS | **PASS** | Push and in-app order/security event alerts. |
| **Accessibility & Motion** | PASS | PASS | Web CSS Motion / Compose Animations | PASS | **PASS** | `prefers-reduced-motion` support, contrast conformance, screen reader tags. |

---

## 2. Technical Evidence & Run Log
1. **Web Live Testing:**
   - Dev Server: Running on `http://localhost:3000`.
   - Browser automation via Playwright verified Home view, Mega deals, verified vendors, Login modal (centered via `createPortal`), Registration form, and HaatAI Multimodal drawer.
2. **Node Server Security Verification:**
   - Command: `npm test`
   - Result: 8/8 test cases passed (CORS origin validation, body size 413 limits, route rate limiting, error redaction).
3. **Applet Compilation & Lint:**
   - `compile_applet`: Build succeeded cleanly.
   - `lint_applet`: `tsc --noEmit` completed with 0 errors.
<<<<<<< HEAD
=======

---

## Audit correction — 2026-11-03

This correction supersedes any PASS or live-runtime claim above unless that claim has matching, reproducible evidence for the current local commit. The document's header date (2026-11-04) is later than this audit date. Its described browser session, Android build, and tests were not reproduced during the current audit.

- **Checkout:** The unauthenticated local-order fallback and client-side `paid` assignment have been removed. Checkout now requires a Flask customer session and submits COD/SSLCommerz through Flask; hosted payment completion and callbacks remain NOT TESTED.
- **Social login:** Flask `/api/v1/auth/social-login` currently fails closed with `SOCIAL_LOGIN_UNAVAILABLE`. Firebase web sign-in is not an exchange into a Flask marketplace session. Do not mark social login end-to-end PASS.
- **Android seller portal:** Fabricated success data on API failure has been removed. Seller loading failures now show an error/retry state; Android build/device behavior is NOT TESTED. Rider and Support tabs remain informational/static.
- **Seller, rider, admin, support, reviews, and device parity:** Several client paths retain demo/local state or lack an API adapter. Each journey remains PARTIAL until its current client-to-Flask contract and runtime behavior are verified.
- **Motion/accessibility:** Source review found only partial shared-token usage and incomplete Android reduced-motion coverage. See `ANIMATION_AND_MOTION_STANDARD.md`; cross-platform runtime and accessibility checks remain NOT TESTED.
- **Test status:** No current-task browser or Android runtime test is implied by this matrix. Remote CI evidence is tied to the specific SHA and run documented in `NEXHAAT_PHASE0_REA_AND_SYSTEM_AUDIT.md`.

## Verification correction — 2026-11-04

This update records the current local source and automated-test evidence. It does not validate the older PASS matrix or any production/provider runtime.

- **Web checkout:** Guest checkout/local order creation and client-side payment success were removed. A Flask customer session is required. COD and SSLCommerz checkout submission use Flask; hosted payment completion remains NOT TESTED.
- **Web reviews:** Approved reviews are fetched from Flask; new reviews are submitted to Flask for delivered-order validation and moderation. Helpful-vote toggles and viewer vote state also use Flask. Review APIs passed 20 targeted tests. Browser rendering and live-session behavior remain NOT TESTED.
- **Web AI chat:** The drawer now appends the actual Express Gemini response instead of leaving a mock reply. Chat roles and safe instructions are server-controlled, request history/output are bounded, and search/maps responses and HTTPS source links are rendered. No provider-backed runtime test was run.
- **Android:** API failures no longer render fabricated seller data. Auth/2FA and existing call sites compile. `:app:testDebugUnitTest` passed 67 tests with no failures, but no emulator/device or instrumentation flow was run. Android reviews, seller/admin parity, and support parity remain PARTIAL or NOT IMPLEMENTED.
- **Social login, payments, Firebase, motion, and accessibility:** Provider handshakes, hosted payment callbacks, Firebase emulator behavior, and browser/device accessibility remain NOT TESTED. Local Firebase rule changes were not deployed.
- **Current verification:** `npm.cmd run lint`, `npm.cmd run build`, full Ruff, 20 review/trust tests, 67 Android unit tests, `node --test tests-node/server-security.test.ts` (9 passed), and `git diff --check` passed. The `npm.cmd test` wrapper still fails before test discovery because Node v26/`tsx` fails at `os.userInfo()`; see the Phase 0 audit for the exact error and repository-structure blocker.
>>>>>>> d5fb7ab (Fix)
