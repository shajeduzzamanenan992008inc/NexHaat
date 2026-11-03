# Phase 55–63 Roadmap Audit (Owner-Supplied Scope)

**Date:** 2026-11-03
**Branch / HEAD:** `main` / `cc0f7fc48d19d38066dcc8b644daa7242bf9ef02`
**Status of every phase:** **Planned.** No item in this document is claimed complete.
**Purpose:** Record the owner's nine-phase roadmap in the canonical plan and map each
of its ~80 items to current repository evidence before any implementation starts.

## Method and honesty rules

- Evidence is the actual source tree: `app/models`, `app/services`, `app/api/routes`,
  `app/routes`, `src/`, and `android/app/src`.
- The authoritative persistence inventory was read from `__tablename__` declarations,
  not inferred from UI labels.
- Status vocabulary used below:
  - **Present** — a working, server-authoritative implementation exists with tests or
    verified call sites.
  - **Partial** — something related exists, but it does not yet satisfy the item as
    written (missing workflow, UI, persistence, or verification).
  - **Absent** — no implementation was found.
- A **Present** label means the capability exists; it does not mean it satisfies the
  stricter acceptance gate of the new phase, and it is not a completion claim.
- Items marked Partial/Absent are proposals, not promises. Each implementation must be
  approved and delivered as a bounded slice with tests.

### Persistence inventory observed

`account_invitations`, `addresses`, `admin_login_challenges`, `admins`, `ai_preferences`,
`ai_request_windows`, `app_settings`, `audit_events`, `auth_throttles`, `banners`,
`categories`, `customer_cart_items`, `customers`, `fdc_*` (reference data),
`notifications`, `order_items`, `order_returns`, `orders`, `outbound_emails`,
`payment_attempts`, `payment_refunds`, `payments`, `phone_otp_challenges`,
`phone_otp_throttles`, `processed_telegram_updates`, `product_translations`,
`product_variants`, `products`, `promotion_codes`, `promotion_redemptions`,
`recently_viewed_products`, `registration_challenges`, `review_helpful_votes`,
`review_reports`, `reviews`, `rider_profiles`, `seller_ledger_entries`,
`seller_payouts`, `seller_profiles`, `support_conversations`, `support_messages`,
`telegram_*`, `users`, `wishlist_items`.

Notable absences: no order-event/history table, no tax table or setting, no currency
table, no KYC document table, no product-question table, no saved-collection table,
no seller-performance table, no job-queue table beyond the email outbox.

---

## Phase 55 — Marketplace Core Upgrade

| # | Item | Status | Evidence / gap |
|---|---|---|---|
| 1 | Advanced search + autocomplete | **Present** | `app/services/catalog.py` weighted relevance over name/brand/category/description/translations + Bangla–Latin transliteration; `app/repositories/catalog.py`; `/api/search-suggestions`; accessible suggestion dropdown |
| 2 | Smart filters — price, category, brand, rating, availability | **Present** | Facets in `app/services/catalog.py` + `app/api/routes/catalog.py`: category, brand, price range, minimum rating, on-sale, availability; pagination preserves active filters |
| 3 | Product comparison | **Present** | `src/components/ComparisonBar.tsx` plus the AI comparison tool (`app/ai/marketplace_tools.py`); no persisted comparison list |
| 4 | Product variants — size, color, model | **Present** | `product_variants` table, `ProductVariant` model, `variant_id` threaded through cart, checkout, and API serializers |
| 5 | Wishlist and saved collections | **Partial** | Wishlist is complete (`wishlist_items`, `app/services/wishlist.py`, `/api/v1` route, `WishlistPage.tsx`). **Saved collections are Absent** — no collection table, service, or UI |
| 6 | Recently viewed products | **Present** | `recently_viewed_products`, `app/services/recent_views.py`, customer-scoped, trimmed, availability-filtered, rendered on the homepage |
| 7 | Product recommendations | **Present** | `app/services/recommendations.py` (frequently-bought-together, cross-sell, personalized), `GET /api/v1/products/{id}/recommendations` |
| 8 | Inventory and stock reservation | **Partial** | Checkout reserves stock transactionally with `with_for_update` and releases it on payment expiry (`app/services/checkout.py`, `app/services/payments.py`). **Absent:** time-boxed cart-level holds and reservation visibility |
| 9 | Coupon, discount and campaign engine | **Present** | `promotion_codes`, `promotion_redemptions`, `app/services/promotions.py`, Admin campaign UI, seller deals, server-side validation + redemption snapshots |
| 10 | Order tracking timeline | **Present** (delivered 2026-11-03) | `order_events` table + migration `20261103_01`, `app/services/order_timeline.py`, hooks at every status writer, owner-scoped timeline endpoints, customer/admin/React timelines. Android UI remains outstanding |

**Phase 55 conclusion:** 8 of 10 items present (order tracking timeline delivered
2026-11-03), 2 partial (saved collections, cart-level reservation).

## Phase 56 — Seller Center Pro

| # | Item | Status | Evidence / gap |
|---|---|---|---|
| 1 | Seller analytics dashboard | **Partial** | AI seller insights (`app/ai/seller.py`, `app/ai/seller_tools.py`, `templates/ai/seller.html`); no deterministic analytics service, charting, or export |
| 2 | Bulk product upload | **Absent** | No bulk product entry path found |
| 3 | Product import/export | **Absent** | No product CSV/JSON import or export; `app/services/food_data_import.py` is reference-data tooling, not seller catalog import |
| 4 | Inventory alerts | **Partial** | Low-stock signals inside AI insights only; no seller alert record, badge, or notification workflow |
| 5 | Order management dashboard | **Present** | `app/routes/seller.py`, seller-scoped order views, status transitions, invoices |
| 6 | Return/refund management | **Present** | `order_returns`, seller review/receipt actions, Admin queue, ledger reversals (Stage 8) |
| 7 | Seller performance metrics | **Partial** | No performance persistence (fulfilment rate, response time, cancellation rate); rating exists but not a metrics surface |
| 8 | Commission and payout reports | **Present** | `seller_ledger_entries`, `seller_payouts`, commission snapshots, Admin reconciliation/payout records |
| 9 | Product approval workflow | **Present** | `approval_status`, moderation, seller-created listing visibility gated server-side |
| 10 | Seller verification / KYC | **Partial** | Seller approval status exists; no KYC document capture, private storage, review, or expiry workflow |

**Phase 56 conclusion:** 4 present, 4 partial, 2 absent.

## Phase 57 — Customer Experience

| # | Item | Status | Evidence / gap |
|---|---|---|---|
| 1 | Advanced checkout | **Present** | `app/services/checkout.py`: variants, promotions, multi-seller split, COD + SSLCOMMERZ, server-authoritative totals |
| 2 | Guest checkout | **Present** | Guest cart/checkout with a signed confirmation grant; staff sessions denied on guest confirmations |
| 3 | Multiple delivery addresses | **Partial** | `addresses` table + `CustomerAddress` model exist; checkout still collects a free-text address per order, so saved-address selection is not verified end-to-end |
| 4 | Shipping cost calculator | **Partial** | Flat `DELIVERY_FEE = Decimal("2.50")`; no zone/weight/quantity calculation |
| 5 | Order cancellation rules | **Present** | Unshipped-cancellation rules and provider refunds (`app/services/payments.py`, `app/services/orders.py`) |
| 6 | Return and refund request tracking | **Present** | Stage 8 customer/seller/Admin flows, statuses, refund references |
| 7 | Verified purchase reviews | **Present** | `Review.order_id` + unique constraint per product/user/order; moderation; helpful votes; abuse reports |
| 8 | Product Q&A | **Absent** | No product-question model, route, or moderated answer UI |
| 9 | Customer support ticket system | **Present** | `support_conversations` / `support_messages`, `app/routes/support.py`, statuses open/pending/closed. Chat-style rather than SLA ticketing |
| 10 | Email / SMS / Telegram notifications | **Present** | `mail.py`, `sms.py` + adapters, `telegram_alerts.py`, `notifications.py`, `outbound_emails` outbox |

**Phase 57 conclusion:** 7 present, 2 partial, 1 absent.

## Phase 58 — NexHaat AI Intelligence

Stage 12 is recorded as complete in application code with scoped, server-selected AI.

| # | Item | Status | Evidence / gap |
|---|---|---|---|
| 1 | AI shopping assistant | **Present** | `app/ai/`, `/ai/chat`, customer tools |
| 2 | Natural-language product search | **Present** | Deterministic multilingual fallback + AI filter extraction |
| 3 | Bangla voice search | **Partial** | Validated voice/audio path exists; Bangla recognition quality and browser/device coverage unverified |
| 4 | AI product descriptions for sellers | **Present** | Seller drafts with mandatory review before save |
| 5 | AI product categorization | **Present** | Seller-reviewed category/tag drafts |
| 6 | Personalized recommendations | **Present** | `app/services/personalization.py` + AI preferences |
| 7 | AI review summarization | **Present** | Approved-reviews-only summary tool |
| 8 | AI customer support | **Present** | Scoped assistant + human support escalation |
| 9 | Seller business insights | **Present** | Seller-owned sales/stock/pricing insights |
| 10 | Fraud/risk signals with human review | **Present** | Admin review-risk flags and Security read-only tools; humans decide |

**Phase 58 conclusion:** 9 present, 1 partial. Remaining work is verification depth,
not new architecture.

## Phase 59 — Security and Trust

| # | Item | Status | Evidence / gap |
|---|---|---|---|
| 1 | Role-based access control audit | **Partial** | Server-side role checks throughout `app/security.py` and route guards; no exhaustive, recorded route-by-route authorization matrix for this phase |
| 2 | OTP abuse protection | **Present** | `phone_otp_throttles`, `auth_throttles`, failed-attempt limits, resend cooldowns, OTP expiry |
| 3 | Session/device management | **Partial** | `auth_version` session revocation and active-account checks; no device/session list, naming, or revoke-one UI |
| 4 | Rate limiting | **Present** | `auth_throttles`, `telegram_rate_limits`, `ai_request_windows`, Express per-process controls |
| 5 | Audit logs | **Present** | `audit_events` + `record_audit` across auth, orders, payments, returns, admin |
| 6 | Payment webhook verification | **Present** | SSLCOMMERZ server-side IPN validation, idempotent, never trusts a redirect |
| 7 | Upload scanning and file validation | **Present** | Private quarantine, malware scan, decode/re-encode, fail-closed media pipeline |
| 8 | Privacy export/delete workflow | **Partial** | Account deletion route + confirmation UI exist; **no customer data export** |
| 9 | Backup and restore testing | **Partial** | Backup/restore CLI with target confirmation and SQLite online backup; no scheduled automated verification |
| 10 | Security regression tests | **Present** | Negative-path auth, ownership, guest-confirmation, rate-limit, and webhook tests inside the 306-test suite |

**Phase 59 conclusion:** 6 present, 4 partial. This phase is audit-and-harden, not
greenfield.

## Phase 60 — Performance and Reliability

| # | Item | Status | Evidence / gap |
|---|---|---|---|
| 1 | Redis caching | **Absent** | Zero Redis/cache references. Introducing it means a new external service → requires explicit approval |
| 2 | Database query optimization | **Partial** | Composite discovery indexes (`20261010_27`), bounded queries; no profiling evidence or measurement recorded |
| 3 | Background job queue | **Partial** | `outbound_emails` outbox for mail; no general-purpose worker/queue for long or scheduled jobs |
| 4 | Image optimization and CDN | **Partial** | Private media pipeline + re-encode; CDN delivery remains an operator gate |
| 5 | API pagination | **Present** | `/api/v1` pagination with bounded page size; web `rel="prev"/"next"` |
| 6 | Database connection pooling | **Partial** | Pool settings exist in `app/config.py`; behavior under concurrent load unverified |
| 7 | Health/readiness endpoints | **Present** | `app/api/routes/health.py`, separate liveness/readiness, DB-failure regression |
| 8 | Error monitoring | **Absent** | No APM/error-tracking integration; structured logs only. Adding a provider requires approval |
| 9 | Automated backup verification | **Partial** | Backup tooling + restore confirmation; no automated verification job or alert |
| 10 | Load and stress testing | **Absent** | No load-test harness or recorded results |

**Phase 60 conclusion:** 2 present, 5 partial, 3 absent. Any measurement claim must be
a recorded before/after, per repository policy.

## Phase 61 — Android App Upgrade

| # | Item | Status | Evidence / gap |
|---|---|---|---|
| 1 | Native push notifications | **Absent** | No FCM/Firebase Messaging integration in `android/app/src` |
| 2 | Deep links | **Absent** | No intent filters / navigation deep links |
| 3 | Offline product browsing cache | **Absent** (Android) | Web PWA has `OfflineIndicator`/online status; no Android offline catalog cache |
| 4 | Cart synchronization | **Partial** | Retrofit cart endpoints exist; offline reconciliation not implemented or verified |
| 5 | Secure authentication | **Present** | Cookie persistence + CSRF interception + Retrofit DTO contract; no embedded WebView auth |
| 6 | Camera-based product search | **Absent** (Android) | Web image search exists in the AI layer; no camera capture pipeline on device |
| 7 | Order tracking | **Partial** | Orders screens exist; blocked on the missing order-timeline history (Phase 55 #10) |
| 8 | App performance monitoring | **Absent** | No APM/trace integration |
| 9 | Accessibility improvements | **Partial** | Compose semantics present in screens; no recorded TalkBack/font-scale audit |
| 10 | Release signing and automated Android tests | **Partial** | Unit-test task exists (`:app:testDebugUnitTest`); signing material must stay out of Git, so a store artifact was never produced here |

**Phase 61 conclusion:** 1 present, 4 partial, 5 absent.

## Phase 62 — Professional UI/UX

| # | Item | Status | Evidence / gap |
|---|---|---|---|
| 1 | Smooth page transitions | **Partial** | Some animation/3D interactions exist; no systematic transition system |
| 2 | Loading skeletons | **Partial** | `ProductGridSkeleton.kt` + Compose screens; inconsistent on web |
| 3 | Micro-interactions | **Partial** | Neumorphic 3D tilt/flip and hover states exist |
| 4 | Responsive layouts | **Present** | Existing responsive web layouts and Android adaptive screens |
| 5 | Dark/light themes | **Partial** | Theme handling in `Navbar.tsx` / `AppContext.tsx`; full dark-theme coverage unverified |
| 6 | Accessible components | **Partial** | Accessible search combobox, focus states, labels; no repository-wide audit |
| 7 | Consistent design system | **Present** | Tailwind tokens, neumorphic surfaces, shared components — must be extended, never replaced |
| 8 | Reduced-motion support | **Partial** | Reduced-motion handling referenced in the design rules; coverage not systematically verified |

**Phase 62 conclusion:** 2 present, 6 partial. This is polish work on an existing design
system, and the repository forbids replacing that system with an unrelated template.

## Phase 63 — International Marketplace Readiness

| # | Item | Status | Evidence / gap |
|---|---|---|---|
| 1 | Multi-currency architecture | **Absent** | No currency setting; BDT is the only currency (no `CURRENCY` config) |
| 2 | Multi-language support | **Present** | Flask-Babel, `SUPPORTED_LOCALES` (English/Bangla/Hindi), translated catalog rows |
| 3 | Country-based shipping rules | **Absent** | Flat delivery fee; no country/zone rules |
| 4 | Tax configuration | **Absent** | No tax/VAT configuration in models, services, or config |
| 5 | Regional payment adapters | **Partial** | SSLCOMMERZ (Bangladesh) + COD; no abstraction for additional regions |
| 6 | International address formats | **Absent** | `addresses` model is Bangladesh-shaped (city/phone rules) |
| 7 | Localization testing | **Partial** | Locale fallback tests exist; no per-locale UI/interpolation sweep |
| 8 | Multi-region deployment planning | **Absent** | Single Azure App Service target; no multi-region plan |

**Phase 63 conclusion:** 1 present, 2 partial, 5 absent. Money, tax, and payment changes
are high-impact and require explicit owner decisions before any code is written.

---

## Aggregate picture

| Phase | Present | Partial | Absent |
|---|---|---|---|
| 55 Marketplace core | 8 | 2 | 0 |
| 56 Seller Center Pro | 4 | 4 | 2 |
| 57 Customer experience | 7 | 2 | 1 |
| 58 AI intelligence | 9 | 1 | 0 |
| 59 Security and trust | 6 | 4 | 0 |
| 60 Performance and reliability | 2 | 5 | 3 |
| 61 Android upgrade | 1 | 4 | 5 |
| 62 Professional UI/UX | 2 | 6 | 0 |
| 63 International readiness | 1 | 2 | 5 |
| **Total (~80 items)** | **40** | **30** | **16** |

Roughly half of the supplied roadmap already exists in some form. The value of this
audit is that it prevents re-building working features, and points implementation at
the 17 genuinely absent items plus the 30 that are materially incomplete.

## Recommended first bounded slices

Ordered by user value, dependency, and blast radius. Each is a separate change with
its own migration (where needed), tests, and acceptance evidence.

1. ~~**Order tracking timeline (Phase 55 #10)**~~ — **delivered 2026-11-03** (see
   [`ORDER_TRACKING_PHASE2_IMPLEMENTATION_REPORT.md`](ORDER_TRACKING_PHASE2_IMPLEMENTATION_REPORT.md)).
   Remaining follow-up: Android timeline UI.
2. **Saved collections (Phase 55 #5)** — extends the existing `wishlist_items` model
   with customer-scoped named collections; no new authorization model.
3. **Seller analytics dashboard + performance metrics (Phase 56 #1, #7)** — uses
   existing orders/ledger data; must stay owner-scoped and read-only.
4. **Product Q&A with moderation (Phase 57 #8)** — mirrors the existing review
   moderation contract (pending → approved/rejected).
5. **Privacy data export (Phase 59 #8)** — completes the existing delete-account path
   with an owner-only, redacted export.

Items deliberately deferred pending explicit decisions: Redis, error-monitoring/APM
provider, background queue, multi-currency, tax, and multi-region deployment. Each adds
an external service, a financial rule, or an infrastructure change that the repository
requires approval for.

## What this document does not do

- It does not implement any phase item.
- It does not change any stage status in the master plan; all nine phases are recorded
  as **Planned**.
- It does not assert that a Present item meets the stricter new acceptance gate.
- It does not claim any CI or remote verification for future work.
