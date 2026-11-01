# Phase 18 — Backup, Restore, and Disaster Recovery Readiness

**Date:** 2026-11-01  
**Status:** PARTIAL / BLOCKED for restore rehearsal and production DR proof  
**Scope:** Read-only recovery audit plus isolated local SQLite backup integrity
comparison. No live or production database was restored, overwritten, deleted,
or exported.

## Executive summary

The repository has an additive backup implementation with SQLite online-backup
support, PostgreSQL `pg_dump`/`psql` helpers, integrity checks, database-size
limits, explicit restore-target confirmation, and release/backup runbooks.
An isolated local backup was created outside the repository and compared to the
configured local SQLite source. Both databases passed SQLite integrity checks,
contained the same 53 application tables, had no row-count mismatches, and had
identical inspected schema objects.

A restore rehearsal remains **BLOCKED**: the available restore command writes
over the configured application database, and no separate disposable restore
target/environment was available. Production was not used as a substitute.
Backup creation and integrity comparison do not prove disaster recovery.

## Backup implementation inventory

| Component | Evidence | Status |
|---|---|---|
| SQLite backup | `app/services/backup.py::backup_database` uses SQLite online backup API | PASS by source inspection |
| SQLite validation | Read-only open, `PRAGMA integrity_check`, required `users` table | PASS by source inspection and execution |
| PostgreSQL backup | `pg_dump --no-owner --file ... DATABASE_URL` when `pg_dump` exists | PASS by source inspection; NOT TESTED locally |
| SQLite restore | Validates source, disposes session/engine, copies into configured target, validates target | PASS by source inspection; NOT EXECUTED |
| PostgreSQL restore | `psql -v ON_ERROR_STOP=1 -f ... DATABASE_URL` when `psql` exists | PASS by source inspection; NOT TESTED |
| Restore safety | CLI requires `--confirm-target`; source must differ from active SQLite file | PASS by source inspection |
| Size guard | `MAX_DATABASE_BYTES` default 400 MiB and backup ceiling check | PASS by source inspection |
| Operational docs | `.github/runbooks/backup-restore.md`, `.github/runbooks/production-release.md`, Stage 10 runbook | PASS by source inspection |

## Backup integrity evidence

Command executed previously and reused as the isolated artifact:

```powershell
python -m flask --app run.py backup-db --to C:\Users\enan9\.copilot\session-state\c67885d9-0c60-477b-80ea-1612d94e67c7\files\phase16-local-backup.sqlite3
```

Result: **PASS** — “Backup verified and written”; backup size **913,408 bytes**.
The artifact is outside the repository and is not a production backup.

Read-only source/backup comparison:

```text
source_integrity ok
backup_integrity ok
same_tables True
source_tables 53 backup_tables 53
count_mismatches []
same_schema_objects True
```

The local source database was not modified. No user-data contents were printed
or included in this report.

## Restore rehearsal

**BLOCKED — not executed.** `restore-db --help` confirms the command requires
`--from FILE` and `--confirm-target`; implementation restores over the
configured application database. The workspace has no separate disposable
restore database, PostgreSQL instance, or approved isolated target. Running it
against `instance/food_ordering.sqlite3` would overwrite the active local
database and violate the zero-loss boundary.

Safe future rehearsal:

1. Provision a disposable SQLite file or isolated PostgreSQL database containing
   synthetic, non-customer data.
2. Apply the current migration head and record the source schema/version.
3. Create and verify a backup.
4. Restore to a different empty target, never the active source.
5. Compare schema, table counts, foreign keys, representative commerce state,
   media references, and migration head.
6. Measure restore duration and record backup identity, validation output, RPO,
   and RTO.
7. Destroy only the disposable target after explicit approval.

## Data and dependency recovery inventory

- **Database:** local SQLite file; production is expected to use managed
  PostgreSQL with TLS-required connection settings.
- **Uploaded files:** profile, branding, delivery-proof, quarantine, and
  catalog-media paths are configuration-dependent. Local `uploads/` contained
  no files; `instance/food_ordering.sqlite3` was 913,408 bytes.
- **Catalog media:** production requires S3-compatible storage, public/CDN URL,
  ClamAV scanning, and object-level permissions; database backup alone does not
  recover media objects.
- **Configuration:** secrets, mail/SMS/payment credentials, Firebase/AI keys,
  media credentials, invoice font, and Azure OIDC settings are external
  operator-managed dependencies and were not accessed.
- **Queues/outbox:** transaction email and background operational tasks require
  reconciliation after restore; queued state and provider delivery status need
  separate recovery procedures.
- **Commerce reconciliation:** payments, refunds, inventory reservations,
  seller ledgers, and order events require provider reconciliation before
  reopening checkout.

## Azure recovery prerequisites

The existing deployment workflow and runbook require:

- exact known-good release SHA/artifact identity;
- protected `production` environment and Azure OIDC configuration;
- migration compatibility review before rollback;
- previous artifact retention or a separately retained known-good artifact;
- recovered environment configuration from the approved secret store;
- post-recovery live/readiness, authentication, catalog, cart, sandbox checkout,
  seller, and admin verification.

Azure resources, deployment history, environment reviewers, secrets, runtime
health, and production logs were not accessed or changed.

## Data-loss risks and limitations

- A verified SQLite backup does not prove PostgreSQL backup/restore behavior.
- Database-only recovery omits object storage/media, configuration, encryption
  keys, queues/outbox delivery state, and external payment/provider state.
- The current restore helper writes over the configured target; isolation must be
  established by the operator before any rehearsal.
- No backup retention schedule, immutable/off-site copy, encryption evidence,
  RPO/RTO measurement, or restore duration baseline was verified.
- No production or staging restore, failover, Azure rollback, or customer-data
  recovery was performed.

## Final local verification

| Command | Result |
|---|---|
| `npm run lint` | **PASS** — `tsc --noEmit`, exit code 0 |
| `npm run build` | **PASS with existing warning** — production bundle generated; Vite reported the existing large-chunk warning |
| `python -m pytest -q` | **PASS** — 305 passed in 486.71s |
| `.\android\gradlew.bat -p android :app:test --no-daemon` | **PASS with warnings** — BUILD SUCCESSFUL in 2m 34s |
| `git diff --check` | **PASS** at final pre-report verification |

## Files changed

Only this report was added for Phase 18. No backup code, database schema,
migration, deployment workflow, Azure resource, or production configuration was
changed.
