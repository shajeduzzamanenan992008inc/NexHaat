# NexHaat public-launch checklist

This is an operator checklist, not proof that a hosting account or third-party service has been configured. The app intentionally keeps live payments, outbound AI spending, and private integration credentials disabled until they are supplied explicitly.

## 1. Before exposing the site

- Use a currently supported **Linux Python 3.12** runtime, matching `runtime.txt` and the CI test runtime.
- Configure a managed PostgreSQL database. Use a TLS connection string, preferably `postgresql+psycopg://...?...sslmode=require`; percent-encode special characters in the username/password. Do not run a public production marketplace on the local SQLite database or a disposable app filesystem.
- Set host-managed environment variables/secrets. Do not upload `.env`, credentials, database exports, local uploads, or a backup to GitHub.
- Set `APP_ENV=production`, `FLASK_DEBUG=0`, `FLASK_TESTING=0`, `SESSION_COOKIE_SECURE=1`, a cryptographically random `SECRET_KEY` of at least 32 characters, canonical `PUBLIC_BASE_URL=https://...`, and `ADMIN_EMAIL`.
- Keep `WTF_CSRF_ENABLED` enabled. Do not add wildcard CORS, disable CSRF, or trust arbitrary `Host` headers.
- Configure HTTPS and a custom domain before public traffic. The smoke test expects HTTPS and the configured security headers.

Generate a secret on a trusted machine, then paste the result into the hosting provider's secret settings (not into source code):

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## 2. Azure App Service settings

The repository workflow targets the Azure Web App named `NexHaat`. In App Service:

1. Select Linux and Python 3.12; set the startup command to `gunicorn --workers 2 --threads 4 --timeout 120 --access-logfile - --error-logfile - "run:app"` if the platform does not automatically honor `Procfile`.
2. Enable build automation for deployments (`SCM_DO_BUILD_DURING_DEPLOYMENT=1`) so the platform installs `requirements.txt`. The GitHub workflow first compiles and tests the app before it deploys.
3. Add app settings under **Environment variables**. Use `.azure-app-settings.example.json` only as a template for Azure's Advanced Edit JSON format; it contains placeholders and must be reviewed before use. `.env.example` is the separate, standard dotenv template for local development.
4. Use GitHub Actions OIDC secrets already referenced by `.github/workflows/main_nexhaat.yml`; confirm they refer to the intended subscription, tenant, and Web App before pushing to `main`.
5. Add the GitHub repository variable `NEXHAAT_PUBLIC_BASE_URL=https://your-real-domain` to enable the workflow's read-only post-deploy smoke test. Without that variable, the workflow emits a warning and you must run the smoke test manually.

## 3. Database migrations and administrator

Deploying code does not upgrade a production database automatically. Run these once against the intended production database, preferably from a controlled release console and with a verified backup:

```bash
flask --app run.py db upgrade
flask --app run.py ensure-admin
flask --app run.py production-check
```

Do **not** put migrations in the web-worker startup command; multiple Gunicorn workers can race. Verify the configured `ADMIN_EMAIL` carefully before `ensure-admin`, because this setting is authoritative for the primary Admin account.

## 4. Features that need external services

The production readiness command lists missing items without revealing secret values. It is intentionally a strict full-marketplace gate: it reports mail, live payment, invoice font, antivirus, and media-storage gaps even when an operator plans to defer one of those integrations. Do not call the launch fully ready until the reported gates are resolved or the deployment plan explicitly scopes out those features and the related endpoints are kept unavailable:

- **Mail/OTP:** configure `BREVO_API_KEY`, an activated `MAIL_DEFAULT_SENDER`, and any needed support address; then run `flask --app run.py check-mail`.
- **Product images:** configure the ClamAV executable, private quarantine storage, an S3-compatible media bucket/CDN, and cloud credentials via the hosting identity/credential chain. Uploads deliberately fail closed without malware scanning and successful object storage. The web app's local filesystem is not durable shared media storage.
- **Invoices:** configure `INVOICE_FONT_PATH` to an installed Unicode font suitable for Bengali and other supported scripts.
- **Online payments:** keep `SSLCOMMERZ_SANDBOX=1` until credentials, callbacks, order reconciliation, refunds, and duplicate callback handling have been checked. Set live credentials and `SSLCOMMERZ_SANDBOX=0` only after payment-provider approval and staging verification. Cash on delivery should still be tested independently.
- **Telegram:** configure the intended bot tokens and webhook secrets in secret settings, point webhooks at the HTTPS domain, and run `flask --app run.py set-telegram-webhooks` from a controlled release environment. Confirm the callbacks arrive. Never place tokens or customer personal data in logs or reports.
- **Hybrid AI:** the default example has AI and paid external fallback disabled. To use a hosted OpenAI-compatible primary provider, configure `AI_ENABLED=1`, `AI_PROVIDER=openai_compatible`, `AI_API_KEY`, `AI_MODEL`, and `AI_BASE_URL`, and set `AI_LOCAL_ENABLED=0` if no private local endpoint will be used. For local-first operation, configure `AI_LOCAL_ENABLED=1`, `AI_LOCAL_BASE_URL`, and `AI_LOCAL_MODEL` (plus `AI_LOCAL_API_KEY` if needed). Do not expose a private GPU endpoint publicly without authentication and network restrictions.
- **Astra/Luna/Sol/Forge specialist providers:** configure real provider credentials and model IDs for each specialist you plan to call. Enter current per-token rates for paid models. Leave `AI_EXTERNAL_ENABLED=0` until external-call consent/notice delivery, provider availability, rate-limit behavior, and a finite positive monthly budget have been tested in staging. A nonzero budget alone does not make external requests safe to enable.

Never ship a real `.env.example` value containing live credentials. All keys must be stored as host secrets or deployment secret variables.

## 5. Pre-launch checks

From a controlled deployment console, run:

```bash
flask --app run.py production-check
python scripts/smoke_test.py --base-url https://your-real-domain
```

Also perform these manual release gates:

- Register test customer and seller accounts; confirm approval/role boundaries and password/OTP email delivery.
- Create a low-value COD order end-to-end. If online payment is enabled, use the provider sandbox first and test success, cancellation, timeout, mismatched totals, duplicate callback, and refund paths.
- Test seller listing approval, inventory changes, customer return flow, and admin audit records.
- Test AI-disabled behavior, configured local model success/failure, direct primary-provider behavior, external-consent denial, spend cap, and Telegram outage. Confirm no false success is shown when a backend operation fails.
- Verify backup creation, restore into an isolated database, and database size monitoring. Schedule backups at the host level.
- Check logs, dependency-update alerts, WAF/rate-limits, uptime alerts, database capacity, storage lifecycle/retention, and privacy/terms/refund pages.

A green HTTP smoke test is only a minimal availability/header check. It does not validate a live database migration, real payment, AI quality, webhooks, storage, load, or security against every attack.
