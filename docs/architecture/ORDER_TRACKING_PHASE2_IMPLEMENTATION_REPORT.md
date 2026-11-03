# Order Tracking Timeline — Phase 2 Implementation Report

**Date:** 2026-11-03
**Branch / baseline HEAD:** `main` / `cc0f7fc48d19d38066dcc8b644daa7242bf9ef02`
**Design:** [ORDER_TRACKING_PHASE1_AUDIT_AND_DESIGN.md](ORDER_TRACKING_PHASE1_AUDIT_AND_DESIGN.md)
**Scope:** Order tracking timeline only. Flask remains authoritative.

## 1. Files created

| File | Purpose |
|---|---|
| `app/services/order_timeline.py` | Record (idempotent), chronological read, latest-tracking lookup, ISO estimate validation |
| `migrations/versions/20261103_01_order_events.py` | Additive `order_events` table + 3 indexes; documented manual rollback |
| `tests/test_order_timeline.py` | 10 focused tests (recording, idempotency, stock release, scoping, serializer, checkout) |
| `docs/architecture/ORDER_TRACKING_PHASE1_AUDIT_AND_DESIGN.md` | Phase 1 deliverable |
| `docs/architecture/ORDER_TRACKING_PHASE2_IMPLEMENTATION_REPORT.md` | This report |
| `docs/architecture/ORDER_TRACKING_PHASE3_VERIFICATION_REPORT.md` | Phase 3 deliverable |

## 2. Files modified

| File | Change |
|---|---|
| `app/models/order.py` | Added `OrderEvent` model, `ORDER_EVENT_TYPES`/`ORDER_EVENT_ACTOR_ROLES`, and `Order.events` relationship |
| `app/models/__init__.py` | Exported `OrderEvent` and the two constant tuples |
| `app/services/orders.py` | `transition_order(..., actor=, description=, actor_role=)` records a `status` event inside the same transaction |
| `app/services/checkout.py` | Records one `created` event per seller sub-order, inside the checkout transaction |
| `app/services/payments.py` | Records `payment` (provider confirmation), `return` (provider refund, manual COD refund); forwards `actor`/`reason` into cancellation transitions |
| `app/routes/portals.py` | Records `delivery` events for every accepted rider transition and the `status` event on delivery |
| `app/routes/seller.py` | Passes the seller as the timeline actor |
| `app/api/routes/commerce.py` | Actor forwarding; new customer + seller timeline endpoints; validated tracking metadata on seller order update |
| `app/api/routes/admin.py` | Passes the admin as the timeline actor |
| `app/routes/orders.py` | Supplies timelines to the customer confirmation page and the admin order detail page; actor on admin status/bulk updates |
| `app/api/serializers.py` | `order_event_to_dict` (no `actor_id`, no internal metadata) |
| `app/templates/orders/confirmation.html` | Customer-facing chronological timeline per seller sub-order |
| `app/templates/admin/order_detail.html` | Admin timeline section with actor role and shipment data |
| `src/lib/marketplaceApi.ts` | `fetchMarketplaceOrderTimeline`, `OrderTimelineEvent` type |
| `src/pages/MyOrdersPage.tsx` | Lazy timeline load on order expansion with loading/empty/error states |

## 3. Database and migration

- Revision `20261103_01`, `down_revision = 20261031_01` → still a **single head**.
- Creates only `order_events` plus `ix_order_events_order_id`, `ix_order_events_created_at`, `ix_order_events_order_created`.
- Foreign keys: `order_id → orders.id ON DELETE CASCADE`, `actor_id → users.id ON DELETE SET NULL`.
- Constraints: `ck_order_event_type_valid`, `ck_order_event_actor_role_valid`, `uq_order_event_dedupe (order_id, dedupe_key)`.
- No existing column, table, index, or row is altered. Automatic downgrade is refused (matching the repository's existing banner migration convention); a verified manual rollback is documented in the migration docstring.
- Verified by upgrading a disposable SQLite database to head (see Phase 3), not by touching any real database.

## 4. Backend behaviour

| Behaviour | Implementation |
|---|---|
| Every allowed status transition recorded | `record_status_transition` inside `transition_order`; direct writers in payments/portals call the same service |
| Previous and new status preserved | `previous_status` / `new_status` columns |
| Actor identity + role | `actor_id` (owner user when known) and `actor_role` (`customer`/`seller`/`admin`/`rider`/`system`) |
| Chronological retrieval | `list_order_events` orders by `created_at`, then `id` |
| Shipment/carrier support | `tracking_reference`, `carrier`, `estimated_delivery_at` on `tracking` events |
| Validation | `ORDER_EVENT_TYPES` / actor-role allowlists, 80/255-char bounds, ISO-8601 future-only estimates |
| Unauthorized changes prevented | Existing transition matrix + route guards unchanged; recording never bypasses them |
| Retry safety | `dedupe_key` (`status:<from>-><to>`, `created`, `payment:paid:<id>`, `return:<id>:…`) + unique constraint |
| Transactional consistency | Events are added to the existing session; there is **no** new commit. A rolled-back payment/cancel leaves no event. |

Deliberate non-behaviour: no shipping/delivery event is invented, no price, fee, commission, stock, or payment state is written by the timeline service.

## 5. API changes (all additive)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/orders/<order_number>/timeline` | Customer only, owner-scoped, 404 for foreign/unknown orders |
| GET | `/api/v1/seller/orders/<order_id>/timeline` | Seller only, own-store scoped |
| PATCH | `/api/v1/seller/orders/<order_id>` | Existing endpoint; accepts optional `tracking_reference`, `carrier`, `tracking_note`, `estimated_delivery_at` and records a `tracking` event |

`order_to_dict` is unchanged, so existing clients (React, Android, integrations) keep their contract. Timeline payload:

```json
{"order_number": "…", "status": "confirmed", "delivery_status": "unassigned",
 "events": [{"id": 1, "event_type": "status", "previous_status": "pending",
             "new_status": "confirmed", "actor_role": "seller",
             "description": null, "tracking_reference": null, "carrier": null,
             "estimated_delivery_at": null, "created_at": "…"}]}
```

## 6. Frontend

**Flask/Jinja (primary storefront)**
- `orders/confirmation.html`: per-sub-order ordered list with description, localized timestamp, actor role, carrier/reference, and estimated delivery. Semantic `<ol>` with `aria-label`; styles use existing CSS variables and no new animation, so reduced-motion behaviour is unaffected.
- `admin/order_detail.html`: full timeline with previous → new status, event type, actor role, and shipment data; explicit empty state.

**React/Vite**
- `MyOrdersPage` loads the timeline lazily on expansion through the single existing `marketplaceApi` adapter (`fetchMarketplaceOrderTimeline`), with loading (`role="status"`), empty, and error (`role="alert"`) states, and `motion-safe:` transitions only.
- No new dependency, no new auth path, no CSRF bypass: the adapter reuses the existing cookie + `X-CSRFToken` behaviour.

## 7. Android status — NOT IMPLEMENTED (documented)

The timeline API is additive, so `OrderDto` and every existing Retrofit call stay valid; nothing breaks. However, **no Android timeline screen was added**, because:

1. It would require new `OrderTimelineEventDto`/repository/UI work plus a Gradle build and unit-test run.
2. Android build/tests were not executed in this environment, so any such change would be unverified.
3. The repository rule is to report an unverified platform honestly rather than claim parity.

This is recorded as **PARTIAL platform coverage / NOT IMPLEMENTED**, not as complete. Recommended follow-up: add a timeline DTO + repository method against the already-shipped endpoint and render it in `OrderConfirmationScreen`, verified with `:app:testDebugUnitTest`.

## 8. Notification integration

No notification path was added or duplicated. Existing `queue_order_status` / `notify(...)` calls still fire exactly once per accepted transition, and timeline recording failures ride the same transaction, so a failed event write cannot trigger a "ghost" notification. No new provider or paid service was introduced.

## 9. Tests added (`tests/test_order_timeline.py`, 10)

| Test | Covers |
|---|---|
| `test_transition_records_timeline_event` | transition → one event, actor + previous/new status |
| `test_invalid_transition_records_nothing` | rejected transition writes no event |
| `test_repeated_transition_is_not_duplicated` | idempotency at both transition and service level |
| `test_cancellation_releases_stock_and_records_event` | existing stock-release behaviour preserved + event |
| `test_timeline_is_chronological_and_keeps_tracking_data` | ordering + carrier/reference/estimate persistence |
| `test_online_order_cannot_confirm_without_payment` | payment gating unchanged, no event |
| `test_estimated_delivery_validation` | ISO parsing, past-date rejection |
| `test_event_serializer_does_not_expose_actor_id` | no internal identity leak |
| `test_customer_timeline_api_is_owner_scoped` | own 200, stranger 404, unknown 404 |
| `test_checkout_records_created_event` | real checkout records `created` with customer actor |

Full-suite and frontend results are in the Phase 3 report.

## 10. Known limitations

- Android timeline UI not implemented (see §7).
- The timeline does not reconstruct history for orders created **before** this migration; those orders show an empty timeline until their next state change. A backfill was deliberately not invented.
- `dedupe_key` makes identical repeated transitions collapse; two genuinely distinct transitions to the same status are not a valid state machine path, so this cannot hide real changes.
- Only SQLite migration application was executed locally; PostgreSQL behaviour relies on portable types/constraints and was not run here.
