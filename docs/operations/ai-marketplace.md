# AI marketplace operations

The shared AI Core is optional application functionality. Paid external providers are disabled by default; all secrets belong in private local or hosting environment settings. Do not paste API keys or Telegram tokens into source files, issue text, or the shared roadmap.

The local loader accepts the repository's Azure Advanced Edit JSON only when it declares `APP_ENV=development` and a SQLite `DATABASE_URL`. A production/PostgreSQL JSON settings file is deliberately ignored on a developer machine; Azure App Service supplies its Application Settings as environment variables. This avoids a local run accidentally using a production database or production bot credentials.

When AI appears unavailable, check `AI_LOCAL_ENABLED`, `AI_LOCAL_BASE_URL`, and `AI_LOCAL_MODEL` in the **active runtime settings**, plus GPU endpoint health and app-to-host networking. `AI_ENABLED` is for the legacy/direct compatibility provider and paid external providers have separate consent and budget controls. Reading an Azure settings export from a local `.env` file does not make those settings active locally or prove which values the hosted process currently has. A successful direct provider check also does not imply that a separate deployment has received the setting.

## Stage 12 direct-provider compatibility configuration

Set these settings only in a private environment when enabling the provider:

- `AI_ENABLED=true`
- `AI_PROVIDER=openai_compatible`
- `AI_API_KEY=<private provider key>`
- `AI_MODEL=<provider model that supports the requested capability>`
- `AI_BASE_URL=https://<provider-host>/v1`

This compatibility provider does not replace Stage 13's private local Core. With Stage 13 configured, ordinary questions use the local endpoint while `AI_ENABLED=false`; without a configured local endpoint, broad answers may fall back to an unavailable message. Catalog search still uses the marketplace database. Keep local development on a development/SQLite settings file and configure production values only in private hosting settings.

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
- An AI-assisted customer cart change is applied only after the customer confirms the current proposal; the confirmation is audited without item details and queued for a metadata-only Security Bot notice. Checkout and payment remain separate customer-controlled workflows.
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

The live provider may be tested safely with an isolated database and a short non-customer prompt. This verifies the configured provider endpoint and key but does not verify a deployed worker's environment. Do not print the answer, key, or provider response body into shared logs.

## Stage 13 local-first operation

Stage 13 keeps ordinary AI requests on the private local endpoint even when paid APIs are disabled. See the [Stage 13 host and model setup](stage-13-ai.md) for the GPU, embedding, Whisper, CosyVoice, SearXNG, PostgreSQL, indexing, and rollout gates. Local endpoint settings belong in the private runtime environment; the checked-in `.env.example` contains empty placeholders only.

Set `AI_LOCAL_ENABLED=true`, `AI_LOCAL_BASE_URL`, and the deployed `AI_LOCAL_MODEL` to enable local text/vision. The default external settings stay closed: `AI_EXTERNAL_ENABLED=false`, empty provider credentials, and a zero monthly budget. To allow a user to opt into external specialist assistance, set the external toggle, configure at least two current provider model IDs and their matching input/output rates, and choose a positive `AI_EXTERNAL_MONTHLY_BUDGET_USD`. Each user/account or Customer Telegram identity must also give consent. A missing consent, missing rate, disabled toggle, or exhausted reserve sends no paid request. Keep a provider-side spending limit configured too.

Revision `20261007_27` adds external-consent digests, monthly spend reservations, manual opt-in memory, scoped knowledge chunks, and the memory preference flag. PostgreSQL installations require the `vector` extension; SQLite stores vectors as JSON for local development. Memory defaults off and consists only of notes the account holder explicitly adds. Search sources must be public HTTPS links. Image analysis, transcription, and optional speech output use only their configured local endpoints. Uploaded image/audio and generated audio bytes are handled transiently and are not saved as chat history.

Security and Rider scopes never use external specialists. The Security Telegram bot remains restricted to allowlisted numeric IDs in private chats; general/coding responses require the local endpoint, while explicit `/health`, `/audit`, and security commands continue to use read-only application data. The Rider assistant reads only deliveries assigned to the authenticated Rider and does not change status or proof.

## Stage 14 Admin AI Builder and Project Guardian

`POST /admin/ai-builder/jobs` currently accepts one ZIP archive plus a bounded analysis prompt. It inspects source files in memory using the ZIP path, symlink, entry-count, expanded-size, per-file, and compression-ratio checks in `app/ai/builder/archives.py`; it skips common secret and generated directories, does not extract or execute files, and bounds source to the configured AI context (external source is further limited to 6,000 characters). The synchronous endpoint tries the Stage 13 local Core first. External code disclosure requires both existing Admin external-AI consent and `allow_external_code=true` for that upload; provider configuration, a positive spend budget, and delivered metadata-only Security Bot notices remain mandatory. The durable job record contains an archive digest, owner, counts, status, consent bit, and bounded result, but not the uploaded archive or source files. Admin owners can retrieve or delete their own job. Apply additive migration `20261007_30` before deploying this endpoint.

This is only the first analysis slice. It does not yet support saved projects, broad image/voice/document ingestion, generation, diffs/export, background workers, test execution, a disposable sandbox, manual/deployment/nightly scans, deployment blocking, Guardian-finding alerts, or approved lessons. Uploaded or generated code is never executed, merged, or deployed by this endpoint. Do not expose it as a patch runner or deployment scanner.

The Customer Shopping Assistant, Customer Telegram image/voice search, observed-price history/alerts, and confirmed cart flows remain supported features from prior work. They are not Builder or Project Guardian acceptance evidence. Stage 13 private GPU, PostgreSQL/vector, media-service, and webhook gates remain separate.
