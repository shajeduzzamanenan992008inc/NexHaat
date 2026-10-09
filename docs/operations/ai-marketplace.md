# AI marketplace operations

The shared AI Core is optional application functionality. Paid external providers are disabled by default; all secrets belong in private local or hosting environment settings. Do not paste API keys or Telegram tokens into source files, issue text, or the shared roadmap.

The local loader accepts the repository's Azure Advanced Edit JSON only when it declares `APP_ENV=development` and a SQLite `DATABASE_URL`. A production/PostgreSQL JSON settings file is deliberately ignored on a developer machine; Azure App Service supplies its Application Settings as environment variables. This avoids a local run accidentally using a production database or production bot credentials.

When AI appears unavailable, check `AI_LOCAL_ENABLED`, `AI_LOCAL_BASE_URL`, and `AI_LOCAL_MODEL` in the **active runtime settings**, plus GPU endpoint health and app-to-host networking. `AI_ENABLED` is for the legacy/direct compatibility provider and paid external providers have separate consent and budget controls. Reading an Azure settings export from a local `.env` file does not make those settings active locally or prove which values the hosted process currently has. A successful direct provider check also does not imply that a separate deployment has received the setting.

With a configured model, every Customer chat message is sent to the AI Core together with bounded recent conversation, the effective locale, and role-scoped marketplace tools. The model—not a keyword-only route—decides whether to answer, clarify, or use catalog/account tools. If no model is configured or inference fails, common marketplace requests retain a deterministic, server-grounded catalog fallback; that fallback is not a general conversational AI. No endpoint, model ID, credential, or inference server is guessed or launched by the app.

## Stage 12 direct-provider compatibility configuration

Set these settings only in a private environment when enabling the provider:

- `AI_ENABLED=true`
- `AI_PROVIDER=openai_compatible`
- `AI_API_KEY=<private provider key>`
- `AI_MODEL=<provider model that supports the requested capability>`
- `AI_BASE_URL=https://<provider-host>/v1`

This compatibility provider does not replace Stage 13's private local Core. With Stage 13 configured, ordinary questions use the local endpoint while `AI_ENABLED=false`; without a configured local endpoint, broad answers may fall back to an unavailable message. Catalog search still uses the marketplace database. Keep local development on a development/SQLite settings file and configure production values only in private hosting settings.

## Configure and verify the local AI service

The Flask application is an OpenAI-compatible API client; this repository does not install, launch, or bundle an inference server or model. Start an approved OpenAI-compatible server separately, then use the exact base URL and model identifier supplied by that service. The API must implement `GET <base-url>/models` and `POST <base-url>/chat/completions`. The health probe calls only the models endpoint, has a short timeout, and returns no endpoint, model, or key values.

For a local development server, set the values in the same PowerShell session used to start Flask (replace each placeholder with the values from the running service; do not commit private settings):

```powershell
$env:AI_LOCAL_ENABLED = "true"
$env:AI_LOCAL_BASE_URL = "<exact-base-URL-from-your-running-OpenAI-compatible-service>"
$env:AI_LOCAL_MODEL = "<exact-model-ID-reported-by-that-service>"
# Set only if that local service requires authentication:
$env:AI_LOCAL_API_KEY = "<private-service-key>"
flask --app app run --host 127.0.0.1 --port 5009
```

Unset `AI_LOCAL_API_KEY` if the local service does not require a key. Plain HTTP is accepted only for loopback hosts in non-production environments; non-loopback and production endpoints must use HTTPS. Use `GET /ai/health` or the status message on the AI page to distinguish missing settings from a configured but unreachable service. This endpoint is a connectivity check, not proof that the selected model can successfully generate a chat response.

The checked-in `.env.example` is an Azure settings export example, not an active local environment file. The local loader intentionally ignores production/PostgreSQL settings exports; set development values in the active process environment or in the accepted development/SQLite settings file. For a paid direct provider instead, configure `AI_ENABLED`, `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`, and `AI_BASE_URL` as described above; do not configure secrets in source control.

When using this direct API instead of the private local endpoint, set `AI_LOCAL_ENABLED=false` to make the selection explicit. To keep local inference primary and use the direct API only when local generation fails, leave `AI_LOCAL_ENABLED=true` and configure both provider paths. The API fallback is restricted to general Customer AI questions; it does not receive chat history, marketplace facts, or tool results, and it never handles Security/Rider requests or live-data queries.

The local-first API fallback is paid external assistance. It sends no request unless `AI_EXTERNAL_ENABLED=true`, the customer has explicitly enabled external assistance, a positive `AI_EXTERNAL_MONTHLY_BUDGET_USD` is available, both `AI_API_INPUT_USD_PER_MILLION` and `AI_API_OUTPUT_USD_PER_MILLION` match the selected model's current rates, and a metadata-only Security Bot notice is successfully delivered. Configure a provider-side spending cap as well. Keep all API keys in private runtime settings.

Alternatively, one completely configured provider in `AI_SPECIALISTS` may
answer a general Customer question when Local AI is missing or unavailable,
under the same external opt-in, budget, and notice gates. This fallback is
blocked for catalog searches and any prompt requiring live or account-scoped
marketplace data. The multi-specialist comparison path still requires at least
two configured specialists.

For both modes, configure the private local model and API values together:

```env
AI_LOCAL_ENABLED=true
AI_LOCAL_BASE_URL=https://<private-local-endpoint>/v1
AI_LOCAL_MODEL=<local-model-id>
AI_ENABLED=true
AI_PROVIDER=openai_compatible
AI_API_KEY=<private-api-key>
AI_MODEL=<api-model-id>
AI_BASE_URL=https://api.openai.com/v1
AI_EXTERNAL_ENABLED=true
AI_EXTERNAL_MONTHLY_BUDGET_USD=<positive-monthly-cap>
AI_API_INPUT_USD_PER_MILLION=<current-model-input-rate>
AI_API_OUTPUT_USD_PER_MILLION=<current-model-output-rate>
```

The Security Bot token and allowlisted Admin IDs must also be configured so the metadata-only notice can be delivered before an API fallback call. Customers separately enable external assistance from their AI preferences. Do not put real keys or provider prices in the checked-in example settings.

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
- Customer AI catalog cards link to product details and can compare two displayed, live catalog results. Signed-in customers can request an add-to-cart proposal, review the current server-quoted product/variant price, and explicitly confirm it; checkout remains a separate protected marketplace step. Guest and non-customer sessions do not receive cart controls.
- Normal product pages and homepage personalization do not call the model. Personalization is deterministic from the signed-in customer's recent views, wishlist, cart, and purchases.
- Customer uploads are validated and processed in memory, then discarded. Do not add transcript/image persistence without a separate privacy and retention decision.
- Provider output matching explicit internal-reasoning or scratchpad markers is rejected and replaced by the safe fallback; raw reasoning is not returned to web or Telegram clients.

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

Set `AI_LOCAL_ENABLED=true`, `AI_LOCAL_BASE_URL`, and the deployed `AI_LOCAL_MODEL` to enable local text/vision. The default external settings stay closed: `AI_EXTERNAL_ENABLED=false`, empty provider credentials, and a zero monthly budget. To allow a user to opt into external specialist assistance, set the external toggle, configure at least two current provider model IDs and their matching input/output rates, and choose a positive `AI_EXTERNAL_MONTHLY_BUDGET_USD`. Each user/account or Customer Telegram identity must also give consent. Guest web consent is a session-scoped checkbox that defaults off; signed-in Customers use AI preferences. A missing consent, missing rate, disabled toggle, or exhausted reserve sends no paid request. Keep a provider-side spending limit configured too.

Revision `20261007_27` adds external-consent digests, monthly spend reservations, manual opt-in memory, scoped knowledge chunks, and the memory preference flag. PostgreSQL installations require the `vector` extension; SQLite stores vectors as JSON for local development. Memory defaults off and consists only of notes the account holder explicitly adds. Search sources must be public HTTPS links. Image analysis, transcription, and optional speech output use only their configured local endpoints. The customer page exposes recording only when local ASR settings are present and Listen only when local TTS settings are present; browser speech recognition is not used. Uploaded image/audio and generated audio bytes are handled transiently and are not saved as chat history.

Security and Rider scopes never use external specialists. The Security Telegram bot remains restricted to allowlisted numeric IDs in private chats; general/coding responses require the local endpoint, while explicit `/health`, `/audit`, and security commands continue to use read-only application data. The Rider assistant reads only deliveries assigned to the authenticated Rider and does not change status or proof.

## Stage 14 Admin AI Builder and Project Guardian

`POST /admin/ai-builder/jobs` currently accepts one ZIP archive plus a bounded analysis prompt. It inspects source files in memory using the ZIP path, symlink, entry-count, expanded-size, per-file, and compression-ratio checks in `app/ai/builder/archives.py`; it skips common secret and generated directories, does not extract or execute files, and bounds source to the configured AI context (external source is further limited to 6,000 characters). The synchronous endpoint tries the Stage 13 local Core first. External code disclosure requires both existing Admin external-AI consent and `allow_external_code=true` for that upload; provider configuration, a positive spend budget, and delivered metadata-only Security Bot notices remain mandatory. The durable job record contains an archive digest, owner, counts, status, consent bit, and bounded result, but not the uploaded archive or source files. Admin owners can retrieve or delete their own job. Apply additive migration `20261007_30` before deploying this endpoint.

The workspace now includes opt-in saved projects, transient bounded image/voice/document/ZIP analysis, starter and model-backed drafts, reviewable patch candidates, digest-pinned Docker test execution, signed manual/deployment/nightly Guardian scans, deduplicated finding notices, and sanitized test-backed lessons. The detailed operator procedure and security limits are in the [AI Builder and Guardian guide](ai-builder-guardian.md). Uploaded or generated code is never executed on the Flask host or deployed automatically.

The Customer Shopping Assistant, Customer Telegram image/voice search, observed-price history/alerts, and confirmed cart flows remain supported features from prior work. They are not Builder or Project Guardian acceptance evidence. Stage 13 private GPU, PostgreSQL/vector, media-service, and webhook gates remain separate.
