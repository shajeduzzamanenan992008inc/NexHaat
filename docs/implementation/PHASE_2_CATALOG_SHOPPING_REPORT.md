# Phase 2 — Catalog and Customer Shopping Foundation

**Date:** 2026-11-04
**Scope:** Development-only catalog data, backend-driven catalog, product detail, cart,
disposable COD checkout, order history/detail, review rules, low-risk performance and
PWA review, browser verification.
**Status:** Implementation complete for the stated scope. Nothing was committed,
pushed, deployed, migrated to production, or charged.

---

## 1. Outcome summary

| Requirement | Result | Evidence |
|---|---|---|
| Development-only catalog data | **PASS** | `app/seed_dev.py`, 16 fixtures, guarded and idempotent; `tests/test_dev_seed.py` |
| Catalog fully backend-driven | **PASS** | Search, category, price, in-stock, discount, rating (real data only), backend sort, pagination, loading/empty/error/retry |
| Product detail | **PASS** | Real price/discount, stock, store name, variants on supported fixtures, image fallback, honest review summary |
| Cart | **PASS** | Add, update quantity, remove, stock rejection, server-authoritative price/subtotal, empty state |
| Disposable COD checkout | **PASS** | Order `FB-F8FA6C5F34E5486E94B47F943496D449-1`, ৳447.00 items + ৳2.50 delivery = ৳449.50, `payment_status: null` (COD pending) |
| Order history and detail | **PASS** | `My Orders` shows the real order, timeline, address, COD pending |
| Review behavior | **PASS** | Empty state honest; submission refused with the backend rule "You can review a product after your order is delivered." |
| Mobile layout | **PARTIAL** | Home, catalog and detail verified at 390×844; mobile checkout/review not driven |
| Performance | **PASS (partial scope)** | Entry chunk 1,074.18 kB → 238.55 kB; vendor chunks remain large |
| PWA development output | **PASS** | `devOptions` now opt-in (`VITE_PWA_DEV`), so `vite dev` no longer writes `dev-dist/` by default |

---

## 2. Environment and isolation

| Item | Value |
|---|---|
| Workspace | `D:\FTP\NexHaat` (branch `main`, HEAD `19d027eb…`) |
| Flask | `127.0.0.1:5000`, `APP_ENV=development` |
| Vite | `127.0.0.1:3010`, same-origin proxy to Flask |
| Browser | Headless Chrome over CDP `127.0.0.1:9222` |
| Desktop viewport | 1440×1000 |
| Mobile viewport | 390×844 |
| Database | Disposable SQLite `C:/Users/enan9/AppData/Local/Temp/nexhaat-phase2-dev.sqlite3` |

The application database was never pointed at a production or shared database. The only
migration run was `flask --app run.py db upgrade` against the disposable SQLite file.
No real payment gateway, SMTР/Telegram, mail or storage provider was contacted.

### 2.1 Development-origin finding (root cause of an initially "unavailable" catalog)

The first browser run showed "Live catalog connection is unavailable" even though
`curl` through the Vite proxy returned 200. The cause was configuration, not app code:
the dev server was started with `VITE_FLASK_API_ORIGIN=http://127.0.0.1:5055`, and
`src/lib/flaskAuth.ts` uses that same value as the **browser** API origin. The page at
`:3010` therefore requested `:5055` cross-origin, which Flask does not allow with
credentials, so the fetch failed with `Failed to fetch`. The Vite proxy was bypassed.

**Working local configuration:** leave `VITE_FLASK_API_ORIGIN` unset for the browser,
run Flask on the proxy's default port `5000`, and let the same-origin `/api` proxy
forward requests. This is the configuration used for every result below. A future,
low-risk follow-up would separate "proxy target" from "browser API origin" so the two
cannot conflict.

---

## 3. Files changed

| File | Purpose |
|---|---|
| `app/seed_dev.py` *(new)* | Guarded, idempotent development fixture seeder |
| `public/dev-fixture-placeholder.svg` *(new)* | Labelled placeholder used by fixture listings |
| `app/services/reviews.py` | `rating_summaries()` — approved-only rating aggregates, batched |
| `app/services/stores.py` | `store_names_for_sellers()` — one query for real store names |
| `app/api/serializers.py` | `product_to_dict(..., seller_name=None)`; rating/seller omitted unless supplied |
| `app/api/routes/catalog.py` | Batched rating + store-name lookups in listings and detail |
| `src/lib/marketplaceApi.ts` | Cart adapters; real `seller_name`; no synthetic SKU |
| `src/context/AppContext.tsx` | Server-cart reconciliation after customer sign-in; async `clearCart` |
| `src/pages/CatalogPage.tsx` | Server-side filters/sort/pagination; error state with in-place **Retry** |
| `src/pages/ProductDetailPage.tsx` | Correct product lookup, not-found UI, image fallback, honest seller/SKU/review display |
| `src/components/ProductCard.tsx` | Image fallback |
| `src/components/ProductReviewsSection.tsx` | Zero-review summary without fabricated stars/averages |
| `src/components/CartDrawer.tsx` | Seller line only when a real store name exists |
| `src/App.tsx` | Catalog-unavailable notice with **Retry** |
| `vite.config.ts` | PWA dev output opt-in; vendor chunk split |
| `tests/test_dev_seed.py` *(new)* | Fixture safety, idempotency, refusal and content tests |
| `tests/test_customer_journey.py` *(new)* | Catalog → cart → COD → order → review journey over the real API |
| `tests/test_customer_journey.py` | Asserts real store name in listing and detail |
| `docs/assets/phase2/*.png` *(new)* | Browser screenshots referenced in this report |

`tests/test_reviews.py` appears modified in the working tree; it was not edited in this
phase and is treated as pre-existing user work.

---

## 4. Development fixture strategy

- Seller: `dev-seller@nexhaat.test`, store **"NexHaat Dev Store (Test Listings)"**,
  role `seller`, active, with an approved seller profile.
- 16 products across electronics, foods, home, stationery, apparel and personal care.
  Slugs are prefixed `dev-fixture-` so they are identifiable in any database.
- Variants on `dev-fixture-basmati-rice` (1 kg / 5 kg with distinct prices and stock);
  one deliberately discounted fixture (`dev-fixture-red-lentil-1kg`, ৳149.00 from
  ৳165.00) and one deliberately sold-out fixture (`dev-fixture-instant-coffee-100g`).
- **No** invented ratings, reviews, sales counts or popularity metrics. Ratings appear
  only when approved reviews exist; fixtures start with none.
- Images use `/dev-fixture-placeholder.svg`, a labelled "development fixture" artwork,
  rather than fabricated product photography.
- Idempotent: products are matched by slug and variants by SKU, so re-running updates
  instead of duplicating.
- Safety: the seeder refuses to run unless `APP_ENV` is `development`/`testing`, the
  database is SQLite, the store is clearly a test store, and `--confirm` is supplied.
  It also refuses to convert an existing non-seller account.
- Production seed behaviour (`app/seed.py`) was not modified.

Commands used:

```bash
DATABASE_URL="sqlite:///C:/Users/enan9/AppData/Local/Temp/nexhaat-phase2-dev.sqlite3" \
APP_ENV=development flask --app run.py db upgrade      # exit 0
python -m app.seed_dev --confirm                        # "Development fixtures ready: 16 test products"
```

---

## 5. Catalog

All listing behaviour is requested from Flask; the frontend does not invent catalog data.

- Search (debounced, `q`), category navigation (`/categories/<slug>`), price range
  (`min_price`/`max_price`), availability (`in_stock`), discounts (`discount`), rating
  (`min_rating`, only when real approved ratings exist), sort (`featured`, `relevance`,
  `newest`, `price_asc`, `price_desc`), and paging (`page`/`limit`).
- Loading skeleton text, empty state with reset, and an error state with **Retry** that
  re-issues the request in place. The app-level notice also offers Retry.
- Verified in browser: 16 products, "Out of Stock" badge on the sold-out fixture,
  discount badges with real percentages, search "Miniket" → exactly 1 listing, and
  `discount + in_stock + ৳140–700` → exactly 2 listings.

---

## 6. Product detail, cart, checkout, orders, reviews

- **Detail:** real price/discount, `In Stock (n)` from live stock, store name from
  `SellerProfile.store_name`, variants where defined, placeholder image fallback, and a
  not-found state instead of silently showing another product.
- **Cart:** add/update/remove through the existing cart architecture; quantity bounds and
  stock are validated by Flask (`422` for out-of-range, `409 OUT_OF_STOCK`); subtotal is
  computed from server prices. Signed-in customers reconcile their browser cart with the
  server cart once per session.
- **Checkout:** address form + standard delivery + COD; the server recalculates prices,
  delivery fee and totals. Observed order: items ৳447.00, delivery ৳2.50, total ৳449.50,
  status `Pending`, payment `COD (PENDING)`. No redirect is treated as payment success.
- **Orders:** history lists the order with backend total; details show timeline, address
  and payment state.
- **Reviews:** section starts empty with `—` and 0% bars (no fabricated stars); submission
  is refused by the server for an undelivered order and the message is shown verbatim.
  Moderation-gated publication is covered by Python tests.

Inventory evidence: the fixture stock dropped from 35 to 32 after ordering 3 units,
matching the server-side decrement.

---

## 7. Browser journey results

| # | Step | Result | Screenshot |
|---|---|---|---|
| 1 | Open home | PASS | `01-home-desktop.png` |
| 2 | Navigate to catalog | PASS | `02-catalog-desktop.png` |
| 3 | Search seeded product | PASS — "Miniket" → 1 result | temp `03-search-desktop.png` |
| 4 | Apply filters | PASS — discount + stock + ৳140–700 → 2 results | `03-catalog-filters-desktop.png` |
| 5 | Open product detail | PASS — real store, ৳149 vs ৳165, 35 in stock | `04-product-detail-desktop.png` |
| 6 | Change quantity | PASS — 1 → 3 | — |
| 7 | Add to cart | PASS — 3 × ৳149 = ৳447.00 | — |
| 8 | Update and remove cart items | PASS — ৳298.00 then empty state | temp `07-cart-empty.png` |
| 9 | Disposable COD checkout | PASS — ৳449.50, COD pending | `05-checkout-desktop.png`, `06-order-confirmation-desktop.png` |
| 10 | Open order details | PASS | temp `12-order-details.png` |
| 11 | Review workflow | PASS — empty state + server refusal for undelivered order | `07-reviews-empty-desktop.png` |
| 12 | Empty and error states | PASS — no-match search; catalog error + working Retry | `08-catalog-error-desktop.png`, temp `14-empty-search.png`, `17-catalog-recovered.png` |
| — | Mobile home / catalog / detail | PASS (390×844) | `09-catalog-mobile.png`, `10-product-detail-mobile.png` |

Browser driving used an ad-hoc Node + CDP script in the OS temp directory (no Playwright
is installed in this project). Screenshots are real captures; where a step was not
driven (mobile checkout, mobile review) it is marked PARTIAL rather than PASS.

---

## 8. Verification commands and exact results

| Command | Result |
|---|---|
| `python -m ruff check app/seed_dev.py app/services/stores.py app/services/reviews.py app/api/serializers.py app/api/routes/catalog.py tests/test_dev_seed.py tests/test_customer_journey.py` | All checks passed |
| `python -m pytest tests/test_customer_journey.py tests/test_dev_seed.py tests/test_api_foundation.py tests/test_catalog.py -q` | **36 passed** in 77.15s |
| `python -m pytest tests/test_customer_journey.py -q` (after seller-name change) | 1 passed in 9.29s |
| `npm.cmd run lint` (`tsc --noEmit`) | PASS |
| `npm.cmd run build -- --outDir …/nexhaat-phase2-build2` | PASS, built in 1m 44s |
| `git diff --check` | PASS after removing pre-existing trailing whitespace in `ProductDetailPage.tsx` |
| Full Python suite | **NOT RUN** (targeted suites only) |
| `npm.cmd test` (Node security) | **NOT RUN** this phase |
| Android `:app:testDebugUnitTest` | **NOT RUN** this phase |

---

## 9. Performance findings

- Every route is already `React.lazy`-loaded in `src/App.tsx`; the initial main chunk was
  large because Firebase and Recharts were bundled into it.
- Low-risk change: `build.rollupOptions.output.manualChunks` splits `react`/`react-dom`,
  `firebase` and `recharts` into separate vendor chunks.
- Measured build output after the change:

| Chunk | Size | Gzip |
|---|---|---|
| `index` (entry) | 238.55 kB | 63.83 kB |
| `vendor-charts` | 581.18 kB | 171.14 kB |
| `vendor-firebase` | 690.43 kB | 175.35 kB |
| `ProductDetailPage` | 81.95 kB | 20.72 kB |
| `AdminPortalPage` | 51.05 kB | 12.15 kB |

- Before: main chunk ≈ 1,074.18 kB (gzip 285.09 kB). Vite still warns about the two large
  vendor chunks; further reduction needs deferring Firebase initialisation behind the
  auth UI, which is a behavioural change and was intentionally not attempted.

---

## 10. PWA findings

- `vite-plugin-pwa` writes generated service-worker files into `dev-dist/` when
  `devOptions.enabled` is true. The configuration previously enabled dev output
  unconditionally, so every `vite dev` run could rewrite that untracked directory.
- Change: `devOptions.enabled = env.VITE_PWA_DEV === 'true'`, so development no longer
  generates `dev-dist/` unless a developer opts in. Production builds still emit `sw.js`
  and the Workbox runtime, verified in the build output (47 precache entries).
- The pre-existing `dev-dist/` directory and its backup in the OS temp directory were
  preserved; nothing was deleted or regenerated over the backup.

---

## 11. Known limitations and remaining work

1. Order lines still display the generic label "NexHaat seller" because the order API
   does not serialise a store name; catalog listings and product detail now show the real
   store. Extending the order serializer is an additive follow-up.
2. Pagination was not exercised in the browser because 16 fixtures fit in one 24-item
   page; the "Load more" path is covered only by code and API behaviour.
3. Guest→server cart reconciliation exists but was not observed end-to-end (the cart was
   emptied before sign-in); server cart operations are covered by Python tests.
4. Mobile checkout and mobile review submission were not driven; only layout was checked.
5. The 30-day price-trend widget is explicitly labelled illustrative and uses current
   listing data; no historical price store is connected.
6. `VITE_FLASK_API_ORIGIN` doubles as proxy target and browser API origin; this caused the
   initial false "catalog unavailable" state. Separating the two would prevent recurrence.
7. Full Python, Node security and Android suites were not run in this phase.

---

## 12. Git, deployment and safety

- No commit, push, merge, release or deployment was performed.
- No production database, migration, backup, bucket, webhook or external message was
  touched. No real payment was initiated or simulated as success.
- Pre-existing modified/deleted/untracked work was preserved; `git status` still reports
  the user's earlier changes (196 entries at the end of this phase) alongside the Phase 2
  additions. No destructive Git command was used.
- The disposable SQLite database, browser screenshots and backup directories remain in
  the OS temp directory and are not part of the repository.

## 13. Next bounded task

Separate the browser API origin from the Vite proxy target so local runs cannot silently
switch to cross-origin requests, then extend order serialisation with the seller store
name so order screens stop using a generic label.
