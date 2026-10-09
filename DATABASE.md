# Database

The app uses Flask-Migrate/Alembic for schema changes. Apply revisions with `flask db upgrade` before deploying application code. The initial adoption revision creates missing tables on a new database and safely recognizes tables created by earlier app versions. Production startup does not issue schema-changing DDL. Production PostgreSQL connections require TLS (`sslmode=require` or stronger); set `APP_ENV=production` to have the app enforce this when parsing its connection URL. Take a database backup before deploying a migration.

The `users` table stores normalized email addresses and Werkzeug password hashes. Customer and admin profiles are linked with foreign keys and one-to-one constraints. `auth_version` invalidates existing sessions after password changes and account activation changes. Password reset digests, expiry times, delivery cooldowns, and a five-attempt limit are stored server-side; raw reset codes are never stored in the database. `auth_throttles` stores keyed hashes of client addresses and applies a shared limit of 10 failed logins per 15-minute window, followed by a five-minute block. Raw addresses are not retained.

Phase 2 adds `categories` and `products`. Category slugs and product slugs are unique and indexed. Product category references use a foreign key with restricted deletion, and active/availability/search fields are indexed. Prices use `Numeric(10, 2)` with database check constraints and Python `Decimal` validation. Customer queries join active categories and available products so unpublished catalog records are not displayed.

Beyond the core `users`, `customers`, `admins`, `addresses`, and `app_settings` tables, the schema now includes:

- `seller_profiles`, `rider_profiles`, and `account_invitations` for role onboarding, approval state, and single-use staff setup links.
- `categories`, `products`, `product_translations`, and `product_variants` for the catalog, seller-authored multilingual text, and SKU stock.
- `products.brand_name` for optional, seller/Admin-authored brand discovery.
- `promotion_codes` for Admin coupons and seller-owned deal codes, including discount rules, schedule windows, usage limits, and status; `promotion_redemptions` records each applied checkout group and discount amount. Orders snapshot `promotion_code` and `discount_amount`, and online `payments.amount` uses the same server-calculated total.
- `orders` and `order_items`. Each order may belong to a `seller` and a `rider`, carries a `checkout_group` and `delivery_fee`, and tracks the delivery workflow through `delivery_status` with per-stage timestamps, proof of delivery, and a note. Order items snapshot product name, selected variant label, SKU, price, quantity, and subtotal so later catalog edits do not change historical orders.
- `admin_login_challenges` for passwordless Admin email-OTP challenges (hashed code, expiry, attempts, single use).
- `registration_challenges` for customer and seller signup OTPs. Challenges keep only a hashed code and password hash plus pending profile details, expire after 10 minutes, allow five verification attempts, and are consumed when the account is created.
- `auth_throttles` for keyed login throttling.
- `outbound_emails` for the durable transactional-email outbox with attempt counts and retry state.
- `audit_events` for the security audit trail (action, actor snapshot, target, detail, and a keyed client-address hash).
- `fdc_*` and `foodon_categories` for the imported reference vocabulary.
- `reviews` for purchase-verified product reviews: a 1–5 rating, an optional comment, an author-name snapshot, the delivered `order_id` that proves the purchase, and an Admin moderation `status` (`pending`/`approved`/`rejected`) with `moderated_at`/`moderated_by_id`. A unique constraint on (`product_id`, `user_id`, `order_id`) stops duplicate reviews of the same purchase. Only `approved` reviews are shown on the storefront.
- `notifications` for the in-app inbox: a `type` (`order`/`delivery`/`account`/`system`), a message, an optional in-app `link`, and an `is_read` flag. Rows cascade-delete with the owning account.
- `order_returns` for a one-per-order return request, seller/Admin review, received/refunded/failed status, provider or manual refund reference, reason, amount snapshot, and lifecycle timestamps. The audit trail records review actors; provider-in-progress state is held in `payment_refunds`. Open requests hold eligible seller-ledger entries until the request is rejected or resolved.
- `wishlist_items` for the customer wishlist: one row per saved product with a `created_at` timestamp and a unique (`user_id`, `product_id`) pair so a product can only be saved once per customer. Rows cascade-delete with the owning account and product.
- `recently_viewed_products` for customer-scoped product history: one row per customer/product pair, ordered by `viewed_at`, with indexes for customer, product, timestamp, and customer/timestamp lookups. The application trims history to the eight most recent products and 30 days; the homepage only shows currently available and approved products.
- `ai_preferences.personalized_recommendations_enabled` for explicit consent before recommendation ranking uses private views, wishlist, cart, or order signals; it defaults off.
- `ai_product_price_history` for observed approved listing prices (regular, discount, effective amount, observation time). It records observations from deployment onward and does not invent or backfill older prices.
- `ai_product_price_alerts` for one customer-owned target per product, with active/notified state. A verified price crossing creates an in-app notification in the same catalog transaction; the alert deactivates after notification.

Cart state remains in the signed Flask session; no persistent cart table is needed. Guest checkout is supported, and signed-in customers can also place orders from their account. A guest can view a COD order confirmation only in the signed session that completed checkout; seller and Admin sessions cannot use customer cart, checkout, or guest order confirmations. Checkout locks and revalidates current product/variant stock and price, reserves inventory in the order transaction, and restores stock for eligible cancellation/decline. The starter taxonomy includes food, clothing, electronics, and household categories; it does not invent products, prices, or stock. Sellers create real listings, which remain unavailable until Admin moderation. Cancelled, declined, and completed orders remain in the database for customer history and audit; removal is only available through the explicit admin action.

Revision `20261008_15` adds nullable `variant_id`, `variant_label`, and `sku_snapshot` fields to `order_items`; apply it with `flask --app run.py db upgrade` before deploying the corresponding application code.

Revision `20261011_18` adds optional product brands, promotion campaign/redemption tables, and per-order discount snapshots. Apply it with `flask --app run.py db upgrade` before deploying Stage 9.

Revision `20261005_19` adds manual COD refund references. Apply it with `flask --app run.py db upgrade` before deploying the complete Stage 8 return flow.

Revision `20261005_20` adds customer recently viewed products. Revision `20261005_21` merges it with the Stage 8 COD refund-reference revision so the database has one Alembic head. Apply both with `flask --app run.py db upgrade` before deploying the corresponding code.

Stage 12 revisions `20261006_25` and `20261006_26` add hashed shared AI rate-limit windows, opt-in customer smart-notification preferences and caps, and explicit human support cases/messages. They do not store AI chat transcripts, audio, or customer image uploads. Revision `20261006_26` adds per-kind weekly digest timestamps. Apply with `flask --app run.py db upgrade` before deploying Stage 12 code; the migration is additive and preserves existing rows.

Revision `20261007_28` adds metadata-only per-request external AI notice records and per-allowlisted-recipient delivery retry state; prompts and media are not stored. Revision `20261007_29` adds opt-in recommendation personalization plus observed price history and customer target alerts. Apply with `flask --app run.py db upgrade`; the new schema is additive and does not backfill synthetic price history.

Revision `20261007_30` adds Admin project-analysis job metadata and bounded result storage. Uploaded ZIP bytes and source files are not persisted; each row is scoped to its creating Admin and can be deleted through the job API. Apply with `flask --app run.py db upgrade` before deploying the Stage 14 analysis endpoint. This schema does not implement saved projects, patches, sandbox state, or scan results.

Revision `20261009_34` adds the owner-scoped `ai_customer_documents` table for extracted PDF, UTF-8 TXT, and Markdown text. Source upload bytes are transient; rows cascade-delete with the owning customer and are covered by a unique per-customer content digest. Apply with `flask --app run.py db upgrade` before deploying Customer AI document upload and retrieval.

## Food reference data

USDA FoodData Central reference records are stored separately from `products`: reference foods have no invented menu price and cannot be ordered. The `fdc_foods`, `fdc_categories`, `fdc_nutrients`, `fdc_food_nutrients`, and `fdc_food_portions` tables keep source IDs, survey category assignments, nutrient measurements, and portion data. FoodOn product vocabulary is stored in `foodon_categories`, separately from the shop's customer-facing menu categories.

Apply the schema migration with `flask db upgrade`, then import a FoodData Central CSV ZIP with `flask import-fdc --zip-path <archive.zip> --release <release-date> --max-db-mib 400`. Import FoodOn vocabulary with `flask import-foodon --owl-path <foodon.owl> --max-db-mib 400`. Both importers stream records in bounded batches, enforce the database size limit, and roll back the active import if it would exceed that limit. USDA FoodData Central data is public domain under CC0; cite FoodData Central when redistributing the imported records.

The 400 MiB limit is a hard maximum for the configured database. A real dataset cannot provide one million distinct foods for every category; FoodOn supplies a real category vocabulary, while USDA supplies a finite set of food and nutrient records. The importer does not create synthetic rows to fill empty categories.

Monetary values use fixed-precision numeric columns and Python `Decimal`, never floating point. Database constraints validate order totals, payment method, order status, item price, and quantity. Composite indexes support customer order history, admin order lists, and catalog ordering. SQLite connections enforce foreign keys and wait briefly during concurrent writes.
