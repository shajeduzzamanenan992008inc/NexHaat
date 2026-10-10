# NexHaat Marketplace

NexHaat is being developed in reviewed phases as a multilingual marketplace for customers, sellers, delivery riders, and administrators. **Foundation Phases 1–6 and Stages 7–9 are complete in application code. Stages 10 and 11 remain in progress; Stage 12 is complete in application code and mocked tests; Stage 13 local-first AI remains in progress with private GPU and staging acceptance open; Stage 14 Builder/Guardian code paths are implemented and verified locally, while sandbox-image, private model, Telegram, and full acceptance gates remain open.** Phase 3 delivered the seller catalog, variants, moderation, and the fail-closed image pipeline; Phase 4 added multi-seller checkout, seller-specific invoices, a durable email outbox, and localized order email; Phase 5 added Rider delivery assignment and a validated delivery workflow with proof of delivery; Phase 6 added the audit trail, backup/restore and database-size tooling, and the production readiness review. Enabling live WAF/ingress, media storage, scheduled backups, and live payment callbacks remains an operator step in the hosting account.

The canonical marketplace roadmap, stage status, acceptance gates, and AI handoff instructions are in [docs/plans/nexhaat-master-plan.md](docs/plans/nexhaat-master-plan.md). **Stage 9 — stronger product discovery and promotions — and Stage 12 — AI marketplace ecosystem — are complete in application code. Stages 10, 11, 13, and 14 remain active.**

## Phase plan

1. **Authentication, brand, and language foundation** — integrated Login and Sign Up experience, NexHaat branding and favicon, accessible responsive forms, CSRF protection, password reset, and four-language support.
2. **Roles and dashboards** — customer, seller, rider, and admin permissions with approval-based account creation where required.
3. **Seller and admin catalog** — store onboarding, product and food categories, variants, stock, moderation, and seller-provided translations.
4. **Customer checkout, invoices, and email** — multi-seller checkout, seller-specific orders and invoices, initially with cash on delivery.
5. **Rider and delivery operations** — delivery assignment, pickup and delivery states, and proof of delivery.
6. **Security and production launch** — WAF/firewall configuration, production review of upload scanning, backups, restore checks, and release review.

For upcoming marketplace work, follow the canonical master plan and update its stage status only after the acceptance gate is verified.

## Languages

The interface starts in **English (US)** and supports **বাংলা**, **हिन्दी**, and **العربية**. Arabic pages use right-to-left direction. Anonymous language choices live in the signed session; signed-in preferences are stored on the user account. Locale resolution is account preference, explicit session choice, browser language, then English (US).

Phase 1 and 2 translate shared navigation, authentication and password recovery, role dashboards, seller review, staff invitations, and password and invitation email. Phase 3 adds translated catalog, seller inventory, and catalog moderation screens. Phase 4 adds translated checkout, order, invoice, and transaction email copy. Seller-authored product text is not machine translated; missing translations retain the original wording and language label.

Translation catalogs live in `app/translations/<locale>/LC_MESSAGES/messages.po`. Extract and update them after adding translatable interface strings:

```powershell
pybabel extract -F babel.cfg -k gettext -k lazy_gettext -k _ -o app/translations/messages.pot app
pybabel update -i app/translations/messages.pot -d app/translations
```

Review and translate the `.po` files, then compile them:

```powershell
pybabel compile -d app/translations
```

Compile the catalogs with `pybabel compile -d app/translations` before deploying when your host does not compile them automatically.

## Local setup

1. Create and activate a virtual environment: `python -m venv .venv`
2. Install runtime and test packages locally: `pip install -r requirements-dev.txt` (production hosts install `requirements.txt` only).
3. Copy `.env.example` to `.env` and set a random `SECRET_KEY`. Keep `.env` out of source control.
4. Apply database migrations: `flask --app run.py db upgrade`
5. Start the development server in the foreground: `flask --app app run --host 127.0.0.1 --port 5009`. Keep its output in the terminal; do not redirect stdout or stderr to files.

Run the automated checks with `python -m pytest`. `.env.example` is a standard dotenv template; `.azure-app-settings.example.json` is only an Azure Advanced Edit template. SQLite is local-only; public deployment must use TLS-enabled PostgreSQL through `DATABASE_URL`. See [the public-launch checklist](docs/operations/public-launch.md) before exposing the site.

## Phase 1 details

- Flask/Jinja customer login and registration use the integrated neumorphic flip-card design with a mobile layout, keyboard support, and reduced-motion handling.
- Customer sign-up checks password confirmation on both client and server. Forms use CSRF tokens, server-side validation, password hashing, and the existing login throttling and password-reset protections.
- Admin accounts are provisioned through `ADMIN_EMAIL`, the `create-admin` CLI, or a staff invitation, and use email OTP sign-in instead of passwords.
- Language changes use `POST /language`, validate supported locales, preserve a safe same-site redirect, and require a CSRF token.
- User language preference is an additive nullable database field. The migration also updates the old default FreshBite brand setting to NexHaat.
- Uploaded images remain outside the database. Reference data imports enforce the separate 400 MB database cap.

## Phase 2 details

- Customers, sellers, and riders use `/auth/login`; Admins use `/admin/login` and verify a one-time code sent to their account email before entering operations.
- Customers can self-register. Seller applications create a restricted pending seller account; Admin can approve or reject each application. Product publishing remains reserved for Phase 3.
- Admin can invite Riders and additional Admins. Setup links expire after 24 hours, are one-use, and store only a keyed token digest. Riders choose a password; invited Admins activate their account and use email OTP for sign-in.
- Admin OTP and staff invitations require BREVO_API_KEY and MAIL_DEFAULT_SENDER; invitations also require a canonical HTTPS PUBLIC_BASE_URL in production. Admin codes expire after 10 minutes, allow five attempts, and can be resent once per minute.
- Set `ADMIN_EMAIL` to select the primary Admin. Local startup creates that account or promotes the matching existing account to Admin, preserving its existing profile and marketplace data while revoking old sessions. After production database migrations, run `flask --app run.py ensure-admin`; run it again whenever the configured primary email changes. Inactive accounts remain inactive and must be reactivated separately. Admin sign-in uses email OTP, never the stored password.
- Run `flask --app run.py check-mail` to verify Brevo key/sender configuration without sending a message.
- Forgot Password works for active non-Admin accounts with the same non-enumerating response and single-use verification-code protections.
- Marketplace customer cart and account actions reject signed-in Seller, Rider, and Admin roles. Admin review routes are protected by role and CSRF checks.
- The portal and operations screens follow the supplied neumorphic login reference with responsive cards, focus states, floating shapes, and reduced-motion handling. Arabic uses the same RTL direction as the shared layout.
- Revision 20261001_08 adds server-side Admin login challenge storage. Run `flask --app run.py db upgrade` before starting a previously initialized local database.

## Phase 3 complete

- Approved sellers can create and update their own listings, maintain base and SKU-variant stock, and provide product names and descriptions in supported languages. Each new or edited listing waits for Admin approval before appearing publicly. Category CRUD, localized storefront search, and seller ownership checks are included.
- Admin can approve or reject seller product submissions with a review note. Active storefront queries exclude pending listings; translated text is used when present and otherwise the source language is identified. Phase 3 catalog and inventory screens have Bengali, Hindi, and Arabic translations.
- Product images use a fail-closed pipeline: private quarantine, ClamAV CLI scan, JPEG/PNG/WEBP decoding and sanitizing, then upload to an S3-compatible bucket. A rejected or unscanned image stays outside public storage. The app returns an image URL only after external storage succeeds.
- To enable image publishing, install a ClamAV command (`clamdscan` by default; set `CATALOG_VIRUS_SCANNER` to another compatible executable if needed) in the app runtime. Set `CATALOG_MEDIA_BUCKET`, `CATALOG_MEDIA_REGION`, `CATALOG_MEDIA_PUBLIC_BASE_URL`, and, for S3-compatible storage, `CATALOG_MEDIA_ENDPOINT_URL`; provide credentials through the AWS SDK credential chain. The public URL host must be served by the configured bucket/CDN. Until scanner and storage are configured, image uploads are intentionally rejected. Configure these values as private service environment settings in deployment.
- Defaults: 3 MB per image, 40 million pixels, 100 MB total quarantine, and 24-hour quarantine retention. Override with the `MAX_CATALOG_*` and `CATALOG_QUARANTINE_*` settings as needed.
- The catalog seed supplies a small curated food, grocery, and retail category set. It does not generate pretend food listings or prices. USDA reference foods remain labeled as reference data until a seller publishes a priced, reviewed listing.
- Revision 20260929_07 adds seller ownership, product stock and review metadata, product translation records, and product variant records. Phase 3 is complete: the full test suite passes, and only the deployment-side scanner and storage configuration remains before live image publishing.

## Phase 4 complete

- A single customer cart is now split at checkout into **seller-specific sub-orders** that share a checkout group. Each sub-order carries its own item snapshot, a per-order delivery fee, and a cash-on-delivery total; the confirmation page lists every sub-order and an overall total.
- Every seller sub-order gets a **seller-specific invoice PDF** built with ReportLab. A Unicode TrueType font (covering Bengali, Hindi, and Arabic) is registered from `INVOICE_FONT_PATH` or a common system font so localized labels and product names render; amounts use the Taka symbol and dates follow the customer locale. Set `INVOICE_FONT_PATH` in deployment for full script coverage.
- Transaction email is durable: each message is rendered once and stored in the `outbound_emails` outbox, then delivered in the background. Failures are retried up to `MAX_EMAIL_ATTEMPTS`, and `flask --app run.py retry-emails` re-sends anything still pending. Diagnostics never log provider credentials.
- Order, invoice, and email copy is translated for **বাংলা**, **हिन्दी**, and **العربية**. (Adding `reportlab` to the requirements brings in the invoice renderer.)

## Phase 5 complete

- Admins assign an active Rider to an order from the dashboard. Delivery state is separate from order status and moves through validated transitions: unassigned → assigned → picked up → out for delivery → delivered, with a `failed` branch.
- The Rider dashboard lists active and completed deliveries and lets the assigned Rider advance each step. Marking an order delivered requires **proof of delivery** — an uploaded photo (JPEG/PNG/WEBP) or a written note — and records a timestamp for each stage.
- Only the assigned Rider (or an Admin) can change a delivery, and invalid transitions are rejected server-side. No live GPS is used in this release; the data model is ready for future location fields.

## Phase 6 complete

- **Audit trail:** the `audit_events` table records security-relevant actions (sign-in, sign-out, denied Admin codes, seller and product review, order status, delivery assignment and updates, settings changes). Events carry a keyed client-address hash and never store raw IP addresses or credentials. Recent activity is listed on the Admin dashboard.
- **Backup and restore:** `flask --app run.py backup-db --to <file>` writes a consistent, integrity-verified backup and `flask --app run.py restore-db --from <file> --confirm-target` restores it only after verification and explicit target confirmation. SQLite uses its online backup API; PostgreSQL uses `pg_dump`/`psql` when present in the runtime.
- **Database monitoring:** `flask --app run.py db-size` reports the size against the `MAX_DATABASE_BYTES` ceiling (default 400 MiB), and a backup refuses to run once the ceiling is exceeded.
- **Health probes:** `/health/live` checks that the web process responds without querying the database; `/health/ready` checks database readiness. `/health` and `/health/db` remain readiness aliases for existing deployments. Set `APP_TIMING_ENABLED=1` to expose app handling time in the standard `Server-Timing` response header; it does not write request logs or create log files.
- **Launch review:** `flask --app run.py production-check` lists remaining production blockers, including secret strength, secure cookies, HTTPS base URL, mail provider, TLS-required PostgreSQL, Admin bootstrap, invoice font, media storage, scan tooling, and live SSLCOMMERZ credentials.
- **Live media smoke check:** after configuring the deployment's ClamAV scanner and S3-compatible bucket/CDN, run `flask --app run.py catalog-media-smoke-check --confirm-external-write`. It sends one generated 1×1 PNG through the upload scanner and sanitizer, writes it to the configured bucket, verifies the object, and removes it. Run it only after confirming the active deployment environment and bucket permissions; it requires put, head, and delete access.
- **Operator steps (hosting account, not application code):** configure the chosen host with HTTPS, managed PostgreSQL, WAF/rate limits, scheduled backups and a restore drill; install/configure ClamAV and private quarantine, configure the product media bucket/CDN, and monitor database capacity. Follow [the public-launch checklist](docs/operations/public-launch.md).

## Stage 7 complete — online payments and seller settlement

- Checkout supports cash on delivery and SSLCOMMERZ hosted checkout in BDT. Online checkout creates one payment record for all seller-specific orders, reserves stock, and snapshots commission and the return window. Orders are released to sellers only after server-side transaction validation; failed, duplicate, mismatched, late, and risk-flagged callbacks have separate handling.
- Admin can reconcile payment attempts, review risk-flagged transactions, request and refresh eligible pre-shipment refunds, configure commission and the seller hold period, and record manual seller payouts. Seller balances become payable only after delivery plus the saved return-window period.
- Migration `20261009_16` adds payment, attempt, refund, commission-snapshot, payout, and seller-ledger persistence. Apply migrations with `flask --app run.py db upgrade`; existing COD checkout remains supported.
- For local sandbox checkout, set `SSLCOMMERZ_STORE_ID`, `SSLCOMMERZ_STORE_PASSWORD`, and a reachable `PUBLIC_BASE_URL`; leave `SSLCOMMERZ_SANDBOX=1`. For production, use private live credentials, `SSLCOMMERZ_SANDBOX=0`, canonical HTTPS callback URLs, an explicitly saved Admin commission (0% is valid), and verify live IPN/refund callbacks before accepting real payments. `flask --app run.py production-check` reports missing live payment configuration.
- Schedule `flask --app run.py expire-payments` periodically (for example, every few minutes) so timed-out unpaid checkouts release reserved stock even when customers do not revisit their payment page. It is safe to rerun.
- Manual payout records are accounting records only; Admin sends the bank/mobile-wallet transfer separately and saves its reference. Stage 7 does not store card details or perform automatic payouts.

## Stage 8 complete — returns and refunds

Customers can request eligible delivered-order returns and follow status and refund details in order history and the API. The owning Seller or Admin can review the request and mark returned goods received; Admin then starts an online provider refund or records a completed manual COD refund. Provider status refresh finalizes online returns and posts idempotent seller-ledger reversals. Apply migration `20261005_19` with `flask --app run.py db upgrade` before deploying. Live refund-provider confirmation still requires the Stage 7 SSLCOMMERZ operator setup.

## Stage 9 complete — discovery and promotions

The existing catalog supports typo-tolerant search and suggestions, category/price/store/brand/variant/stock filters, relevance and price sorting, a discounted-listings page, canonical URLs, and Product/Offer structured data. Admins can create and activate scheduled marketplace coupons or seller-scoped campaigns; approved sellers can create and manage their own dated deal codes. Checkout recalculates discounts from current server-side merchandise totals, allocates cents across seller orders, and records usage in the order transaction. Verification: 16 catalog/promotion tests passed, including the isolated migration check. Apply migration `20261011_18` before deployment. Evidence is recorded in the canonical master plan.

## Stage 10 in progress — production readiness

The focused security/operations/media/configuration suite passes 29 tests, covering health probes, opt-in timing, readiness configuration, media failure handling, PostgreSQL TLS enforcement, restore target confirmation, and CLI safety. The full project suite passed 204 tests in the 2026-10-05 audit. Live ClamAV/S3 upload, managed PostgreSQL, WAF/ingress, scheduled backups and isolated restore, monitoring, CDN delivery, and workload review still need hosting access and recorded operator evidence. Stage 11 has a verified recently-viewed-products slice; its other capabilities remain for separately scoped increments. Follow [the Stage 10 operations runbook](docs/operations/stage-10-runbook.md).

## Stage 12 complete — AI marketplace ecosystem

The shared AI Core connects the customer Shopping Assistant and Telegram bot with catalog, comparison, own-cart/order, and support tools; it also provides seller-reviewed listing help, read-only Admin and Security analysis, and bounded visual/voice search. The provider is disabled by default. Verification passed: 46 focused AI/Telegram tests and 257 full-suite tests; the isolated migration and CLI report the single head `20261006_26`. Apply migrations before deployment and keep `AI_API_KEY` plus Telegram credentials in private environment settings. Conversation history and customer image/audio uploads are not persisted. See [the AI marketplace operations guide](docs/operations/ai-marketplace.md) and the Stage 12 scope/acceptance trace in the [master plan](docs/plans/nexhaat-master-plan.md).

## Stage 13 in progress — local-first hybrid AI

Stage 13 adds a shared private local-model path for web and Telegram, opt-in memory and external-provider consent, capped specialist routing, scoped retrieval, local search/media adapters, and a protected Rider assistant. APIs remain disabled unless configured with user consent and a monthly spend cap. Voice recording appears only when private ASR is configured and uses that local transcription path; the page never falls back to browser speech recognition. Listen controls appear only when local TTS is configured. The additive migration is `20261007_27`; apply it with `flask --app run.py db upgrade`. This workspace has no private GPU host or staging bot delivery, so local model, PostgreSQL pgvector, media-service, and live Telegram acceptance remain operator gates. See [Stage 13 AI operations](docs/operations/stage-13-ai.md) and the status record in the [master plan](docs/plans/nexhaat-master-plan.md).

## Stage 14 in progress — Multimodal AI Builder and Project Guardian

Stage 14 adds an Admin-only Builder and Guardian in the existing Flask application. Admins can opt into private saved projects, generate starter or model-backed draft files, analyze bounded ZIP/text/PDF/DOCX/image/audio inputs, review diffs, run manual Guardian scans, and propose lessons from passing test evidence. Patches stay candidates until a restricted Docker sandbox passes and an Admin separately approves them; only then can they be applied to the saved project or exported. Guardian scan jobs are signed, high-risk notices are deduplicated, and deployment checks block only Admin-confirmed high-risk findings. The private-local hidden coding benchmark requires a configured model and the same sandbox. Project files are never extracted to the web root, and code is never run on the host or deployed automatically. The sandbox requires AI_BUILDER_SANDBOX_IMAGE set to an immutable image digest; Docker is unavailable in this workspace, so sandbox execution and patch approval remain blocked here. Private inference, embedding, and live Telegram staging checks are separate operator gates. See [AI Builder and Guardian operations](docs/operations/ai-builder-guardian.md), [AI marketplace operations](docs/operations/ai-marketplace.md), and the [master plan](docs/plans/nexhaat-master-plan.md).

For the **Astra/Luna/Sol/Forge specialist personas**, safe AI configuration checks, and the next “ultra hybrid AI” acceptance gates, see [Ultra Hybrid AI setup (Bangla)](docs/operations/ultra-ai-upgrade-bn.md). Run `python scripts/diagnose_ai.py` to inspect configuration without sending a model request; use `--probe-local` or `--probe-direct` only when you intentionally want to send a minimal test request.

Admin AI queries and Builder analysis runs generate prompt-free audit entries and retryable, metadata-only Security Bot notices, with a link back to the protected Admin AI workspace. The web workspace shows a per-Admin activity history and clearly identifies AI as read-only. In private chat, Security Bot `/approvals` supports only the enumerated marketplace decisions documented in the [Telegram operations guide](docs/operations/telegram-bots.md); each callback requires an allowlisted Telegram ID mapped to an active website Admin and reuses the same server-side decision rules. General Admin AI actions, deployments, and unsupported decisions remain website-only.

## Account management

- **Customers** can permanently delete their own account from Account Settings; this removes their profile, address, and sign-in.
- **The primary Admin** — the account whose email matches `ADMIN_EMAIL` — can delete Seller, Rider, and sub-Admin accounts from the Admin dashboard. The primary Admin account itself is protected and cannot be deleted.
- **Sub-Admins** are added by inviting them (`role = Admin`) from the Admin dashboard and sign in the same passwordless email-OTP way as the primary Admin.
- The Admin sign-in entry point (`/admin/login`) only accepts active Admin accounts. Any other email is refused with *"That email is not an Admin account."*

## Deployment

The project includes a production entry point and a `Procfile` that starts Gunicorn. Configure the host's release/deploy step to install dependencies, apply database migrations before serving traffic, and provision a strong secret, managed PostgreSQL URL, Brevo API key, sender address, canonical HTTPS `PUBLIC_BASE_URL`, and Admin bootstrap values through private environment settings.

Telegram customer and security bot configuration, account-linking, webhook registration, and Azure App Service deployment steps are documented in [the Telegram bots operations guide](docs/operations/telegram-bots.md). Configure the separate bot tokens and webhook secrets as private App Service settings; after applying the Telegram migrations, run `flask --app run.py set-telegram-webhooks` from the deployed environment. Schedule `flask --app run.py retry-telegram-alerts` if security alerts are enabled.

A public deployment should put a managed WAF/reverse proxy in front of the application where possible. That external account and network configuration is not created by application code. Security uses layered controls; no application can promise to be impossible to hack.

See [the Stage 10 operations runbook](docs/operations/stage-10-runbook.md) for the production setup and acceptance checklist.
