# Stage 12 AI marketplace operations

The shared AI Core is optional application functionality. Its provider is disabled by default; all secrets belong in private local or hosting environment settings. Do not paste API keys or Telegram tokens into source files, issue text, or the shared roadmap.

The local loader accepts the repository's Azure Advanced Edit JSON only when it declares `APP_ENV=development` and a SQLite `DATABASE_URL`. A production/PostgreSQL JSON settings file is deliberately ignored on a developer machine; Azure App Service supplies its Application Settings as environment variables. This avoids a local run accidentally using a production database or production bot credentials.

## Configuration

Set these settings only in a private environment when enabling the provider:

- `AI_ENABLED=true`
- `AI_PROVIDER=openai_compatible`
- `AI_API_KEY=<private provider key>`
- `AI_MODEL=<provider model that supports the requested capability>`
- `AI_BASE_URL=https://<provider-host>/v1`

`AI_ENABLED=false`, an empty key, or missing model/base URL means broad natural-language answers are unavailable. Catalog search still uses the marketplace database; the assistant explains when it falls back. For local development, use a development/SQLite settings file and configure the provider settings there. For production, configure all five values in the hosting provider's private Application Settings and restart the app.

Bound resource use with `AI_TIMEOUT`, `AI_MAX_TOKENS`, `AI_MAX_TOOL_CALLS`, `AI_MAX_CONTEXT_SIZE`, `AI_RATE_LIMIT`, and `AI_RATE_LIMIT_WINDOW_SECONDS`. The application clamps request limits. A provider may not support vision or transcription; those functions then show a safe fallback to catalog search. `AI_ENABLED=false` keeps ordinary catalog, cart, orders, and support services available without a provider request.

Do not configure an untrusted provider URL. The configured base URL is treated as operator-controlled infrastructure and must use HTTPS in production. The adapter appends its supported chat, image, and transcription paths.

## Database and deployment

After backing up a deployment database, run:

```powershell
flask --app run.py db upgrade
```

The Stage 12 revisions add hashed AI request windows, opt-in alert preferences and weekly digest timestamps, plus explicitly submitted human support cases. They do not store AI prompts, generated chat transcripts, customer images, or voice recordings. Install and deploy the same code version only after the migration succeeds.

The optional daily in-app cart/recommendation digest is deterministic and does not call the AI provider or send email. Schedule this command once a day only if the operator wants these reminders:

```powershell
flask --app run.py smart-ai-notification-digest --limit 200
```

Customers must opt in from `/ai/preferences`. The product-change alerts and digest share a daily account-wide limit; cart reminders and recommendation picks each have a weekly limit. The command reports aggregate counts only.

## Scope and data behavior

- `/ai/chat`, visual search, and voice search are customer-only or guest catalog surfaces. Signed-in non-customer roles are denied. Private cart and order tools require the authenticated customer.
- Seller endpoints require an approved seller and query only that seller's records. AI-generated listing text is a draft; the usual listing form owns all writes.
- Admin AI is read-only and allows only Admin/Super-Admin. Review flags are hints for human moderation.
- Security AI is only available to numeric IDs in `TELEGRAM_SECURITY_ADMIN_IDS`, in a private chat. Its tools reveal minimized event metadata and cannot change accounts, logs, or system settings.
- Shopping Telegram and web chat use the same customer query service. A Telegram cart callback still validates the linked customer, product, variant, stock, and current service rules.
- Normal product pages and homepage personalization do not call the model. Personalization is deterministic from the signed-in customer's recent views, wishlist, cart, and purchases.
- Customer uploads are validated and processed in memory, then discarded. Do not add transcript/image persistence without a separate privacy and retention decision.

## Verification

Run focused mocked tests and the entire suite before completing Stage 12:

```powershell
python -m pytest tests/test_ai_core.py tests/test_ai_features.py tests/test_telegram_bots.py tests/test_app_entrypoints.py -q
python -m pytest -q
```

The test suite uses mocked provider/Telegram transport; no live provider key or bot token is required. Also run `flask --app run.py db heads` and confirm one head, validate `.env.example` as JSON, and run `git diff --check`. A live provider request is optional operator verification after private settings are configured; do not record secret values or customer prompt content in the shared plan.
