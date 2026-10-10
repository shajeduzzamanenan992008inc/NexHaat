# Development setup

The project targets Python 3.12 (`runtime.txt`).

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
flask --app run.py db upgrade
flask --app run.py ensure-admin
flask --app run.py seed-catalog
flask --app run.py run --host 127.0.0.1 --port 5009
```

Set a random `SECRET_KEY` (32+ characters) and an `ADMIN_EMAIL` in `.env`; the file is git-ignored and never committed, so keep local secrets in it. The development database is created in `instance/food_ordering.sqlite3`, and the repository ships the migration environment.

## Useful commands

```powershell
python -m pytest -q                    # run the test suite
python scripts/check_env_example.py    # check dotenv settings coverage
python scripts/smoke_test.py --base-url https://your-real-domain  # after deployment
flask --app run.py db-size             # database size against the 400 MiB ceiling
flask --app run.py backup-db --to backups/app.sqlite3
flask --app run.py restore-db --from backups/app.sqlite3
flask --app run.py retry-emails        # resend queued transactional email
flask --app run.py production-check    # production launch readiness review
```

Translation catalogs are refreshed with `pybabel extract`/`update` and compiled with `pybabel compile -d app/translations` (compile them during your build if your host does not do so automatically).



## Public launch

Review [docs/operations/public-launch.md](docs/operations/public-launch.md) before deployment. It covers Azure App Service settings, PostgreSQL/TLS, secret configuration, migrations, admin bootstrap, AI/payment/email/media setup, and post-deploy smoke tests.
