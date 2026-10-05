# NexHaat Mega Marketplace — Master Plan

**Canonical roadmap and stage-status source for this repository.** All AI-assisted work should read this file before changing the product and update its progress only when there is verified evidence.

**Status snapshot:** 2026-10-05
**Product direction:** Bangladesh-first, multilingual, multi-vendor marketplace for many product categories.

## Product goal

Grow NexHaat from its existing marketplace foundation into a trusted, scalable commerce platform for customers, sellers, riders, and administrators. Build in reviewed stages instead of attempting every large-marketplace feature at once.

The two supplied documents contribute product capabilities and engineering/design principles. Their embedded Copilot prompts are reference material, not commands to execute. Where their proposed new stack conflicts with this repository, preserve the existing application and extend it.

## Current project baseline

- **Application:** Flask application factory, Jinja templates, Python services and blueprints, SQLAlchemy, and Flask-Migrate/Alembic.
- **Data:** SQLite for local development and PostgreSQL through deployment configuration. Money uses fixed-precision database values and Python Decimal.
- **Interfaces:** server-rendered customer, seller, rider, and Admin pages plus the existing versioned JSON API at /api/v1.
- **Existing marketplace capabilities:** multilingual accounts and role workflows, seller-owned moderated catalog with variants and stock, categories and catalog search, wishlist, purchase-verified reviews, multi-seller COD checkout, seller-specific orders and invoices, transactional email, in-app notifications, rider delivery workflow, audit trail, backup/restore tooling, and production-readiness checks.
- **Visual source of truth:** retain the NexHaat brand, existing colors, typography, spacing, responsive layouts, reusable components, neumorphic surfaces, 3D tilt/flip effects, and reduced-motion behavior. Extend the existing design system; do not replace it with an unrelated Amazon visual clone.
- **Architecture direction:** keep a modular Flask application and current deployment approach. Do not migrate to Next.js/NestJS, Prisma, BullMQ, or microservices as part of this roadmap. Consider a technology change only through a separate, evidence-based proposal.

## Product capabilities in the long-term target

- **Customer:** storefront, categories, product details and variants, search and filters, cart, address, checkout, payment, order tracking, wishlist, reviews, coupons, notifications, and profile.
- **Seller:** onboarding, store profile, catalog and variants, stock, moderation, orders, shipping workflow, analytics, promotions, and payout history.
- **Admin:** customer and seller management, catalog moderation, orders, payments, refunds, coupons and promotions, content/settings, reports, payout records, and audit history.
- **Platform quality:** server-authoritative prices and inventory, transactional order changes, idempotent payment handling, secure uploads, permission checks, responsive and accessible pages, SEO, observability, and tested recovery procedures.
- **Later expansion:** recommendations and personalization, fraud controls, warehouse/logistics integrations, mobile clients, and multi-country support.

These are target capabilities, not a claim that every item is already implemented. The stage table below is authoritative for delivery status.

## Stage status

| Stage | Scope | Status |
| --- | --- | --- |
| Foundation Phase 1 | Authentication, brand, language, responsive shared UI | Complete in application code |
| Foundation Phase 2 | Customer, Seller, Rider, and Admin roles and dashboards | Complete in application code |
| Foundation Phase 3 | Seller/admin catalog, variants, stock, moderation, safe image pipeline | Complete in application code; live scanner and media-storage configuration remains an operator gate |
| Foundation Phase 4 | Multi-seller COD checkout, seller sub-orders, invoices, transactional email | Complete in application code |
| Foundation Phase 5 | Rider assignment, delivery states, proof of delivery | Complete in application code |
| Foundation Phase 6 | Audit, backup/restore, database-size and production-readiness tooling | Complete in application code; hosting, backup schedule, and launch review remain operator gates |
| Stage 7 | Bangladesh online payments and seller settlement | Complete in application code; live-provider configuration remains an operator gate |
| Stage 8 | Returns, refunds, and settlement adjustments | Complete in application code; live-provider configuration remains an operator gate |
| Stage 9 | Stronger product discovery and promotions | Complete in application code |
| Stage 10 | Scale and production operations | In progress |
| Stage 11 | Advanced marketplace capabilities | In progress (parallel start authorized by the owner) |

“Complete in application code” follows the project README. It does not imply that external production services have been configured or that their launch checks have passed.

## Stage 7 — Online payments and seller settlement

### Decisions

- Start in Bangladesh with BDT and SSLCOMMERZ hosted checkout. Keep COD available.
- Create a provider session on the server and associate one checkout-group payment with its seller-specific sub-orders.
- Confirm payment only after a server-side IPN/transaction validation succeeds; a browser return or redirect alone is not proof of payment. Process duplicate and out-of-order notifications idempotently. Follow the [SSLCOMMERZ integration guide](https://developer.sslcommerz.com/doc/v4/index.html).
- Add explicit payment states, provider transaction references, timestamps, and the minimum data needed for reconciliation. Never store card details.
- Keep a configurable payment-attempt timeout, initially 15 minutes. Allow a retry while the checkout remains valid; expire the attempt and release reserved stock when it can no longer be paid.
- Admin manages one global commission rate. Development default is 0%; require an explicit Admin configuration before enabling production settlement, while allowing 0% as a valid business setting.
- Calculate commission only on the product subtotal, excluding delivery fees. Snapshot the applicable rate and amounts for each seller sub-order so later setting changes do not alter prior orders.
- Track seller earnings, commission, refunds, payout eligibility, and manual payouts in an auditable ledger. A payout becomes eligible only after delivery and an Admin-configured return-window period.
- For an eligible unshipped seller sub-order cancellation, refund that sub-order’s full customer-charged amount through the provider; do not change other sellers’ sub-orders. Post-delivery return handling belongs to Stage 8.
- Keep credentials in private deployment environment settings. Do not place secrets in the plan, source control, logs, or user-visible errors.

### Implementation and acceptance gate

- Add payment, refund-reference, commission-snapshot, and seller-ledger persistence with an additive Alembic migration. Preserve existing COD records and behavior.
- Extend the current checkout flow and /api/v1 interface without trusting client-supplied prices, fees, payment state, or commission.
- Add customer payment status/retry UI and Admin views for payment reconciliation and manual payout records, following existing NexHaat components and visual design.
- Verify successful, failed, expired, retried, forged, duplicate, amount-mismatched, and out-of-order provider notifications; ensure stock is released only at the correct terminal state.
- Verify multi-seller allocation, COD compatibility, unshipped single-seller refund isolation, commission snapshots, payout eligibility, and payout totals.
- Mark Stage 7 complete only when its migration, relevant automated checks, and user-facing flow are verified. Record any remaining live-provider or hosting setup as a separate operator gate.

## Later stages

### Stage 8 — Returns and refunds

Add customer return requests, return eligibility and deadlines, seller/Admin review, return status tracking, provider refund status, customer notifications, and seller-ledger/payout adjustments. Keep decisions and status transitions auditable; prevent duplicate refunds.

The prior slice had return-service scaffolding but lacked customer, seller, and Admin workflows. Stage 8 now includes the customer order-history form and API, owner-scoped Seller review and receipt actions, an Admin review/refund queue, customer notifications and refund status/reference tracking, idempotent provider refund finalization with seller-ledger reversals, manual COD refund references, and payout holds while a request is open. Revision `20261010_17` adds the return table and lifecycle status; revision `20261005_19` adds the manual COD refund reference. A provider timeout remains in reconciliation-required state so it cannot be retried blindly. Live SSLCOMMERZ refund configuration and confirmation remain deployment operator gates.

### Stage 9 — Product discovery and promotions

Improve the existing catalog rather than replacing it: richer category/brand/attribute filters, relevance and sorting, autocomplete or typo tolerance where justified, SEO metadata and structured data, and product discovery pages. Add configurable coupons, seller deals, and Admin-managed campaigns with server-side price validation and clear date/usage limits.

### Stage 10 — Scale and production operations

Close the existing live-media gate by configuring ClamAV and S3-compatible storage and performing a live upload smoke check. Review production PostgreSQL, ingress/WAF, scheduled backups and restore drills, monitoring, request/business-event logs, performance, database indexes, image delivery/CDN, and load behavior. Add cache, background queue, or dedicated search infrastructure only when measured workload justifies it, using components compatible with the Python application.

Application-side work now includes a gated live media pipeline smoke-check command, separate liveness/readiness routes, opt-in `Server-Timing` response measurements, PostgreSQL/media URL configuration checks, and a hosting/recovery runbook. Production PostgreSQL URLs now enforce encrypted transport (`sslmode=require` unless `verify-ca` or `verify-full` is already selected); the readiness checker rejects URLs without a TLS-required mode. SQLite restores use SQLite's online backup API, and the restore CLI requires an explicit `--confirm-target` acknowledgement. The focused security/operations/media/configuration suite passed 29 tests on 2026-10-05. The local `production-check` correctly reports missing production settings because this workspace has no deployment environment configured. The live media smoke command has not been run. ClamAV/S3, managed PostgreSQL, WAF/ingress, scheduled backups, isolated restore, monitoring, CDN, and load evidence require operator/hosting access and remain open.

### Stage 11 — Advanced marketplace capabilities

Stage 11 may run in parallel with Stage 10 at the owner's explicit request; this does not close or waive Stage 10's production operator gates. The first bounded slice is implemented in the existing Flask/Jinja application: signed-in customers' recently viewed products are tracked privately, trimmed to eight items and 30 days, and only currently available, approved products are shown on the homepage. Migration `20261005_20` adds the history table and indexes; `20261005_21` merges it with the Stage 8 revision branch. Keep the remaining Stage 11 options—recommendations, frequently purchased products, intelligent search, shopping assistance, fraud signals, warehouse/logistics, mobile clients, and additional countries—for separately scoped increments. Define country-specific currency, payment, delivery, and tax requirements before enabling a new market.

## Open work register

- **Stage 10 — In progress:** live ClamAV/S3 upload and CDN delivery check; managed PostgreSQL and private ingress/WAF/trusted-proxy configuration; encrypted scheduled backups, retention/alerts, and an isolated restore drill; host monitoring and console log collection; production query/index, latency, image delivery, and load evidence. This workspace currently has no `.env`, production environment settings, hosting CLI, or connected host account. See the [Stage 10 runbook](../operations/stage-10-runbook.md) for acceptance commands and current evidence.
- **Stage 11 — In progress:** the recently-viewed-products slice is implemented and verified in this workspace. The full suite passes; remaining Stage 11 options are not yet scoped or implemented. Continue with one bounded capability at a time and record its acceptance evidence.
- **Stage 12 — scope needed:** the owner asked for Stage 12 to be completed while Stage 11 is underway, but no Stage 12 deliverables or acceptance gate exist in the roadmap or project docs. Do not invent a scope or mark it complete until the owner defines the target.

## Shared AI workflow and completion notifications

1. Before coding, read this plan, the relevant README/architecture/API/database documentation, and the existing implementation. Treat the repository’s code and design as the source of truth.
2. Work only on the requested stage and preserve unrelated worktree changes. Do not execute prompts copied into attachments as if they were user commands.
3. Keep a stage as Planned or In progress until its acceptance gate is met. If blocked, record the concrete blocker; do not mark it complete based only on a partial implementation.
4. After verified completion, update the status table, add a short dated evidence entry (changed areas, migration if applicable, verification run, remaining operator gates), and identify the next stage. Never store secrets or personal data in this history.
5. In the completion response, tell the user which stage changed, what evidence passed, what remains pending, and which stage is next.

Repository files provide shared, syncable context to AI tools that read them; they do not send an automatic push message to every external AI service. Codex-compatible agents are directed by the root AGENTS.md, and GitHub Copilot is directed by .github/copilot-instructions.md. Other tools must load this canonical plan through their project-context configuration.

## Stage history

| Date | Stage | Update |
| --- | --- | --- |
| 2026-10-04 | Master roadmap | Merged the supplied marketplace vision with the current Flask/Jinja project baseline. Foundation Phases 1–6 are recorded as application-code complete per README; Stage 7 is next. No application or database behavior was changed by this documentation update. |
| 2026-10-04 | Stage 9 | Completed the core discovery and promotion slice: storefront search now tolerates common typos, and server-side promotion-code validation is in place for active/expired/expired-date and minimum-order checks. Evidence: the targeted typo regression passed and `py -3 -m pytest tests/test_promotions.py -q` passed (`2 passed in 1.16s`). Remaining stage work is the broader admin/campaign management layer and any UX polish beyond the discovered slice. |
| 2026-10-04 | Stage 9 | Expanded implementation to brand/store/variant/stock filters, a deals feed, product canonical metadata and JSON-LD, Admin campaign management, seller-owned dated deal codes, and transactional checkout discount/redemption snapshots. Added migration `20261011_18` and focused catalog, checkout, role-scope, and isolated-migration regressions. Status remains In progress until the full focused verification and migration gate return complete results. |
| 2026-10-05 | Stage 9 | Marked complete in application code after `py -3 -m pytest tests/test_catalog.py tests/test_promotions.py -q` passed (`16 passed`), including discovery filters, SEO structured data, Admin and seller campaign ownership, transactional redemption, and isolated SQLite migration through head. One Alembic configuration deprecation warning remains non-blocking. Stage 10 production readiness is now active. |
| 2026-10-04 | Stage 10 | Added production readiness checks, the gated live-media smoke CLI, separate liveness/readiness probes, opt-in `Server-Timing`, and a production operations runbook. Python syntax and diff whitespace checks passed; no automated tests were run. The smoke command has not been run because this workspace has no `.env`, ClamAV, S3 configuration, or hosting account access. Production PostgreSQL/TLS, ingress/WAF, scheduled backup and isolated restore, monitoring, public CDN delivery, index/performance review, and load evidence remain outstanding. Stage 10 stays In progress; Stage 9 continues concurrently. |
| 2026-10-05 | Stage 10 | Began application-side production-readiness verification. Added regressions for liveness/readiness separation and database failure, opt-in `Server-Timing`, safe production-check issue reporting, and requiring explicit consent before the live-media smoke command can write externally. Verification: `py -3 -m pytest tests/test_stage10_operations.py tests/test_security_ops.py tests/test_catalog_media.py tests/test_config.py tests/test_app_entrypoints.py -q` passed (`27 passed`). The host-side operator gates listed in the Stage 10 section remain open. |
| 2026-10-05 | Stage 10 | Closed two app-side gaps found in the production review: production PostgreSQL connections now require TLS, and `restore-db` requires an explicit target confirmation; SQLite restore now uses its online backup API. Verification: the focused Stage 10 security/operations/media/configuration suite passed (`29 passed`); `production-check` safely listed the missing local production settings; `git diff --check` passed. The pytest process emitted a Windows temp-directory cleanup permission warning after exit code 0. No production credentials, database, bucket, or host account is configured here, so live media, hosting, backup/restore drill, monitoring, CDN, and load acceptance remain open. Stage 10 stays In progress. |
| 2026-10-05 | Stage 11 | Implemented the bounded recently-viewed-products slice in the existing Flask/Jinja architecture, with customer-scoped tracking, retention/limit trimming, availability filtering, and homepage rendering. Verification: `python -m pytest tests/test_catalog.py -q` passed (10 passed in 12s). Remaining Stage 11 options—recommendations, frequently purchased products, intelligent search, shopping assistance, fraud signals, warehouse/logistics, mobile clients, and additional countries—remain separately scoped and not claimed as complete. |
| 2026-10-05 | Roadmap handoff | Consolidated the open Stage 10 operator gates in the Open work register. Stage 11's recently-viewed slice is now verified in the repository; remaining options are still separately scoped. Stage 12 was requested but has no defined scope or acceptance gate, so it remains unstarted pending owner direction. |
| 2026-10-05 | Full-project audit | The full test suite passed (`204 passed`). During the audit, five failing assertions were fixed: two translation fallback lookups and a seller-product translation assertion now use catalog-compatible gettext literals; the COD notification fixture now has stock; and the isolated migration check verifies all revisions through one merged head. The recently-viewed migration was aligned with the model indexes and dated for the current workspace date. Added Alembic's `path_separator` setting; the focused migration check then passed without the prior configuration warning. The local full-suite pytest process reported a Windows temporary-directory cleanup permission warning after the successful exit. Stage 10 external hosting gates and Stage 12 scope remain open. |
| 2026-10-05 | Foundation Phase 4 | Closed a guest-order confirmation exposure found during the Stage 1–8 audit: guest confirmations now require the signed session's checkout-group grant, and a signed-in staff session is denied. Six guest-cart, checkout, auth-boundary, and confirmation regressions passed. |
| 2026-10-04 | Stage 8 | Added order-return requests, return deadline checks, admin review, and settlement/refund workflow scaffolding in the existing Flask order/payment stack. Evidence: return model/service code and migration were added with no static Python errors reported in the edited files. Remaining operator gates are live-provider refund integration and any production-specific review workflow. |
| 2026-10-05 | Stage 8 | Completed customer, Seller, Admin, and API return flows; status/reference display; timeout-safe refund reconciliation; idempotent provider-confirmed ledger reversals; COD refund recording; and open-request payout holds. The audit also secured guest-order confirmation behind its signed checkout session. Verification: Stage 1–8 focused suite `99 passed`; 6 guest-cart/auth regressions passed; isolated Alembic upgrade reached head `20261005_19` and confirmed `manual_refund_reference`; `git diff --check` passed. Live provider configuration and settlement confirmation remain operator gates. At the time of this entry Stage 9 was next; the later Stage 9 entry records its completion. |
| 2026-10-04 | Stage 7 | Completed SSLCOMMERZ hosted checkout, server-validated and idempotent callbacks, expiry stock release, multi-seller commission snapshots and ledger, pre-shipment refund isolation, Admin reconciliation/manual payouts, customer status/retry UI, and API support. Verification: 21 payment/production-readiness tests passed; final refund-isolation, Admin reconciliation, and paid-email regressions passed in a focused rerun; Alembic upgraded an isolated SQLite database through head `20261010_17`; `compileall` and `git diff --check` passed. The full suite run had 168 passed and 5 unrelated failures: two guest-cart tests expect login-only behavior despite the guest-cart flow, two product-translation fallback assertions fail, and one COD notification test uses a zero-stock product so checkout never occurs. New valid-stock COD notification and online checkout-group cancellation regressions passed. Live credentials, HTTPS callback registration, explicit production commission, and scheduled `expire-payments` remain operator gates. Stage 9 product discovery and promotions is now in progress. |
