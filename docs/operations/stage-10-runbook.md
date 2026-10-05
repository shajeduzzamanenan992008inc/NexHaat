# Stage 10 — production operations runbook

Stage 10 is in progress. This runbook separates checks the application can perform from controls that must be configured in the hosting account. Do not put credentials, customer data, or database dumps in the repository.

## Application checks

1. Set `APP_ENV=production` and the remaining production environment variables in the hosting provider's private settings, then run `flask --app run.py production-check`. Resolve each reported item before accepting production traffic. The check validates configuration; it does not prove that external services are reachable.
2. Use managed PostgreSQL with encrypted connections. Production configuration automatically adds `sslmode=require` when the URL omits TLS or requests a weaker mode; retain `verify-ca` or `verify-full` when the provider's CA setup supports certificate verification. `production-check` rejects URLs without a TLS-required mode.
3. Configure the catalog scanner executable and S3-compatible bucket/CDN values. Give the app's service identity only the object permissions it needs.
4. After confirming the active deployment and target bucket, run:

   ```powershell
   flask --app run.py catalog-media-smoke-check --confirm-external-write
   ```

   This command passes a generated 1×1 PNG through the normal private-quarantine, malware-scan, sanitize, and upload path, reads the stored object metadata, and deletes the temporary object (including its version when bucket versioning is enabled). The command is intentionally gated because it writes to the configured bucket. Verify public CDN delivery separately with a normal approved product image; the smoke command does not claim to validate CDN caching or browser delivery.
5. Check `flask --app run.py db-size` against the configured database ceiling. Configure `/health/live` as the process liveness probe and `/health/ready` as the database readiness probe. Existing `/health` and `/health/db` routes remain readiness aliases. Set `APP_TIMING_ENABLED=1` only when host-side latency collection will consume the standard `Server-Timing` response header; this adds no per-request log output or log files.

## Hosting and recovery checks

- Use managed PostgreSQL with encrypted connections and keep the database private to the application network. Confirm ingress/WAF and trusted-proxy settings at the host before exposing the service.
- Schedule `flask --app run.py backup-db --to <destination>` to write backups to encrypted storage outside the application workspace. Set retention and alert on failed or stale runs.
- Rehearse restoration in an isolated staging database/environment and record the restore duration and data-integrity result. `restore-db` replaces the database configured for that process; verify the target and pass `--confirm-target`. Never point a restore drill at production.
- Configure host monitoring for application health, database health/size, backup freshness, payment callback failures, and upload failures. Keep application logs on the configured host console/collector; the app must not redirect logs into repeated workspace files.
- Review database query plans and indexes against measured production queries. Measure page/API latency, image delivery, and load behavior before adding a cache, task queue, or dedicated search service.
- Keep security/business events in the existing audit trail. Avoid logging passwords, OTP values, payment credentials, request bodies, or raw client addresses.

## Stage 10 acceptance record

| Acceptance area | Current state |
| --- | --- |
| Production readiness, health probes, backup tooling, audit trail, database size check | Application code exists; 29 focused security/operations tests passed on 2026-10-05; host setup still needs evidence |
| PostgreSQL transport security and restore-target guard | Production PostgreSQL URLs require TLS; restore CLI requires `--confirm-target`; covered by the 29-test focused run on 2026-10-05 |
| ClamAV + S3 smoke check | Command exists and refuses external writes without its explicit flag; live check remains open because scanner and bucket configuration are absent |
| Managed PostgreSQL and private ingress/WAF | Hosting account is not connected to this workspace |
| Scheduled backups and isolated restore drill | No scheduler/backup destination is configured; no drill recorded |
| Monitoring, CDN delivery, indexes, and load behavior | Requires production traffic, host metrics, and CDN configuration |

Keep Stage 10 In progress until the live media smoke check passes and the hosting-side PostgreSQL, ingress/WAF, scheduled backup, isolated restore drill, monitoring, image delivery, and workload review have recorded evidence. Document measured bottlenecks and any follow-up infrastructure decision in the master plan.
