# Telegram Bots

The marketplace includes two independent Telegram integrations in the existing Flask application. The customer bot can search the live catalog and use a linked customer's shared web/API cart. The security bot provides read-only security/AI notices and identity-bound Admin approval actions in private chats. Write actions require both a numeric Telegram user-ID allowlist and an explicit binding to an active website Admin account. Their webhook URLs and bot tokens are separate; no polling worker or new service is required.

Telegram is a first-class interface for future feature work, not only AI. For each suitable marketplace feature, assess whether the Customer bot or the Security bot should expose it and add focused bot tests when it does. Reuse the same application services and enforce the same ownership, role, consent, validation, and transaction rules rather than duplicating business logic in Telegram handlers. Keep workflows that need a protected web experience or stronger confirmation on that surface and document the boundary.

## Configuration

Set these values as private Azure App Service application settings (or local environment variables). `.env.example` contains the App Service Advanced Edit JSON shape with empty secret values.

| Setting | Purpose |
| --- | --- |
| `TELEGRAM_CUSTOMER_BOT_TOKEN` | Customer bot token from BotFather |
| `TELEGRAM_CUSTOMER_WEBHOOK_SECRET` | Customer webhook header secret; 1–256 letters, digits, `_` or `-` |
| `TELEGRAM_SECURITY_BOT_TOKEN` | Separate security bot token from BotFather |
| `TELEGRAM_SECURITY_WEBHOOK_SECRET` | Separate security webhook header secret |
| `TELEGRAM_SECURITY_ADMIN_IDS` | Comma-separated immutable numeric Telegram user IDs; usernames are ignored |
| `TELEGRAM_SECURITY_ADMIN_USER_MAP` | Comma-separated `<telegram_user_id>:<website_user_id>` bindings for active Admin/Super-Admin accounts; required for Security Bot data and approval actions |
| `TELEGRAM_SUPPORT_URL` | Optional support destination; production must use HTTPS |
| `TELEGRAM_RATE_LIMIT_PER_MINUTE` | Customer Bot per-user request ceiling; default `30` |
| `TELEGRAM_SECURITY_RATE_LIMIT_PER_MINUTE` | Security Bot per-user request ceiling; default `10`, independently configurable |
| `TELEGRAM_API_TIMEOUT` | Telegram API timeout in seconds; default `10` |
| `PUBLIC_BASE_URL` | Canonical marketplace origin used to build links and webhook URLs |

Generate different unpredictable webhook secrets and bot tokens for each bot/environment. Keep secret settings private and slot-sticky. Never put secrets in source, logs, screenshots, the shared roadmap, or command-line arguments. Before enabling the Security Bot, bind each allowlisted numeric Telegram ID to the corresponding active website Admin/Super-Admin in `TELEGRAM_SECURITY_ADMIN_USER_MAP`. Security data and approvals require both checks. Bot interactions that reveal account/cart/order/security information work only in private chats.

## BotFather

Create two separate bots and save their tokens only in the settings above. Configure command menus separately:

Customer bot: `/start`, `/shop`, `/products`, `/categories`, `/search`, `/price-history`, `/price-alert`, `/cart`, `/orders`, `/account`, `/support`, `/help`, `/link`, `/ai-consent`, `/ai-revoke`.

Security bot: `/start`, `/status`, `/health`, `/security`, `/alerts`, `/logins`, `/audit`, `/admins`, `/approvals`, `/help`.

## Account Linking and Cart

A customer sends `/link` in a private chat, then signs in to the existing NexHaat account and enters the 10-digit, one-time code in Account settings. Codes are stored as keyed digests, expire after 10 minutes, and are rate-limited. The bot never asks for a password. A Telegram numeric ID can link to at most one customer; the customer can unlink from Account settings.

Authenticated web, API, and Telegram actions use the same database-backed cart. Guest carts remain in the signed session and are validated/merged after customer sign-in. Prices and stock are re-read from the catalog; checkout and payment remain in the authenticated marketplace, not in Telegram. Product search/categories are sourced from current approved/available catalog records. Order details are filtered by the linked account and omit phone/address/email.

The Customer bot supports `/price-history <product name>` using only prices NexHaat has actually observed; no older history is fabricated. A linked customer can set `/price-alert <target BDT price> <product name>` or cancel it with `/price-alert off <product name>` in a private chat. Alerts are explicit opt-ins and their price-crossing notifications are delivered to the customer's in-app inbox. Ambiguous product names require a more specific name.

Customer free-text messages also support greetings, product browsing/search, category lists, budget recommendations, cart/order questions, support navigation, add-to-cart selection, and product comparisons. Recommendations use currently available catalog listings, the stated budget, and approved review ratings; ambiguous comparisons ask for exact product names. For 30 minutes, the bot can resolve ordinal and selected-product follow-ups such as “second product ta koto?”, “compare first and third”, “show the cheaper one”, and “eta cart e dao” against the recent live results. Context stores only product slugs and the selected slug under an HMAC of the Telegram user ID; it does not store message text or transcripts. If the reference is ambiguous, the bot asks which product rather than guessing. Personal cart/order data is available only in a private chat to the linked customer. An add-to-cart prompt presents product buttons but does not change the cart until the customer explicitly selects Add.

## Deploy and Register Webhooks

1. Configure the App Service settings and use a public HTTPS `PUBLIC_BASE_URL`.
2. Back up the deployment database and apply migrations before serving the new application: `flask --app run.py db upgrade` (current Telegram/AI schema includes revisions through `20261008_32`).
3. Deploy the Flask application using the existing `Procfile`/App Service startup configuration.
4. Confirm the canonical HTTPS host resolves publicly and `GET /health/live` returns `200` with `{"status":"ok"}`. Run `flask --app run.py set-telegram-webhooks` to register every configured bot, or add `--bot customer` / `--bot security` to register one bot. The command refuses to change webhooks when the public app fails its liveness check. It uses Telegram's secret-token header, preserves pending updates, and prints no token or webhook secret. Configure the Security allowlist before registration.
5. Smoke-test customer `/start`, `/search`, account linking, shared cart and order-owner isolation. Verify an unallowlisted or unmapped Telegram ID receives only an access-denied response from the Security Bot. For each Admin Telegram user, include the numeric Telegram ID in `TELEGRAM_SECURITY_ADMIN_IDS` and bind it to the active website Admin's numeric database user ID in `TELEGRAM_SECURITY_ADMIN_USER_MAP` (for example, `123456789:42`). Verify read-only commands and `/approvals` work only for mapped active Admins, and callbacks record the mapped Admin as actor. Do not rely on Telegram usernames or shared group chats for authorization.
6. Schedule `flask --app run.py retry-telegram-alerts` from the existing deployment scheduler/WebJob or another authorized scheduler. It retries queued alerts up to five attempts and remembers successful recipients, so later attempts skip Admins who already received that alert. A delivery accepted by Telegram immediately before a network failure or process crash may still be repeated because the remote send and local database cannot share a transaction.

The webhook endpoints are `/telegram/customer/webhook` and `/telegram/security/webhook`. Missing bot credentials fail closed with `503`; an invalid Telegram secret header returns a generic `403`. Requests above the application-wide 4 MB body limit are rejected. Per-user throttles are persisted separately for each bot; the first over-limit update receives a wait-and-retry notice and further excess updates in the same minute are dropped without generating repeated replies. A bot API token can work for outbound messages while no webhook is registered for inbound updates; inspect `getWebhookInfo` when users receive no reply. Local development needs a public HTTPS tunnel before Telegram can reach it. Do not use polling in production.

## Security Scope

The security bot reads health, audit events and login-throttle aggregates. Every security-data command and AI query requires both an allowlisted numeric Telegram ID and a mapping to an active website Admin/Super-Admin. It does not execute commands, arbitrary queries, or account/firewall actions. In a private chat, `/approvals` can approve/reject pending seller applications, product listings and reviews; approve validated payment risk reviews and return requests; and confirm eligible pending orders (or decline COD orders). Each callback rechecks the pending state and mapped active Admin before applying the same marketplace rules/services used by the website, and records the mapped website Admin as the audit actor. Stale or unsupported decisions are rejected. Decisions requiring a rejection note, such as return rejection, remain website-only. Both surfaces show the same resulting marketplace state.

Alerts cover recorded security events, Admin AI lifecycle actions and Admin approval decisions; payloads exclude emails, addresses, raw IPs, event details, prompts, source, tokens and secrets. An AI proposal is not itself an action: customer cart changes still require explicit customer confirmation, and only a confirmed change generates an AI-action notice. The customer and security handlers, bot tokens, webhook routes and authorization rules are separate.

The customer Shopping Assistant and Customer Telegram bot share the same local-first AI Core. Customer free text may receive general, coding, or catalog-grounded answers, and the AI answer is returned in Telegram; catalog, cart, order, policy, observed-price, and alert operations continue to use authoritative marketplace services. A Customer Telegram user can send `/ai-consent yes` to opt into paid external help for complex prompts, and `/ai-revoke` to turn that consent off. External help additionally requires the application-wide toggle, two configured specialists, current price rates, and available monthly budget. Every individual external specialist or verifier request also requires successful delivery of its metadata-only Security Bot notice first; failed notice delivery blocks that request. Security Bot general/coding prompts use the local model only; security records, tool results, and private role data are never sent to an external provider. `/health`, `/audit`, and security commands remain backed by read-only application data.

Both bots accept Telegram OGG voice notes up to 8 MB and transcribe them through the configured private local ASR service (`AI_ASR_BASE_URL` and `AI_ASR_MODEL`). Without local ASR, the bot asks the user to type instead; it does not send audio to an external specialist. When local speech output is configured (`AI_TTS_BASE_URL` and `AI_TTS_MODEL`), a voice question also receives an optional synthesized audio reply alongside its text answer. Security voice questions remain restricted to allowlisted private chats.

The Customer bot also accepts product photos up to 5 MB in JPEG, PNG, or WebP. It validates and normalizes the image in memory, uses the configured local vision service, then sends the resulting description to the same catalog-grounded AI Core as text search. The source and normalized image are not persisted; personal recommendations are only enabled in private chat.

The shared Core can be checked after the private model is configured with
`flask --app run.py benchmark-ai`. The benchmark explicitly disables external
specialists and does not save or print answers. It measures the model/Core, not
Telegram webhook delivery or Telegram formatting; use the bot tests and a
private staging chat for those separate checks.

Admin AI query and Builder-analysis lifecycle events are added to the existing
audit-backed Security Bot alert queue. Notices are sent immediately when
possible and remain retryable with `flask --app run.py retry-telegram-alerts`.
They include only a generic action label, severity, and UTC time—never the
Admin prompt, AI answer, project contents, or private data. When
`PUBLIC_BASE_URL` is valid, an inline button opens the Admin AI workspace and
still requires normal website authentication and CSRF protection. The AI
workspace also lists the signed-in Admin's recent metadata-only activity.

Admin AI is read-only: it cannot approve sellers/products, confirm orders or
payments, change accounts, or deploy code. The Security Bot exposes only the
explicit, identity-bound marketplace approval actions documented in this file;
it has no general AI write tool. Website and Telegram decisions update the same
protected marketplace records.

Migration `20261007_27` adds AI consent, spend reservations, scoped retrieval, and explicit memory preference state; apply it with `flask --app run.py db upgrade`. Telegram inbound delivery still requires a healthy, publicly resolvable HTTPS webhook after deployment. Local mocked tests do not prove that a production Telegram update reaches the current Flask release. See [Stage 13 AI operations](stage-13-ai.md) for model service and operator acceptance steps.

## Rollback

Disable a bot by clearing its token and webhook secret in App Service settings; its endpoint then fails closed. To stop Telegram delivery while preserving queued alerts, leave the security bot token unset and stop scheduling `retry-telegram-alerts`. Database downgrade removes Telegram identity/cart/outbox state and therefore should only be considered after an explicit data-retention decision; prefer rolling back application code while keeping additive tables until the next reviewed migration.
