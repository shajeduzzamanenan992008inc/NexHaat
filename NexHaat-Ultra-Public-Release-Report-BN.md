# NexHaat — Public Release Hardening Report (বাংলা)

## কী আপডেট হয়েছে

- `.env.example`-কে সাধারণ dotenv `KEY=value` ফরম্যাটে রাখা হয়েছে; এতে ১০৫টি unique setting আছে।
- Azure App Service-এর Advanced Edit JSON-এর জন্য আলাদা `.azure-app-settings.example.json` রাখা হয়েছে। এটিতে ১০৫টি unique setting আছে; secret-এর ঘর blank এবং production placeholder স্পষ্টভাবে চিহ্নিত।
- `app/config.py`-এ malformed/out-of-range integer environment setting এলে startup-এ অনিয়ন্ত্রিত exception না দিয়ে validated fallback ব্যবহারের ব্যবস্থা যোগ করা হয়েছে।
- `requirements.txt`-এ runtime dependency রাখা হয়েছে; testing dependency `requirements-dev.txt`-এ আলাদা করা হয়েছে। Psycopg v3 ব্যবহারকারী SQLAlchemy URL-এর সঙ্গে সামঞ্জস্য রাখতে অপ্রয়োজনীয় `psycopg2-binary` সরানো হয়েছে।
- GitHub Actions workflow-তে Python compile, environment-template validation এবং full pytest suite deploy-এর আগে বাধ্যতামূলক। সফল test artifact-ই Azure deploy job-এ ব্যবহৃত হবে।
- Deployment artifact থেকে `.env`, SQLite/DB, local uploads, logs, backups, virtualenv ও cache বাদ দেওয়া হয়েছে।
- `scripts/check_env_example.py` দিয়ে missing/duplicate environment key এবং example-এ accidental secret value খোঁজার validation যোগ করা হয়েছে।
- `scripts/smoke_test.py` দিয়ে read-only HTTPS, health/readiness endpoint ও security-header check করা যায়।
- `docs/operations/public-launch.md`-এ production hosting, database, admin setup, payment, mail, media, Telegram, AI ও post-deploy validation-এর checklist যোগ করা হয়েছে।
- Setup/README/operations docs-এ dotenv এবং Azure JSON template-এর পার্থক্য পরিষ্কার করা হয়েছে।

## এই পরিবেশে চালানো যাচাই

- `python -m compileall -q app scripts run.py wsgi.py` — **PASS**
- `python scripts/check_env_example.py` — **PASS**: ১০৫টি unique key; app source-এ statically referenced ১০৪টি environment key কভার করা হয়েছে; example template-এ non-demo secret value পাওয়া যায়নি।
- Azure settings JSON parsing/uniqueness — **PASS**: ১০৫টি unique setting। Secret-সংক্রান্ত value blank বা documented placeholder।
- Smoke-test manual harness — **PASS**: healthy HTTPS/readiness; readiness `503` হলে fail; public HTTP এবং origin ছাড়া URL প্রত্যাখ্যান করা হয়।
- Full pytest suite — **এই execution environment-এ চালানো যায়নি**: `Flask` dependency অনুপস্থিত এবং package index-এ network/DNS access না থাকায় dependency install করা যায়নি। GitHub Actions runner `requirements-dev.txt` install করে full suite চালানোর জন্য কনফিগার করা হয়েছে।
- Real Azure deployment, live AI provider, payment, email, Telegram webhook, production DB migration/restore/load/security penetration test — **চালানো হয়নি**; এর জন্য তোমার host/provider credentials ও deployed environment দরকার।

## পাবলিক hosting-এর আগে বাধ্যতামূলক

1. `.env.example`-কে সরাসরি production `.env` হিসেবে ব্যবহার করবে না। Host-এর secret manager-এ random `SECRET_KEY` (কমপক্ষে ৩২ অক্ষর), `APP_ENV=production`, `FLASK_DEBUG=0`, `FLASK_TESTING=0`, `SESSION_COOKIE_SECURE=1`, HTTPS `PUBLIC_BASE_URL`, এবং TLS-enabled managed PostgreSQL configure করো।
2. `.azure-app-settings.example.json`-এর database URL ও secret placeholders বাস্তব host settings দিয়ে প্রতিস্থাপন করো; sample placeholder রেখে app চালু করো না।
3. Confirm করো host Python 3.12 ব্যবহার করছে, build automation enabled, and startup command uses `gunicorn --workers 2 --threads 4 --timeout 120 --access-logfile - --error-logfile - "run:app"` if `Procfile` is not automatically honored.
4. Backup যাচাই করে একবার controlled console-এ চালাও: `flask --app run.py db upgrade`, তারপর `flask --app run.py ensure-admin`, তারপর `flask --app run.py production-check`। Admin email আগে double-check করো।
5. Mail/OTP, ClamAV upload scanning, private quarantine, durable media storage, Bengali invoice font, live payment callback/reconciliation, Telegram webhook, এবং AI-provider secret/consent/budget আলাদাভাবে configure ও staging-এ পরীক্ষা না করা পর্যন্ত সংশ্লিষ্ট feature-কে production-ready বলো না।
6. GitHub repo variables-এ `NEXHAAT_PUBLIC_BASE_URL=https://...` দিলে deploy-এর পর workflow read-only smoke test করবে। Branch protection ও GitHub OIDC/Azure identity permissions review করো।
7. Original uploaded archive-এ Git history ও local SQLite database ছিল। Release ZIP-এ `.git`, local DB, `.env`, uploaded user media ও local runtime/cache বাদ দেওয়া হয়েছে। পূর্বে Git history বা public repo-তে আসল credential commit হয়ে থাকলে সেগুলো revoke/rotate করো।

## Release-এর সীমা

এই deliverable হলো hardened source release, সফল live production launch-এর প্রমাণ নয়। Public host-এ AI model, SMTP/mail, live payment, Telegram, managed DB, persistent media storage ও domain/HTTPS বাস্তব credentials/service settings ছাড়া চালু হবে না। Production readiness-এর রিপোর্টে থাকা blocker সমাধান করে staging acceptance tests pass করার পরেই public traffic দাও।
