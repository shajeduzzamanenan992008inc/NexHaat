# Order Tracking Timeline — Phase 1 Audit and Design

**Date:** 2026-11-03
**Branch / HEAD:** `main` / `cc0f7fc48d19d38066dcc8b644daa7242bf9ef02`
**Scope:** Order tracking timeline only. No other feature was changed.
**Mode:** Local workspace. No deployment, no production access.

## 1. Baseline

| Item | Observed |
|---|---|
| `git status --short --branch` at start | `## main...origin/main`; the CI-remediation changes from Phase 54 were already present in the working tree (3 modified, 4 untracked). All were preserved. |
| Migration head before this work | `20261031_01` |
| Python | 3.15.2 (Windows x64) |
| Node / npm | 26.13.0 / 11.20.0 |
| Existing order tables | `orders`, `order_items`, `order_returns`, `payments`, `payment_attempts`, `payment_refunds`, `seller_ledger_entries`, `seller_payouts` |

## 2. Existing implementation inventory

| Capability | Status | Evidence |
|---|---|---|
| Order status field | **CONFIRMED** | `Order.status` in `app/models/order.py`, constrained to `pending, confirmed, preparing, delivered, returned, cancelled, declined` |
| Order status history | **MISSING** | No history/event table; `grep` for `status_history|OrderEvent|order_events` found none |
| Order event model | **MISSING** | — |
| Order event repository/service | **MISSING** | — |
| Tracking number / shipment reference | **MISSING** | No column on `orders` |
| Carrier information | **MISSING** | — |
| Estimated delivery timestamp | **MISSING** | Only `delivered_at`/`out_for_delivery_at` actual timestamps exist |
| Seller status updates | **CONFIRMED** | `app/routes/seller.py:update_order_status`, `PATCH /api/v1/seller/orders/<id>` in `app/api/routes/commerce.py` |
| Admin status updates | **CONFIRMED** | `app/routes/orders.py` (single + bulk), `PATCH /api/v1/admin/orders/<id>` |
| Customer order detail | **CONFIRMED** | `GET /orders/<order_number>` → `orders/confirmation.html`; `GET /api/v1/orders/<order_number>`; React `MyOrdersPage.tsx` |
| Existing tracking APIs | **MISSING** | No timeline endpoint |
| Notification hooks on status change | **CONFIRMED** | `queue_order_status`, `notify(...)` after each transition |
| Cancellation / return event handling | **CONFIRMED (state only)** | `cancel_order_with_refund` (payments), `request_order_return`, `refresh_refund_status`, manual COD refund |
| Delivery (rider) workflow | **CONFIRMED** | `DELIVERY_TRANSITIONS` + `app/routes/portals.py:update_delivery` |
| Audit trail | **CONFIRMED (separate)** | `audit_events` records actions, but is not order-scoped or customer-visible |

### Status writers found (every one had to be hooked)

| Location | Write |
|---|---|
| `app/services/orders.py:transition_order` | central allowed-transition writer |
| `app/services/payments.py` (payment confirmation) | `order.status = "confirmed"` directly |
| `app/services/payments.py` (provider refund) | `order.status = "returned"` |
| `app/services/payments.py` (manual COD refund) | `order.status = "returned"` |
| `app/routes/portals.py` (rider delivered) | `order.status = "delivered"` + `order.delivery_status` |
| `app/services/checkout.py` | creates each seller sub-order at `pending` |

## 3. Gap analysis

The order object already records **current** state and a handful of delivery timestamps, so a shopper can see "where it is now" but not how it got there. Because several writers assign `order.status` directly, no single chokepoint existed; a timeline required (a) an append-only event table and (b) hooks at every writer.

Chosen approach: **extend** the existing model/service layer with an additive `order_events` table and a small service, and route recording through `transition_order` plus the four direct writers. No existing table, route, payload, or workflow was replaced.

## 4. Database design

```
order_events
├── id                      INTEGER PK
├── order_id                FK orders.id ON DELETE CASCADE, indexed
├── event_type              created | status | delivery | payment | return | tracking
├── previous_status         VARCHAR(20) NULL
├── new_status              VARCHAR(20) NULL
├── actor_id                FK users.id ON DELETE SET NULL NULL
├── actor_role              customer | seller | admin | rider | system | NULL
├── description             VARCHAR(255) NULL
├── tracking_reference      VARCHAR(80) NULL
├── carrier                 VARCHAR(80) NULL
├── estimated_delivery_at   TIMESTAMPTZ NULL
├── dedupe_key              VARCHAR(120) NULL
├── created_at              TIMESTAMPTZ NOT NULL
├── UNIQUE (order_id, dedupe_key)
└── INDEX (order_id, created_at), (order_id), (created_at)
```

Design notes:
- **Additive only** — `orders` and `order_items` are untouched; migration `20261103_01` creates one table and three indexes.
- **UTC internally**; templates format with the existing conventions.
- `dedupe_key` gives idempotency: repeat `status:previous->new` writes collapse to one row. SQLite and PostgreSQL both allow multiple `NULL`s in a unique constraint, so tracking/delivery events without a key are unaffected.
- No customer PII is stored on the event; `actor_id` is stored but never serialized to clients.
- `ON DELETE CASCADE` from the order keeps history consistent if an order is ever removed; `actor_id` uses `SET NULL` so account deletion never erases timeline history.

## 5. API design

| Method | Path | Actor | Notes |
|---|---|---|---|
| GET | `/api/v1/orders/<order_number>/timeline` | customer (owner only) | `{order_number, status, delivery_status, events[]}`; 404 for anyone else's order |
| GET | `/api/v1/seller/orders/<id>/timeline` | seller (own store only) | same envelope |
| PATCH | `/api/v1/seller/orders/<id>` | seller | existing endpoint, now accepts optional `tracking_reference`, `carrier`, `tracking_note`, `estimated_delivery_at` (validated, recorded as a `tracking` event) |

All responses use the existing `success_response` envelope, so no client contract changes. The customer timeline endpoint returns events only — no actor IDs, no internal metadata.

## 6. Authorization design

- Customer: `_customer()` + `Order.user_id == user.id`; foreign orders and unknown numbers both return 404 (no existence disclosure).
- Seller: `_seller()` + `Order.seller_id == user.id`.
- Admin: existing `admin_required` / `_admin()` guards; admin timeline visible on the existing admin order detail page.
- Rider: existing delivery transitions only; each delivery change records an event with `actor_role="rider"`.
- Guest: the confirmation page keeps its existing signed-checkout-group rule; the JSON timeline endpoint remains authenticated-customer only.

## 7. Status-transition matrix (as implemented by existing code)

| Current | Allowed next | Authorized actor | Existing validation | Timeline event |
|---|---|---|---|---|
| `pending` | `confirmed` | seller, admin, system (paid online) | valid transition; online requires `paid`/`partially_refunded` | `status` (or `payment` when provider-confirmed) |
| `pending` | `declined` | seller, admin | cancellation + refund path | `status` |
| `pending` | `cancelled` | customer, admin, system (expiry) | cancellation rules | `status` |
| `confirmed` | `preparing` | seller, admin | online payment must be settled | `status` |
| `confirmed` | `declined` / `cancelled` | seller/admin / customer/admin | refund when paid | `status` |
| `preparing` | `delivered` | rider (proof of delivery), admin | proof photo or note required | `status` |
| `preparing` | `cancelled` | admin | refund rules | `status` |
| `delivered` | `returned` | system (refund completed) | return workflow | `return` |
| `returned`/`cancelled`/`declined` | — | — | terminal | — |

Delivery (`DELIVERY_TRANSITIONS`) is unchanged; every accepted change appends a `delivery` event, and the delivered step also records the `status` transition.

## 8. Compatibility risks and mitigations

| Risk | Mitigation |
|---|---|
| Event write breaking a payment/cancel transaction | Events are added to the **same session** and committed with the existing transaction; no extra commit was introduced |
| Duplicate events on retry | `dedupe_key` + unique constraint; invalid transitions are rejected before recording |
| Guest checkout regression | Guest creation records `actor_role="system"`; the guest confirmation rule is unchanged |
| Socket/DB portability | No DB-specific SQL; JSON-neutral types; verified on SQLite |
| Template variable missing on other renderers | `timelines`/`timeline` are supplied by the only two render sites; templates guard with defaults |
| Notification duplication | No new notification path was added; existing notifications still fire once per transition |
| Android contract | `order_to_dict` is unchanged; the timeline is a separate additive endpoint, so existing DTOs keep working |

## 9. Implementation plan (executed in Phase 2)

1. Add `OrderEvent` model + `order.events` relationship; export it.
2. Add `app/services/order_timeline.py` (record, chronological read, tracking lookup, ISO parsing).
3. Record inside `transition_order` and at the four direct status writers; record `created` at checkout.
4. Add timeline endpoints; extend the seller update payload with validated tracking metadata.
5. Render the timeline on the customer confirmation page and the admin order detail page; add it to the React orders page.
6. Add migration `20261103_01` and focused tests.

Phase 1 made no source change; only this document was added.
