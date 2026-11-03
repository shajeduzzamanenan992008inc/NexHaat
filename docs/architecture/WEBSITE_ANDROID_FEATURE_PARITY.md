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
