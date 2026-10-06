# Telegram Bots

The marketplace includes two independent Telegram integrations in the existing Flask application. The customer bot can search the live catalog and use a linked customer's shared web/API cart. The security bot is read-only and requires a numeric Telegram user-ID allowlist. Their webhook URLs and bot tokens are separate; no polling worker or new service is required.

## Configuration

Set these values as private Azure App Service application settings (or local environment variables). `.env.example` contains the App Service Advanced Edit JSON shape with empty secret values.

| Setting | Purpose |
| --- | --- |
| `TELEGRAM_CUSTOMER_BOT_TOKEN` | Customer bot token from BotFather |
| `TELEGRAM_CUSTOMER_WEBHOOK_SECRET` | Customer webhook header secret; 1–256 letters, digits, `_` or `-` |
| `TELEGRAM_SECURITY_BOT_TOKEN` | Separate security bot token from BotFather |
| `TELEGRAM_SECURITY_WEBHOOK_SECRET` | Separate security webhook header secret |
| `TELEGRAM_SECURITY_ADMIN_IDS` | Comma-separated immutable numeric Telegram user IDs; usernames are ignored |
| `TELEGRAM_SUPPORT_URL` | Optional support destination; production must use HTTPS |
| `TELEGRAM_RATE_LIMIT_PER_MINUTE` | Per-bot, per-Telegram-user request ceiling; default `30` |
| `TELEGRAM_API_TIMEOUT` | Telegram API timeout in seconds; default `10` |
| `PUBLIC_BASE_URL` | Canonical marketplace origin used to build links and webhook URLs |

Generate different unpredictable webhook secrets and bot tokens for each bot/environment. Keep secret settings private and slot-sticky. Never put secrets in source, logs, screenshots, the shared roadmap, or command-line arguments. Add at least one authorized numeric ID before enabling the security bot. Bot interactions that reveal account/cart/order/security information work only in private chats.

## BotFather

Create two separate bots and save their tokens only in the settings above. Configure command menus separately:

Customer bot: `/start`, `/shop`, `/products`, `/categories`, `/search`, `/cart`, `/orders`, `/account`, `/support`, `/help`, `/link`.

Security bot: `/start`, `/status`, `/health`, `/security`, `/alerts`, `/logins`, `/audit`, `/admins`, `/help`.

## Account Linking and Cart

A customer sends `/link` in a private chat, then signs in to the existing NexHaat account and enters the 10-digit, one-time code in Account settings. Codes are stored as keyed digests, expire after 10 minutes, and are rate-limited. The bot never asks for a password. A Telegram numeric ID can link to at most one customer; the customer can unlink from Account settings.

Authenticated web, API, and Telegram actions use the same database-backed cart. Guest carts remain in the signed session and are validated/merged after customer sign-in. Prices and stock are re-read from the catalog; checkout and payment remain in the authenticated marketplace, not in Telegram. Product search/categories are sourced from current approved/available catalog records. Order details are filtered by the linked account and omit phone/address/email.

## Deploy and Register Webhooks

1. Configure the App Service settings and use a public HTTPS `PUBLIC_BASE_URL`.
2. Back up the deployment database and apply migrations before serving the new application: `flask --app run.py db upgrade` (Telegram schema revisions `20261006_22`, `20261006_23`, and `20261006_24`).
3. Deploy the Flask application using the existing `Procfile`/App Service startup configuration.
4. In the deployed environment run `flask --app run.py set-telegram-webhooks`. It registers only configured bots, uses Telegram's secret-token header, preserves pending updates, and prints no token or webhook secret. Verify the CLI reports the expected endpoint for each bot.
5. Smoke-test customer `/start`, `/search`, account linking, shared cart and order-owner isolation. Verify an unallowlisted Telegram ID receives only `Access denied.` from the security bot.
6. Schedule `flask --app run.py retry-telegram-alerts` from the existing deployment scheduler/WebJob or another authorized scheduler. It retries queued alerts up to five attempts. Delivery is at-least-once; a transient failure after a partial multi-admin send can result in a duplicate alert.

The webhook endpoints are `/telegram/customer/webhook` and `/telegram/security/webhook`. Missing bot credentials fail closed with `503`; an invalid Telegram secret header returns a generic `403`. Local development needs a public HTTPS tunnel before Telegram can reach it. Do not use polling in production.

## Security Scope

The security bot reads health, existing audit events and existing login-throttle aggregates only. It does not execute commands, arbitrary queries, or account/firewall actions. Alerts are generated only from recorded admin-login denials and account-removal audit actions; payloads exclude emails, addresses, raw IPs, event details, tokens and secrets. The customer and security handlers, bot tokens, webhook routes and authorization rules are separate.

AI assistants are not part of this initial release. Product search and security summaries use deterministic server-side code; no AI provider or customer data is sent externally.

## Rollback

Disable a bot by clearing its token and webhook secret in App Service settings; its endpoint then fails closed. To stop Telegram delivery while preserving queued alerts, leave the security bot token unset and stop scheduling `retry-telegram-alerts`. Database downgrade removes Telegram identity/cart/outbox state and therefore should only be considered after an explicit data-retention decision; prefer rolling back application code while keeping additive tables until the next reviewed migration.
