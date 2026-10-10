# Restore OpenRouter Free AI in local development

The most recent AI provider refactor made direct customer fallback require a positive external budget, model pricing, persisted external-call notice, and customer consent. The uploaded configuration uses OpenRouter's `openrouter/free` route with zero token rates, while the local loader intentionally does not import Telegram Security Bot secrets. Those combined gates can stop the call before it reaches OpenRouter.

## Local SQLite run

1. Keep your existing `.env` private. Do not commit it or upload it to a public repository.
2. Confirm your `.env` dotenv settings (or a legacy Azure JSON-array file) have the correct OpenRouter API key, `AI_PROVIDER=openai_compatible`, `AI_BASE_URL=https://openrouter.ai/api/v1`, and `AI_MODEL=openrouter/free`. Never print the key in a terminal screenshot.
3. Run `python scripts/enable_openrouter_free_local.py` from the project root. It validates the provider host/model, backs up `.env`, and turns on the dev-only metadata-notice mode. It does not change the key.
4. Start the project in development with SQLite, then run `flask --app run.py db upgrade` so the external-call notice/spend tables exist. Restart Flask after settings changes.
5. Open the customer AI page and explicitly enable **Allow external AI assistance**. Only eligible general questions without live-data, shopping, or account-specific needs can use this fallback.
6. Test `hello` first. The free model may still reject or rate-limit calls according to OpenRouter's current policy. Check the Flask terminal and browser Network response without sharing headers or secrets.

The local notice mode records metadata in SQLite and never contacts Telegram. It is guarded by both `ENVIRONMENT=development` and a SQLite database URL. Production must leave `AI_EXTERNAL_LOCAL_NOTICE_MODE=false`, configure the Security Bot token/admin recipients, maintain customer consent and an approved budget, and verify provider pricing. Do not set fake positive rates for a zero-priced model. The positive budget is an enablement gate; it cannot meter zero-cost requests, so retain application rate limits and the provider's limits.

## Undo

Restore the backup named `.env.backup-YYYYMMDD-HHMMSS` created by the script, or set `AI_EXTERNAL_ENABLED=false`, `AI_API_IS_FREE=false`, and `AI_EXTERNAL_LOCAL_NOTICE_MODE=false`.
