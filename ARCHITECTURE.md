# Architecture

The project uses an application factory in `app/__init__.py`. Extensions are initialized without an app in `app/extensions.py`, allowing the same models and services to be used by tests, CLI commands, and production entry points.

HTTP routes live in blueprints under `app/routes`. Catalog routes delegate active filtering and lookups to `app/services/catalog.py`, which uses `app/repositories/catalog.py` query builders. This keeps route handlers focused on HTTP concerns and ensures unavailable products are not exposed through normal customer catalog routes.

Cross-cutting behavior lives in `app/services`:

- `catalog_media.py` runs the fail-closed image intake (private quarantine, ClamAV scan, decode/re-encode, S3-compatible upload).
- `mail.py` renders each transaction email once into the `outbound_emails` outbox and delivers it in the background with bounded retries; `flask retry-emails` resends anything still pending.
- `invoice.py` builds a seller-specific, localized PDF invoice with ReportLab.
- `audit.py` appends security-relevant events to `audit_events` and never breaks a request if auditing fails.
- `backup.py` and `review.py` back the backup/restore, database-size, and production-readiness CLI commands.
- `ai_rate_limit.py`, `personalization.py`, and `ai_notifications.py` provide shared AI request limits, deterministic customer-signal ranking, and opt-in in-app alert hooks/digests.

The shared AI Core lives under `app/ai`. A configured private local model is the first responder; external specialist/API fallback is separately consented, budget-reserved, and gated by metadata-only Security Bot notices. Each request scope is selected by the authenticated role or the Security Bot numeric allowlist; a request cannot choose another scope or user. Tool functions call existing catalog, cart, order, seller, and aggregate services. The Core has no general SQL, shell, or file access. Customer cart proposals are one-use and revalidate current product, variant, price, and stock through the cart service. Seller drafts are returned for manual review. Admin and Security analytics are read-only, while the Security Bot exposes only explicitly identity-bound marketplace approvals.

When a model is configured, Customer messages go to the shared Core with bounded recent turns, the selected locale, and scoped marketplace tools before any deterministic catalog fallback. The Core is instructed to interpret meaning and context—including informal, multilingual, misspelled, corrective, and compound messages—rather than require exact command phrases. Conversation history is untrusted context, never verified marketplace data; private and current facts still require authoritative tools.

AI requests have bounded input, context, provider timeouts, tokens, tool calls, uploads, and database-backed per-scope rate limits. Logs keep metadata only. Provider output with explicit internal-reasoning/scratchpad markers is rejected before it reaches a client. AI chat history and customer voice/image uploads are handled in memory; curated role-scoped Markdown is indexed through the configured local embedding endpoint. Only explicitly submitted human support cases are stored. Normal catalog/homepage requests do not call an AI provider. Customer and Security Telegram handlers use the same Core and authoritative services as the website; webhook delivery is separately verified from mocked handler tests.

The Admin Builder/Guardian is an Admin-only Stage 14 workspace over the shared Core. Project persistence is explicit opt-in; uploaded media and one-off source are handled in memory, while saved project source is bounded, owner-scoped, and screened for common secret literals. ZIP inspection rejects traversal, symlinks, and decompression abuse without extraction. Patch candidates are stored as bounded diffs and candidate files. Tests run only in a digest-pinned Docker image with no network, a read-only project mount, a non-root UID, dropped capabilities, and resource limits. Approval is a separate Admin action; applying to a saved project and exporting are separate actions, and no deployment is automatic. Guardian scans use a signed queue and local static rules; repeated findings are deduplicated, scanner failures warn, and the deployment command blocks only on Admin-confirmed high-risk findings. Sanitized lessons enter the Admin-only knowledge scope only after passing sandbox evidence and explicit approval.

Checkout groups a customer's cart by seller and creates one sub-order per seller inside a shared `checkout_group`, so each seller gets an independent order, invoice, delivery record, and status.

Catalog prices use SQL `Numeric(10, 2)` and Python `Decimal`; floating-point money calculations are not used. Product and category slugs are normalized and unique. Catalog pages are limited to 48 records, while the admin order and customer tables are paginated. Uploaded images are restricted to JPEG, PNG, and WebP, checked against their file signatures, and limited to 2 MB; active SVG uploads are rejected.

Users are represented by one `users` table with a role and separate one-to-one profile tables (`customers` and `admins`). Password reset state and attempt counts live in the database, while `auth_version` revokes sessions after password changes. Login throttling uses a keyed client-address hash in the database so it works across workers without storing raw addresses.

Flask-Migrate owns production schema changes. Production app startup does not create or alter tables; deployments apply migrations before starting workers. The adoption revision preserves databases created by earlier app versions. SQLite connections enable foreign-key enforcement and a write wait timeout for reliable local development.

USDA FoodData Central reference foods and nutrient observations live in separate `fdc_*` tables, not in the orderable menu product table. FoodOn taxonomy terms live in `foodon_categories`; they are vocabulary records and are not automatically assigned to a product when no authoritative mapping is present. The explicit `flask import-fdc` and `flask import-foodon` commands stream public source files into the configured SQLite or PostgreSQL database and enforce a maximum database size of 400 MiB by default.

Responses set a restrictive Content Security Policy, MIME sniffing and framing protections, referrer and permissions policies, and HSTS on secure production requests. CSRF protection covers state-changing forms.

## Extension rules

- Keep secrets in environment variables.
- Use migrations for schema changes after the initial prototype.
- Keep order creation transactional and server-side price validated.
- Add authorization decorators before exposing admin routes.
