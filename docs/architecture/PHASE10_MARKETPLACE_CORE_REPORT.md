# NexHaat Phase 10 — Marketplace Core Integration Report

**Status:** PARTIAL — catalog/cart/wishlist integration added; full marketplace E2E remains unverified  
**Date:** 2026-11-01  
**Branch/HEAD:** `main` / `dec15ac458a59a0dd0a6d3dda19727bb8cd7a699`

## Executive summary

The preferred Google AI Studio React UI now has an additive bridge to the existing Flask marketplace catalog. On startup it requests the real categories and featured product listing through `/api/v1/categories` and `/api/v1/products?limit=100&sort=featured`. The existing UI, filters, search controls, cards, animations, and local preview data remain intact. If Flask is unavailable or returns no usable listing, the previous local/mock catalog remains visible and the UI reports that fallback.

Authenticated customers also synchronize add/update/remove cart operations and add/remove wishlist operations with existing Flask APIs. The backend remains authoritative for availability, stock, price, customer role, and authorization. Checkout/payment/order execution was not changed.

## Baseline and preserved functionality

The worktree was already dirty before editing with many user and generated files. No unrelated file was reverted or deleted. Existing React pages, Firebase, Express, Flask routes, database models, migrations, Android contracts, and server-rendered pages were preserved. No production operation occurred.

## Existing Flask API mapping

| Feature | Existing endpoint | React integration | Status |
|---|---|---|---|
| Categories | `GET /api/v1/categories` | `fetchMarketplaceCatalog` | PASS locally by contract |
| Product listing/search/filter backend | `GET /api/v1/products` with `q`, `category_id`, price, stock, rating, discount, sort, page, limit | Initial live listing is fetched; existing React controls still filter loaded data | PARTIAL |
| Product detail | `GET /api/v1/products/<id>` | Existing detail UI still uses context product | NOT TESTED as a separate fetch |
| Cart add | `POST /api/v1/cart/items` | Customer `addToCart` sync | PASS by contract/tests |
| Cart update | `PATCH /api/v1/cart/items/<product[:variant]>` | Customer quantity update sync | PASS by contract/tests |
| Cart remove | `DELETE /api/v1/cart/items/<product[:variant]>` | Customer remove sync | PASS by contract/tests |
| Wishlist list | `GET /api/v1/wishlist` | Customer session initialization | PASS by contract |
| Wishlist add/remove | `POST /api/v1/wishlist/items`, `DELETE /api/v1/wishlist/items/<id>` | Customer toggle sync | PASS by contract |
| Checkout/orders/payments | Existing `/api/v1/checkout`, `/api/v1/orders`, payment routes | Not changed | NOT TESTED in browser; intentionally out of scope |

The API serializer returns fixed-precision money strings. The adapter converts those strings to display numbers only at the UI boundary; Flask remains authoritative for calculations. Fields absent from the current serializer (seller display name, rating, Bengali-specific text, unit) receive clearly non-authoritative display defaults so the existing component contract remains usable.

## Files created or modified

- [`src/lib/marketplaceApi.ts`](../../src/lib/marketplaceApi.ts) — typed API envelope, product/category mapping, catalog/cart/wishlist calls.
- [`src/context/AppContext.tsx`](../../src/context/AppContext.tsx) — live catalog replacement when available, preview fallback, customer server synchronization.
- [`src/pages/CatalogPage.tsx`](../../src/pages/CatalogPage.tsx) — loading and fallback status messages.

No Flask model, schema, migration, route, payment, checkout, or Android file was changed.

## Feature-preservation matrix

| Capability | Status | Evidence / limitation |
|---|---|---|
| AI Studio visual design and reusable components | PASS | Existing pages/components retained; only status messages and data source bridge added |
| Real product listing | PARTIAL | Live listing request added; browser/staging API response not run |
| Search, filtering, sorting | PARTIAL | Existing UI behavior remains; server query parameters are available but the initial client fetch is capped at 100 |
| Pagination/load-more | NOT TESTED | No new pagination control was invented |
| Product details/images/fallback | PARTIAL | API image/display_image mapped; separate detail fetch not added |
| Cart persistence | PARTIAL | Customer mutations sync; initial server-cart hydration and clear-cart sync remain |
| Wishlist persistence | PASS by contract / NOT TESTED browser | Customer list and mutations are wired; staging cookie flow remains |
| Checkout/payment/orders | PRESERVED / NOT TESTED | No order or payment was created or changed |
| Seller ownership and stock | PASS server-side | Existing Flask guards/services remain authoritative |

## Test evidence

- `npm run lint` — **PASS**, exit code 0.
- `npm run build` — **PASS**, exit code 0; existing large chunk warning.
- `FLASK_TESTING=1 python -m pytest tests\test_auth.py tests\test_api_foundation.py tests\test_catalog.py tests\test_wishlist.py tests\test_orders.py -q` — **PASS**, 103 passed in 800.38s, exit code 0.
- `git diff --check` — **PASS**.
- Local frontend HTTP 200 — previous Phase 8 **PASS**; this phase did not claim it as an authenticated API test.
- Browser catalog against Flask — **NOT TESTED**.
- Real checkout/payment/inventory mutation — **NOT TESTED** and intentionally not initiated.

## Security and compatibility

- **PASS:** No client total, price, or stock is sent as authoritative checkout data.
- **PASS:** Mutating calls use Flask CSRF token and credentialed cookies.
- **PASS:** Guest users retain local preview/cart behavior; customer server sync is gated by the verified Flask session role.
- **PARTIAL:** A live deployment must provide compatible origin/CORS/cookie settings; no production settings were changed.
- **RISK:** The current API serializer lacks seller/rating/localized fields expected by the rich AI Studio cards. The adapter uses safe display defaults; a future additive serializer extension is preferable to inventing client data.
- **RISK:** The initial listing is limited to 100 products; large catalogs need a reviewed pagination/load-more bridge before claiming completeness.

## Rollback and recommended next steps

Rollback by removing only [`src/lib/marketplaceApi.ts`](../../src/lib/marketplaceApi.ts), its imports/effects in [`src/context/AppContext.tsx`](../../src/context/AppContext.tsx), and the status block in [`src/pages/CatalogPage.tsx`](../../src/pages/CatalogPage.tsx). This restores the existing local preview behavior without touching Flask or Firebase.

Next phases should:

1. Use an approved staging environment to validate browser catalog/auth/cart/wishlist flows with mock providers.
2. Add a typed paginated catalog query and server-cart hydration after confirming the deployed API contract.
3. Only then integrate product-detail reviews and checkout preview; do not initiate real payment during validation.

