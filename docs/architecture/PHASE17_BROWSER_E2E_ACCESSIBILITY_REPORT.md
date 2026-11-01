# Phase 17 — Browser E2E, Accessibility, and Integration Verification

**Date:** 2026-11-01  
**Status:** PARTIAL / BLOCKED for authenticated staging E2E  
**Scope:** Safe local browser verification only. No real customer data,
credentials, OTP delivery, payment, provider call, production system, or
database mutation was used.

## Executive summary

The existing Playwright MCP browser environment was available, so no browser
dependency was added. The built React application was served locally and
verified at desktop, tablet, and mobile viewport sizes. Existing customer UI
entry points, lazy-loaded views, authentication dialog/OTP handoff entry,
wishlist, cart, notifications, AI drawer, keyboard focus, and reduced-motion
behavior were exercised without submitting credentials or creating an order.

The local Flask API also ran on `http://127.0.0.1:5009` for read-only checks.
Direct requests to liveness, categories, and products succeeded, while the
unauthenticated session endpoint correctly returned 401. A separately built
React preview configured for that Flask origin reached the API but the browser
blocked cross-origin requests because no CORS allow-list was configured for the
temporary `http://127.0.0.1:3001` origin. This is recorded as a staging
configuration blocker, not “fixed” by weakening CORS.

## Browser environment and exact verification

| Item | Evidence |
|---|---|
| Browser tooling | Existing `microsoft/playwright-mcp` browser tools; no package installation |
| Dev preview | `http://127.0.0.1:3000/`, served by existing `npm run dev` |
| Production-like preview | `http://127.0.0.1:3001/`, built with `VITE_FLASK_API_ORIGIN=http://127.0.0.1:5009` |
| Local Flask | `python -m flask --app run.py run --host 127.0.0.1 --port 5009` |
| Desktop viewport | 1280 × 900 |
| Tablet viewport | 768 × 1024 |
| Mobile viewport | 390 × 844 |
| Motion mode | `prefers-reduced-motion: reduce` exercised |

## Routes and UI surfaces tested

| Surface | Result | Evidence |
|---|---|---|
| Home page | **PASS** | Heading, navigation, marketplace sections, footer, and AI entry rendered |
| Catalog navigation | **PASS / FALLBACK** | Lazy page loaded; visible “Live catalog is unavailable; showing the saved preview catalog.” with one preview product when the origin was not Flask |
| Deals page | **PASS** | “Daily Flash Deals & Exclusive Vouchers” and discounted listings rendered |
| Authentication entry | **PASS** | “NexHaat Login” opened a semantic dialog with Sign in/Register tabs and labeled fields |
| Registration/OTP handoff entry | **PASS by source/UI** | Register tab exposed full name, phone, email, password, and seller store fields; form was not submitted, so no OTP was sent |
| Wishlist | **PASS** | “Your Wishlist”, item cards, and “Move All to Cart” rendered |
| Cart | **PASS** | Empty-cart state, “Shopping Cart”, item count, close control, and “Explore Marketplace” rendered |
| Notifications | **PASS** | “Notifications & Alerts”, filters, and “Mark All Read” rendered |
| AI UI | **PASS / PROVIDER BLOCKED** | AI Studio drawer rendered with chat, voice, transcription, visual, music, and bioscience tabs; provider request returned 500 because no Gemini API key was configured |
| Product detail | **NOT TESTED** | No safe product selection was needed after the catalog fallback/API boundary was identified |
| Checkout/orders | **NOT TESTED** | No authenticated disposable customer session or order fixture was available; no order mutation was attempted |
| Seller/rider/admin portals | **NOT TESTED** | No disposable role accounts were available; UI role switching is not an authorization test |

## Responsive and accessibility checks

**PASS by local browser evidence:**

- Desktop, tablet, and mobile snapshots rendered without horizontal layout
  overflow in the captured viewport bounds.
- Tab navigation reached a button and the browser reported a visible default
  focus outline (`outline-width: 1px`); no focus bypass was introduced.
- Authentication controls exposed labels and a semantic `dialog`.
- Cart used a labeled close button and an empty-state message.
- Images exposed meaningful alt text in snapshots, including product and brand
  imagery.
- The AI panel and loading fallback exposed status/live semantics where
  applicable.
- Reduced-motion emulation was accepted without blocking page rendering.

**NOT TESTED:** screen-reader output, color-contrast measurement, full
keyboard-only completion of every workflow, focus restoration after every modal,
Lighthouse scores, touch gestures, and real-device browser behavior.

## API integration evidence

Read-only direct probes against the local Flask server:

```text
200 GET http://127.0.0.1:5009/health/live
401 GET http://127.0.0.1:5009/api/v1/auth/me
200 GET http://127.0.0.1:5009/api/v1/categories
200 GET http://127.0.0.1:5009/api/v1/products?limit=5&sort=featured
```

The React preview configured for the same Flask origin issued:

```text
GET http://127.0.0.1:5009/api/v1/auth/me
GET http://127.0.0.1:5009/api/v1/categories
GET http://127.0.0.1:5009/api/v1/products?limit=100&sort=featured
```

The browser rejected all three with a CORS error because
`http://127.0.0.1:3001` was not an allowed origin. No CORS control was weakened
to make the test pass. Credentialed auth, CSRF, cart, checkout, orders,
notifications, and role isolation therefore remain **BLOCKED** until an
approved staging origin and policy are available.

The initial dev preview also showed `/api/v1/*` requests returning the Vite SPA
HTML fallback rather than Flask JSON. This confirms that the frontend-only
Express/Vite server is not a substitute for the Flask marketplace API.

## Android compatibility

No Android source or API DTO was changed. The existing Android unit test command
remains the compatibility evidence:

```text
.\android\gradlew.bat -p android :app:test --no-daemon
BUILD SUCCESSFUL in 2m 59s
```

Live Android API/device authentication was **NOT TESTED**. Existing unsigned
release, SDK XML, and Gradle deprecation warnings remain.

## Failures and blockers

- **FAIL / expected local provider gate:** Gemini chat returned HTTP 500 because
  `GEMINI_API_KEY` was not configured; no external provider call was authorized.
- **BLOCKED:** browser React→Flask CORS/session/CSRF verification requires an
  approved staging origin and disposable accounts.
- **BLOCKED:** authenticated checkout, orders, seller/admin authorization, and
  OTP delivery require safe fixtures/providers.
- **NOT TESTED:** production, Azure, real email/SMS, payments, Firebase live
  behavior, and device E2E.

## Final local verification

| Command | Result |
|---|---|
| `npm run lint` | **PASS** — `tsc --noEmit`, exit code 0 |
| `npm run build` | **PASS with existing warning** — Vite build completed; initial `index` chunk 1,017.94 kB and `AdminPortalPage` 471.78 kB remain above the 500 kB warning threshold |
| `python -m pytest -q` | **PASS** — 305 passed in 486.71s |
| `.\android\gradlew.bat -p android :app:test --no-daemon` | **PASS with warnings** — BUILD SUCCESSFUL in 2m 34s; unsigned release, SDK XML, and Gradle deprecation warnings |
| `git diff --check` | **PASS** at final pre-report verification |

## Files changed

Only this report was added for Phase 17. No application, workflow, schema,
authentication, OTP, Android, or provider code was changed.
